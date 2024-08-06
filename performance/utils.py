from django.apps import apps
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


def get_existing_evaluators(user_evaluation):
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
