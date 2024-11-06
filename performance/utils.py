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

    UserEvaluationModel = apps.get_model("performance", "UserEvaluation")

    selected_quarter = UserEvaluationModel.Quarter(
        user_evaluation.quarter
    ).name.replace("_", " ")

    selected_year = user_evaluation.year

    return f"{selected_year} - {selected_quarter}"


def get_user_evaluator_choices(selected_user):
    """
    Retrieves a list of active users from the same department as the selected user,
    excluding the selected user themselves. The list is ordered by user role and first name.
    """

    UserModel = apps.get_model("auth", "User")
    UserDetailsModel = apps.get_model("core", "UserDetails")

    hr_role = UserDetailsModel.Role.HR.value
    director_role = UserDetailsModel.Role.DIRECTOR.value
    president_role = UserDetailsModel.Role.PRESIDENT.value

    evaluator_choices = (
        UserModel.objects.filter(
            Q(is_active=True),
            Q(userdetails__role=hr_role)
            | Q(userdetails__role=director_role)
            | Q(userdetails__role=president_role)
            | Q(userdetails__department=selected_user.userdetails.department),
            is_active=True,
        )
        .exclude(pk=selected_user.id)
        .order_by("-userdetails__role", "first_name")
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

    QuestionnaireModel = apps.get_model("performance", "Questionnaire")

    is_evaluatee_employee = user.userdetails.is_employee()
    if is_evaluatee_employee:
        return QuestionnaireModel.objects.get(
            content__questionnaire_code=QuestionnaireTypes.NEPET.value
        )

    return QuestionnaireModel.objects.get(
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
    PollModel = apps.get_model("performance", "Poll")
    PostModel = apps.get_model("performance", "Post")

    if not filters:
        show_poll = True
        show_post = True
    else:
        show_poll = "poll" in filters
        show_post = "post" in filters

    polls = (
        PollModel.objects.all().order_by("-created")
        if show_poll
        else PollModel.objects.none()
    )
    posts = (
        PostModel.objects.all().order_by("-created")
        if show_post
        else PostModel.objects.none()
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

    PollModel = apps.get_model("performance", "Poll")
    PostModel = apps.get_model("performance", "Post")

    all_polls = PollModel.objects.all().order_by("-created")
    all_posts = PostModel.objects.all().order_by("-created")

    combined_list = list(chain(all_polls, all_posts))
    sorted_combined_list = sorted(
        combined_list, key=attrgetter("created"), reverse=True
    )

    return sorted_combined_list


def get_shared_resources_directory_path(instance, filename):
    """
    Returns the file path for saving a file based on the uploader's ID and the filename.
    """
    return f"{instance.uploader.id}/resource/{filename}"


def get_user_with_hr_role():
    """
    Retrieves users who have the HR role.
    """
    UserModel = apps.get_model("auth", "User")
    UserDetailsModel = apps.get_model("core", "UserDetails")

    hr_role = UserDetailsModel.Role.HR.value
    hr = UserModel.objects.filter(is_active=True, userdetails__role=hr_role)
    return hr


def extract_filename_and_extension(filename: str):
    """
    Splits the filename into its name and extension parts.
    """
    name, extension = os.path.splitext(filename)
    return name, extension


def validate_file_size(file):
    # TODO: Update if needed.
    # size_limit = 10 * 1024 * 1024
    # if file.size > size_limit:
    #     return "File size exceeded limit."
    return None


def get_users_shared_resources(uploader_id, shared_to_id=""):
    """
    Retrieves documents shared with a specific user or uploaded by them.
    If `shared_to_id` is provided, it returns documents where the uploader is either `uploader_id` or `shared_to_id`,
    and the document is shared with either `shared_to_id` or `uploader_id`.
    If `shared_to_id` is not provided, it returns documents uploaded by `uploader_id` and not shared with anyone.
    """
    SharedResourceModel = apps.get_model("performance", "SharedResource")

    if shared_to_id:
        shared_documents_filter = (
            Q(uploader_id=uploader_id) | Q(uploader_id=shared_to_id)
        ) & (Q(shared_to=shared_to_id) | Q(shared_to=uploader_id))
    else:
        shared_documents_filter = Q(uploader_id=uploader_id) & Q(shared_to__isnull=True)

    user_shared_documents = SharedResourceModel.objects.filter(shared_documents_filter)
    return user_shared_documents


def get_users_for_shared_resources(user):
    """
    Retrieves users with HR, President, Director, Department Head, or Employee roles, excluding the specified user.
    """
    UserModel = apps.get_model("auth", "User")
    UserDetailsModel = apps.get_model("core", "UserDetails")

    hr_role = UserDetailsModel.Role.HR.value
    president_role = UserDetailsModel.Role.PRESIDENT.value
    director_role = UserDetailsModel.Role.DIRECTOR.value
    department_head_role = UserDetailsModel.Role.DEPARTMENT_HEAD.value
    employee_role = UserDetailsModel.Role.EMPLOYEE.value

    if user.userdetails.role == employee_role:
        users = UserModel.objects.filter(
            Q(is_active=True),
            Q(userdetails__role=hr_role)
            | Q(
                userdetails__department=user.userdetails.department,
                userdetails__role__in=[department_head_role],
            ),
        ).exclude(pk=user.id)
    elif user.userdetails.role == department_head_role:
        users = UserModel.objects.filter(
            Q(is_active=True),
            Q(userdetails__role=hr_role)
            | Q(
                userdetails__department=user.userdetails.department,
                userdetails__role__in=[director_role, employee_role],
            ),
        ).exclude(pk=user.id)
    elif user.userdetails.role == director_role:
        users = UserModel.objects.filter(
            Q(is_active=True),
            Q(userdetails__role=hr_role)
            | Q(
                userdetails__department=user.userdetails.department,
                userdetails__role__in=[department_head_role, president_role],
            ),
        ).exclude(pk=user.id)
    elif user.userdetails.role == president_role:
        users = UserModel.objects.filter(
            Q(is_active=True),
            Q(userdetails__role=hr_role)
            | Q(
                userdetails__department=user.userdetails.department,
                userdetails__role__in=[director_role],
            ),
        ).exclude(pk=user.id)
    else:
        users = UserModel.objects.exclude(pk=user.id)

    return users


def get_users_per_shared_resources(user, resource):
    """
    Retrieves users who have the HR, President, Director, Department Head, or Employee roles and are not the specified user or already shared with the resource.
    """
    users_shared_with_resource = resource.shared_to.values_list("id", flat=True)

    users = get_users_for_shared_resources(user=user).exclude(
        id__in=users_shared_with_resource
    )

    return users


def get_finalized_user_evaluation_year_list():
    """
    Retrieves a list of distinct years for finalized user evaluations.
    Returns the years in which evaluations have been finalized.
    """
    UserEvaluationModel = apps.get_model("performance", "UserEvaluation")
    return (
        UserEvaluationModel.objects.filter(is_finalized=True)
        .values_list("year", flat=True)
        .distinct()
    )


def get_user_evaluation_users():
    """
    Retrieves a list of users who have finalized evaluations.
    The users are ordered by their first names and returned as distinct entries.
    """
    UserModel = apps.get_model("auth", "User")
    return (
        UserModel.objects.filter(
            is_active=True, evaluatee_evaluations__is_finalized=True
        )
        .order_by("first_name")
        .distinct()
    )
