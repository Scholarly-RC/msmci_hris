import datetime

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django_htmx.http import push_url, reswap, retarget, trigger_client_event
from render_block import render_block_to_string

from performance.actions import process_evaluator_modification
from performance.models import Questionnaire, UserEvaluation
from performance.utils import (
    get_user_evaluator_choices,
    get_year_and_quarter_from_user_evaluation,
    get_existing_evaluators,
)


# Create your views here.
def performance_management(request):
    questionnaire_content = Questionnaire.objects.last().content.get(
        "questionnaire_content", {}
    )
    context = {"questionnaire_content": questionnaire_content}
    return render(request, "performance/performance_management.html", context)


def user_evaluation_management(request):
    users = User.objects.filter(is_superuser=False, is_active=True).order_by(
        "-userdetails__department"
    )
    context = {
        "employee_details": [
            {
                "user": user,
                "current_user_evaluation": user.evaluatee_evaluations.filter(
                    is_finalized=False
                ).first(),
            }
            for user in users
        ]
    }

    return render(request, "performance/user_evaluation_management.html", context)


def modify_user_evaluation(request, pk, quarter, year=""):
    context = {}
    selected_user = User.objects.get(id=pk)

    evaluator_choices = get_user_evaluator_choices(selected_user)

    context.update(
        {"selected_user": selected_user, "evaluator_choices": evaluator_choices}
    )

    selected_year = year or datetime.datetime.now().year

    user_evaluation, user_evaluation_created = UserEvaluation.objects.get_or_create(
        evaluatee=selected_user, quarter=quarter, year=selected_year
    )

    year_and_quarter = get_year_and_quarter_from_user_evaluation(user_evaluation)

    existing_evaluators = get_existing_evaluators(user_evaluation)

    context.update(
        {
            "year_and_quarter": year_and_quarter,
            "user_evaluation": user_evaluation,
            "existing_evaluators": existing_evaluators,
        }
    )

    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/modify_user_evaluation.html",
            "modify_user_evaluation_section",
            context,
        )
        response = push_url(
            response,
            reverse(
                "performance:modify_user_evaluation",
                kwargs={"pk": pk, "quarter": quarter},
            ),
        )
        response = retarget(response, "#user_evaluation_management_section")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "performance/modify_user_evaluation.html", context)


def finalize_user_evaluation_toggle(request, user_evaluation_id):
    context = {}
    user_evaluation = UserEvaluation.objects.get(id=user_evaluation_id)
    user_evaluation.is_finalized = not user_evaluation.is_finalized
    user_evaluation.save()

    selected_user = user_evaluation.evaluatee

    evaluator_choices = get_user_evaluator_choices(selected_user)

    year_and_quarter = get_year_and_quarter_from_user_evaluation(user_evaluation)

    existing_evaluators = get_existing_evaluators(user_evaluation)

    context.update(
        {
            "selected_user": selected_user,
            "user_evaluation": user_evaluation,
            "evaluator_choices": evaluator_choices,
            "year_and_quarter": year_and_quarter,
            "existing_evaluators": existing_evaluators,
        }
    )

    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/modify_user_evaluation.html",
            "modify_user_evaluation_section",
            context,
        )
        response = retarget(response, "#modify_user_evaluation_section")
        response = reswap(response, "outerHTML")
        return response


def modify_user_evaluation_evaluators(request, user_evaluation_id):
    context = {}
    user_evaluation = UserEvaluation.objects.get(id=user_evaluation_id)

    if request.htmx and request.method == "POST":
        data = request.POST
        selected_evaluator_id = data.get("selected_evaluator", None)
        selected_evaluator_to_remove_id = data.get("evaluator_to_remove", None)
        deselect_all = data.get("deselect_all", None)

        to_remove_evaluator = (
            selected_evaluator_to_remove_id and not selected_evaluator_id
        )

        process_evaluator_modification(
            user_evaluation,
            selected_evaluator_id or selected_evaluator_to_remove_id,
            "ALL" if deselect_all else "ONE" if to_remove_evaluator else "",
        )

        evaluator_choices = get_user_evaluator_choices(user_evaluation.evaluatee)
        existing_evaluators = get_existing_evaluators(user_evaluation)

        context.update(
            {
                "user_evaluation": user_evaluation,
                "evaluator_choices": evaluator_choices,
                "existing_evaluators": existing_evaluators,
            }
        )

        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/modify_user_evaluation.html",
            "select_evaluator_section",
            context,
        )

        response = retarget(response, "#select_evaluator_section")
        response = reswap(response, "outerHTML")
        return response
