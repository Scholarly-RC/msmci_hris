from django.apps import apps
from django.db import transaction

from performance.utils import get_user_questionnaire


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
