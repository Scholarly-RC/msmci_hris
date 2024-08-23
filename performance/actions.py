from django.apps import apps
from django.db import transaction
from django_q.tasks import async_task

from performance.utils import (
    extract_filename_and_extension,
    get_user_questionnaire,
    get_user_with_hr_role,
    validate_file_size,
)


@transaction.atomic
def process_evaluator_modification(user_evaluation, evaluator_id, to_remove=""):
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
    for domain in current_content_data:
        if domain.get("domain_number") == domain_number:
            domain_questions = domain.get("questions")
            for question in domain_questions:
                if question.get("indicator_number") == indicator_number:
                    question["rating"] = value
    return current_content_data


@transaction.atomic
def modify_qualitative_content_data(current_evaluation_id: str, key: str, value: str):
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
    selected_evaluation.reset_evaluation()


@transaction.atomic
def add_poll_choice(poll, new_item, color):
    data = poll.data
    data.append({new_item: {"color": color, "voters": []}})
    poll.save()

    return poll


@transaction.atomic
def remove_poll_choice(poll, item_index_to_remove):
    data = poll.data
    item_index_to_remove = int(item_index_to_remove)
    data.pop(item_index_to_remove)
    poll.save()

    return poll


@transaction.atomic
def submit_poll_choice(poll, choice_index, user):
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

        hr = get_user_with_hr_role()
        hr_id = hr.values_list("id", flat=True)
        new_shared_resource.shared_to.add(*hr_id)

    user_shared_resources = shared_resources_model.objects.filter(uploader=user)
    return user_shared_resources, errors
