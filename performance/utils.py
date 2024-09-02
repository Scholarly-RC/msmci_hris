import datetime
import os
from collections import defaultdict
from itertools import chain
from operator import attrgetter

from django.apps import apps
from django.db.models import Q
from django.shortcuts import redirect
from django_htmx.http import HttpResponseClientRedirect

from performance.enums import QuestionnaireTypes


def get_year_and_quarter_from_user_evaluation(user_evaluation):
    """
    Extracts and formats the year and quarter from a user evaluation.
    Returns a string in the format "Year - Quarter".
    """

    user_evaluation_model = apps.get_model("performance", "UserEvaluation")

    selected_quarter = user_evaluation_model.Quarter(
        user_evaluation.quarter
    ).name.replace("_", " ")

    selected_year = user_evaluation.year

    return f"{selected_year} - {selected_quarter}"


def get_user_evaluator_choices(selected_user):
    """
    Retrieves a list of active users from the same department as the selected user,
    excluding the selected user themselves. The list is ordered by user role and first name.
    """

    user_model = apps.get_model("auth", "User")
    user_details_model = apps.get_model("core", "UserDetails")

    hr_role = user_details_model.Role.HR.value

    evaluator_choices = (
        user_model.objects.filter(
            Q(userdetails__user_role=hr_role)
            | Q(userdetails__department=selected_user.userdetails.department),
            is_active=True,
        )
        .exclude(pk=selected_user.id)
        .order_by("-userdetails__user_role", "first_name")
    )

    return evaluator_choices


def get_existing_evaluators_ids(user_evaluation):
    """
    Retrieves a list of evaluator IDs from the user evaluations, excluding the evaluatee's ID.
    """

    return user_evaluation.evaluations.exclude(
        evaluator=user_evaluation.evaluatee
    ).values_list("evaluator__id", flat=True)


def get_user_questionnaire(user):
    """
    Retrieves the appropriate questionnaire for the user based on their employment status.
    Returns the questionnaire with the code 'NEPET' if the user is an employee,
    otherwise returns the questionnaire with the code 'NAPES'.
    """

    questionaire_model = apps.get_model("performance", "Questionnaire")

    is_evaluatee_employee = user.userdetails.is_employee()
    if is_evaluatee_employee:
        return questionaire_model.objects.get(
            content__questionnaire_code=QuestionnaireTypes.NEPET.value
        )

    return questionaire_model.objects.get(
        content__questionnaire_code=QuestionnaireTypes.NAPES.value
    )


def get_question_rating_mean_from_evaluations(
    evalutaions, domain_number: str, indicator_number: str
):
    """
    Calculates the mean rating for a specific domain and indicator from a list of evaluations.
    Returns the mean rating based on the collected ratings.
    """

    current_ratings = []
    for evaluation in evalutaions:
        rating = evaluation.get_specific_rating(domain_number, indicator_number)
        if rating:
            rating = int(rating)
            current_ratings.append(rating)
    rating_mean = get_list_mean(current_ratings)
    return rating_mean


def get_list_mean(values_list):
    """
    Calculates the mean of a list of numbers.
    Returns an integer if the mean is a whole number, otherwise returns a float.
    Returns 0 if the list is empty.
    """

    if values_list:
        mean = sum(values_list) / len(values_list)
        if mean.is_integer():
            return int(mean)
        return mean
    return 0


def check_if_user_is_evaluator(evaluation, current_user) -> bool:
    """
    Checks if the current user is an evaluator for the given evaluation.
    Returns True if the user is an evaluator, otherwise False.
    """

    current_user_evaluation = evaluation.user_evaluation
    return current_user.id in get_existing_evaluators_ids(current_user_evaluation)


def redirect_user(is_htmx: bool, redirect_url: str):
    """
    Redirects the user based on whether the request is made with HTMX.
    Uses `HttpResponseClientRedirect` for HTMX requests and `redirect` for others.
    """

    if is_htmx:
        return HttpResponseClientRedirect(redirect_url)
    return redirect(redirect_url)


def check_item_already_exists_on_poll_choices(poll, item) -> bool:
    """
    Checks if the specified item already exists in the poll's choices.
    Returns True if the item is found, otherwise False.
    """

    data = poll.data
    return any(item in d for d in data)


