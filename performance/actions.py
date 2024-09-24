from django.apps import apps
from django.db import transaction
from django_q.tasks import async_task

from performance.utils import (
    extract_filename_and_extension,
    get_user_questionnaire,
    validate_file_size,
)


@transaction.atomic
def process_evaluator_modification(user_evaluation, evaluator_id, to_remove=""):
    """
    Modifies the list of evaluators for a user's evaluation.
    - If `to_remove` is "ALL", it deletes all evaluations for the user.
    - If `to_remove` is "ONE", it deletes evaluations by the specified evaluator.
    - Otherwise, it adds or updates an evaluation for the specified evaluator.
    """
    evaluation_model = apps.get_model("performance", "Evaluation")
    user_model = apps.get_model("auth", "User")

    if to_remove == "ALL":
        user_evaluation.evaluations.all().delete()
        return

    if to_remove == "ONE":
        user_evaluation.evaluations.filter(evaluator__id=evaluator_id).delete()
        return

    selected_evaluator = user_model.objects.get(id=evaluator_id)

    questionnaire = get_user_questionnaire(user_evaluation.evaluatee)

    new_evaluation, new_evaluation_created = evaluation_model.objects.get_or_create(
        evaluator=selected_evaluator,
        user_evaluation=user_evaluation,
        questionnaire=questionnaire,
        defaults={"content_data": questionnaire.content.get("questionnaire_content")},
    )
    return


@transaction.atomic
def add_self_evaluation(user_evaluation):
    """
    Adds a self-evaluation for the user being evaluated, using their own questionnaire.
    """
    evaluation_model = apps.get_model("performance", "Evaluation")

    self_user = user_evaluation.evaluatee

    questionnaire = get_user_questionnaire(self_user)

    new_evaluation, new_evaluation_created = evaluation_model.objects.get_or_create(
        evaluator=self_user,
        user_evaluation=user_evaluation,
        questionnaire=questionnaire,
        defaults={"content_data": questionnaire.content.get("questionnaire_content")},
    )


@transaction.atomic
def modify_content_data_rating(data):
    """
    Updates the content data rating for an existing evaluation based on provided data.
    """
    evaluation_model = apps.get_model("performance", "Evaluation")
    domain = data.get("domain_number")
    indicator = data.get("indicator_number")
    str_id = domain + "_" + indicator
    value = data.get(str_id)
    current_evaluation_id = data.get("current_evaluation")
    current_evaluation = evaluation_model.objects.get(id=current_evaluation_id)

    current_content_data = current_evaluation.content_data

    _edit_content_data(current_content_data, domain, indicator, value)

    current_evaluation.save()


def _edit_content_data(current_content_data, domain_number, indicator_number, value):
    """
    Updates the rating of a specific indicator in the content data for a given domain.
    """
    for domain in current_content_data:
        if domain.get("domain_number") == domain_number:
            domain_questions = domain.get("questions")
            for question in domain_questions:
                if question.get("indicator_number") == indicator_number:
                    question["rating"] = value
    return current_content_data


@transaction.atomic
def modify_qualitative_content_data(current_evaluation_id: str, key: str, value: str):
    """
    Updates qualitative feedback fields (positive feedback or improvement suggestion)
    for a specific evaluation.
    """
    evaluation_model = apps.get_model("performance", "Evaluation")
    current_evaluation = evaluation_model.objects.get(id=current_evaluation_id)
    value = value.strip()

    if key == "positive_feedback":
        current_evaluation.positive_feedback = value or None
    if key == "improvement_suggestion":
        current_evaluation.improvement_suggestion = value or None

    current_evaluation.save()


@transaction.atomic
def reset_selected_evaluation(selected_evaluation):
    """
    Resets the specified evaluation to its initial state.
    """
    selected_evaluation.reset_evaluation()


@transaction.atomic
def add_poll_choice(poll, new_item, color):
    """
    Adds a new choice to a poll with a specified color and no initial voters.
    """
    data = poll.data
    data.append({new_item: {"color": color, "voters": []}})
    poll.save()

    return poll


@transaction.atomic
def remove_poll_choice(poll, item_index_to_remove):
    """
    Removes a choice from the poll at the specified index.
    """
    data = poll.data
    item_index_to_remove = int(item_index_to_remove)
    data.pop(item_index_to_remove)
    poll.save()

    return poll


@transaction.atomic
def submit_poll_choice(poll, choice_index, user):
    """
    Records a user's vote for a specific choice in the poll.
    Adds the user's ID to the list of voters for the selected choice.
    """
    data = poll.data
    choice_index = int(choice_index)
    selected_choice = data[choice_index]

    for key, value in selected_choice.items():
        voters = value.get("voters")
        voters.append(user.id)
    poll.save()
    return poll


@transaction.atomic
def process_upload_resources(user, file_data):
    """
    Handles the uploading of multiple files.
    Validates file sizes and creates shared resources entries for valid files.
    If the file is not a media file or a PDF, initiates an asynchronous task to convert it to PDF.
    """
    shared_resources_model = apps.get_model("performance", "SharedResource")
    errors = []
    files = file_data.getlist("uploaded_resources")
    for file in files:
        file_name, ext = extract_filename_and_extension(file.name)
        file_size_error = validate_file_size(file)
        if file_size_error is not None:
            errors.append(f"Error: {file_name}{ext} - {file_size_error}")
            break

        new_shared_resource = shared_resources_model.objects.create(
            uploader=user, resource=file, resource_name=file_name
        )

        if (
            not new_shared_resource.is_resource_media()
            and not new_shared_resource.is_resource_pdf()
        ):
            async_task(
                "performance.tasks.convert_document_to_pdf",
                new_shared_resource,
                file_name,
            )

    user_shared_resources = shared_resources_model.objects.filter(uploader=user)
    return user_shared_resources, errors


@transaction.atomic
def share_resource_to_user(resource, selected_user_id, remove=False):
    """
    Shares or unshares a resource with a specific user.
    If `remove` is False, adds the user to the list of users with access to the resource.
    If `remove` is True, removes the user from the list and from confidential access users.
    """
    user_model = apps.get_model("auth", "User")

    selected_user = user_model.objects.get(id=selected_user_id)
    if not remove:
        resource.shared_to.add(selected_user)
    else:
        resource.shared_to.remove(selected_user)
        resource.confidential_access_users.remove(selected_user)

    return resource


@transaction.atomic
def modify_user_file_confidentiality(resource_id, selected_user_id):
    """
    Toggles a user's confidential access status to a specific resource.
    Adds the user to confidential access if not already present; removes if present.
    """
    user_model = apps.get_model("auth", "User")
    shared_resources_model = apps.get_model("performance", "SharedResource")

    selected_user = user_model.objects.get(id=selected_user_id)
    resource = shared_resources_model.objects.get(id=resource_id)

    if selected_user in resource.confidential_access_users.all():
        resource.confidential_access_users.remove(selected_user)
    else:
        resource.confidential_access_users.add(selected_user)

    return resource, selected_user
