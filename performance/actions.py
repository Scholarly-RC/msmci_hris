from django.apps import apps
from django.db import transaction

from performance.enums import QuestionnaireTypes


@transaction.atomic
def process_evaluator_modification(user_evaluation, evaluator_id, to_remove=""):
    evaluation_model = apps.get_model("performance", "Evaluation")
    questionaire_model = apps.get_model("performance", "Questionnaire")
    user_model = apps.get_model("auth", "User")

    if to_remove == "ALL":
        user_evaluation.evaluations.all().delete()
        return

    if to_remove == "ONE":
        user_evaluation.evaluations.filter(evaluator__id=evaluator_id).delete()
        return

    selected_evaluator = user_model.objects.get(id=evaluator_id)

    is_evaluatee_employee = user_evaluation.evaluatee.userdetails.is_employee()
    if is_evaluatee_employee:
        questionnaire = questionaire_model.objects.get(
            content__questionnaire_code=QuestionnaireTypes.NEPET.value
        )
    else:
        questionnaire = questionaire_model.objects.get(
            content__questionnaire_code=QuestionnaireTypes.NAPES.value
        )

    new_evaluation, new_evaluation_created = evaluation_model.objects.get_or_create(
        evaluator=selected_evaluator,
        user_evaluation=user_evaluation,
        questionnaire=questionnaire,
        defaults={"content_data": questionnaire.content.get("questionnaire_content")},
    )
    return


def _reset_evaluation_values(evaluation):
    questionnaire_content = evaluation.questionnaire.content.get(
        "questionnaire_content"
    )
    evaluation.content_data = questionnaire_content
    evaluation.positive_feedback = None
    evaluation.improvement_suggestion = None
    evaluation.save()