def get_polls_and_posts_by_date_and_filter(date="", filters=[]):
    """
    Fetches polls and posts from the database, with optional filtering by date and type.
    Returns a list of dates with their corresponding polls and posts, sorted by date and creation time.
    """
    poll_model = apps.get_model("performance", "Poll")
    post_model = apps.get_model("performance", "Post")

    if not filters:
        show_poll = True
        show_post = True
    else:
        show_poll = "poll" in filters
        show_post = "post" in filters

    polls = (
        poll_model.objects.all().order_by("-created")
        if show_poll
        else poll_model.objects.none()
    )
    posts = (
        post_model.objects.all().order_by("-created")
        if show_post
        else post_model.objects.none()
    )

    if date:
        date = datetime.datetime.strptime(date, "%m/%d/%Y").date()
        if polls:
            polls = polls.filter(created__date=date)
        if posts:
            posts = posts.filter(created__date=date)

    polls_and_post_by_date = defaultdict(list)

    if polls:
        for poll in polls:
            polls_and_post_by_date[poll.created.date()].append(poll)
    if posts:
        for post in posts:
            polls_and_post_by_date[post.created.date()].append(post)

    result = []

    for date, polls_and_posts in polls_and_post_by_date.items():
        polls_and_posts.sort(key=lambda item: item.created, reverse=True)
        result.append({"date": date, "polls_and_posts": polls_and_posts})

    result.sort(key=lambda item: item["date"], reverse=True)

    return result


def check_if_user_already_voted(poll, user) -> bool:
    """
    Checks if the specified user has already voted in the given poll.
    Returns True if the user has voted, otherwise False.
    """
    data = poll.data
    for choice in data:
        for key, value in choice.items():
            if user.id in value.get("voters"):
                return True
    return False


def get_poll_and_post_combined_list():
    """
    Retrieves all polls and posts from the database, combines them into a single list,
    and sorts them by creation date in descending order.
    """

    poll_model = apps.get_model("performance", "Poll")
    post_model = apps.get_model("performance", "Post")

    all_polls = poll_model.objects.all().order_by("-created")
    all_posts = post_model.objects.all().order_by("-created")

    combined_list = list(chain(all_polls, all_posts))
    sorted_combined_list = sorted(
        combined_list, key=attrgetter("created"), reverse=True
    )

    return sorted_combined_list


def get_shared_resources_directory_path(instance, filename):
    return f"{instance.uploader.id}/resource/{filename}"


def get_user_with_hr_role():
    user_model = apps.get_model("auth", "User")
    user_details_model = apps.get_model("core", "UserDetails")

    hr_role = user_details_model.Role.HR.value
    hr = user_model.objects.filter(userdetails__user_role=hr_role)
    return hr


def extract_filename_and_extension(filename: str):
    name, extension = os.path.splitext(filename)
    return name, extension


def validate_file_size(file):
    # TODO: Update if needed.
    # size_limit = 10 * 1024 * 1024
    # if file.size > size_limit:
    #     return "File size exceeded limit."
    return None


def get_users_shared_resources(uploader_id, shared_to_id):
    user_model = apps.get_model("auth", "User")
    shared_documents_model = apps.get_model("performance", "SharedResource")

    if shared_to_id:
        shared_documents_filter = Q(uploader_id=uploader_id) & Q(shared_to=shared_to_id)
    else:
        shared_documents_filter = Q(uploader_id=uploader_id) & Q(shared_to__isnull=True)

    user_shared_documents = shared_documents_model.objects.filter(
        shared_documents_filter
    )
    return user_shared_documents


def get_users_for_shared_resources(user):
    user_model = apps.get_model("auth", "User")
    user_details_model = apps.get_model("core", "UserDetails")

    hr_role = user_details_model.Role.HR.value
    department_head_role = user_details_model.Role.DEPARTMENT_HEAD.value
    employee_role = user_details_model.Role.EMPLOYEE.value

    users = user_model.objects.filter(
        Q(userdetails__user_role=hr_role)
        | Q(userdetails__user_role=department_head_role)
        | Q(userdetails__user_role=employee_role)
    ).exclude(pk=user.id)

    return users


def get_users_per_shared_resources(user, resource):
    user_model = apps.get_model("auth", "User")
    user_details_model = apps.get_model("core", "UserDetails")

    hr_role = user_details_model.Role.HR.value
    department_head_role = user_details_model.Role.DEPARTMENT_HEAD.value
    employee_role = user_details_model.Role.EMPLOYEE.value

    users_shared_with_resource = resource.shared_to.values_list("id", flat=True)

    users = (
        user_model.objects.filter(
            Q(userdetails__user_role=hr_role)
            | Q(userdetails__user_role=department_head_role)
            | Q(userdetails__user_role=employee_role)
        )
        .exclude(id=user.id)
        .exclude(id__in=users_shared_with_resource)
    )

    return users
