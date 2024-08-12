from django.apps import apps
from django.shortcuts import redirect
from django_htmx.http import HttpResponseClientRedirect

from performance.enums import QuestionnaireTypes


def get_year_and_quarter_from_user_evaluation(user_evaluation):
    user_evaluation_model = apps.get_model("performance", "UserEvaluation")

    selected_quarter = user_evaluation_model.Quarter(
        user_evaluation.quarter
    ).name.replace("_", " ")

    selected_year = user_evaluation.year

    return f"{selected_year} - {selected_quarter}"


def get_user_evaluator_choices(selected_user):
    user_model = apps.get_model("auth", "User")
    evaluator_choices = (
        user_model.objects.filter(
            is_active=True, userdetails__department=selected_user.userdetails.department
        )
        .exclude(pk=selected_user.id)
        .order_by("-userdetails__user_role", "first_name")
    )

    return evaluator_choices


def get_existing_evaluators_ids(user_evaluation):
    return user_evaluation.evaluations.exclude(
        evaluator=user_evaluation.evaluatee
    ).values_list("evaluator__id", flat=True)


def get_user_questionnaire(user):
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
    current_ratings = []
    for evaluation in evalutaions:
        rating = evaluation.get_specific_rating(domain_number, indicator_number)
        if rating:
            rating = int(rating)
            current_ratings.append(rating)
    rating_mean = get_list_mean(current_ratings)
    return rating_mean


def get_list_mean(values_list):
    if values_list:
        mean = sum(values_list) / len(values_list)
        if mean.is_integer():
            return int(mean)
        return mean
    return 0


def check_if_user_is_evaluator(evaluation, current_user) -> bool:
    current_user_evaluation = evaluation.user_evaluation
    return current_user.id in get_existing_evaluators_ids(current_user_evaluation)


def redirect_user(is_htmx: bool, redirect_url: str):
    if is_htmx:
        return HttpResponseClientRedirect(redirect_url)
    return redirect(redirect_url)


def check_item_already_exists_on_poll_choices(poll, item) -> bool:
    data = poll.data
    return any(item in d for d in data)
