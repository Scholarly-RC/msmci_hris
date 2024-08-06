import datetime

from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.timezone import make_aware
from django_htmx.http import push_url, reswap, retarget, trigger_client_event
from render_block import render_block_to_string

from performance.actions import (
    add_self_evaluation,
    modify_content_data_rating,
    process_evaluator_modification,
)
from performance.models import Evaluation, Questionnaire, UserEvaluation
from performance.utils import (
    get_existing_evaluators,
    get_user_evaluator_choices,
    get_year_and_quarter_from_user_evaluation,
)


# Create your views here.
def performance_management(request):
    return redirect(reverse("performance:performance_evaluation"))


def performance_evaluation(request):
    context = {"evaluation_section": "self"}
    current_user = request.user
    user_evaluations = UserEvaluation.objects.filter(
        evaluatee=current_user, is_finalized=True
    ).order_by("-year")

    current_user_evaluation = user_evaluations.first()

    context.update(
        {
            "user_evaluations": user_evaluations,
            "current_user_evaluation": current_user_evaluation,
        }
    )

    current_evaluation = current_user_evaluation.evaluations.filter(
        evaluator=current_user
    ).first()

    if current_evaluation:
        context.update(
            {
                "current_evaluation": current_evaluation,
            }
        )

    if current_evaluation.is_submitted():
        current_submitted_evaluation_data = (
            current_user_evaluation.get_questionnaire_content_data_with_self_and_peer_rating_mean()
        )
        context.update(
            {
                "current_submitted_evaluation_data": current_submitted_evaluation_data,
            }
        )

    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/performance_management.html",
            "performance_and_learning_management_section",
            context,
        )
        response = push_url(
            response,
            reverse(
                "performance:performance_evaluation",
            ),
        )
        response = retarget(response, "#performance_and_learning_management_section")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "performance/performance_management.html", context)


def performance_peer_evaluation(request):
    context = {"evaluation_section": "peer"}

    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/performance_management.html",
            "performance_and_learning_management_section",
            context,
        )
        response = push_url(
            response,
            reverse(
                "performance:performance_peer_evaluation",
            ),
        )
        response = retarget(response, "#performance_and_learning_management_section")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "performance/performance_management.html", context)


def submit_evaluation_rating(request):
    context = {}
    if request.htmx and request.method == "POST":
        data = request.POST

        modify_content_data_rating(data)

        current_evaluation_id = data.get("current_evaluation")
        current_evaluation = Evaluation.objects.get(id=current_evaluation_id)
        context.update({"current_evaluation": current_evaluation})

        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/performance_management.html",
            "evaluation_counter_and_submit_section",
            context,
        )
        response = retarget(response, "#evaluation_counter_and_submit_section")
        response = reswap(response, "outerHTML")
        return response


def submit_user_evaluation(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        current_evaluation_id = data.get("current_evaluation")
        current_evaluation = Evaluation.objects.get(id=current_evaluation_id)
        current_evaluation.date_submitted = make_aware(datetime.datetime.now())
        current_evaluation.save()
        response = HttpResponse()
        return response


def switch_performance_management_section(request):
    if request.htmx:
        breakpoint()


def user_evaluation_management(request, year=""):
    context = {}

    users = User.objects.filter(is_superuser=False, is_active=True).order_by(
        "-userdetails__department"
    )

    user_search_query = request.POST.get("search_user")
    if user_search_query:
        search_params = (
            Q(first_name__icontains=user_search_query)
            | Q(last_name__icontains=user_search_query)
            | Q(userdetails__middle_name__icontains=user_search_query)
        )
        context.update({"user_search_query": user_search_query})
        users = users.filter(search_params)

    selected_year = (
        request.POST.get("evaluation_year") or year or datetime.datetime.now().year
    )
    selected_year = int(selected_year)

    first_quarter_value = UserEvaluation.Quarter.FIRST_QUARTER.value
    second_quarter_value = UserEvaluation.Quarter.SECOND_QUARTER.value

    context.update(
        {
            "employee_details": [
                {
                    "user": user,
                    "current_first_quarter_user_evaluation": user.evaluatee_evaluations.filter(
                        quarter=first_quarter_value, year=selected_year
                    ).first(),
                    "current_second_quarter_user_evaluation": user.evaluatee_evaluations.filter(
                        quarter=second_quarter_value, year=selected_year
                    ).first(),
                }
                for user in users
            ],
            "selected_year": selected_year,
        }
    )

    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/user_evaluation_management.html",
            "user_evaluation_management_section",
            context,
        )
        response = push_url(
            response,
            reverse(
                "performance:user_evaluation_management_filtered",
                kwargs={"year": selected_year},
            ),
        )
        response = retarget(response, "#user_evaluation_management_section")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "performance/user_evaluation_management.html", context)


def modify_user_evaluation(request, pk, quarter, year=""):
    context = {}
    selected_user = User.objects.get(id=pk)

    evaluator_choices = get_user_evaluator_choices(selected_user)

    selected_year = year or datetime.datetime.now().year
    selected_year = int(selected_year)

    user_evaluation, user_evaluation_created = UserEvaluation.objects.get_or_create(
        evaluatee=selected_user, quarter=quarter, year=selected_year
    )

    if user_evaluation_created:
        add_self_evaluation(user_evaluation)

    year_and_quarter = get_year_and_quarter_from_user_evaluation(user_evaluation)

    existing_evaluators = get_existing_evaluators(user_evaluation)

    if user_evaluation.is_finalized:
        evaluator_choices = evaluator_choices.filter(id__in=existing_evaluators)

        existing_evaluations = user_evaluation.evaluations.all()
        context.update({"existing_evaluation_data": existing_evaluations})

    context.update(
        {
            "selected_user": selected_user,
            "evaluator_choices": evaluator_choices.exclude(pk__in=existing_evaluators),
            "selected_choices": evaluator_choices.filter(pk__in=existing_evaluators),
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
                kwargs={"pk": pk, "quarter": quarter, "year": selected_year},
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

    if user_evaluation.is_finalized:
        evaluator_choices = evaluator_choices.filter(id__in=existing_evaluators)

        existing_evaluations = user_evaluation.evaluations.all()
        context.update({"existing_evaluation_data": existing_evaluations})

    context.update(
        {
            "selected_user": selected_user,
            "evaluator_choices": evaluator_choices.exclude(pk__in=existing_evaluators),
            "selected_choices": evaluator_choices.filter(pk__in=existing_evaluators),
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

        selected_user = user_evaluation.evaluatee

        evaluator_choices = get_user_evaluator_choices(selected_user)

        year_and_quarter = get_year_and_quarter_from_user_evaluation(user_evaluation)

        existing_evaluators = get_existing_evaluators(user_evaluation)

        if user_evaluation.is_finalized:
            evaluator_choices = evaluator_choices.filter(id__in=existing_evaluators)

            existing_evaluations = user_evaluation.evaluations.all()
            context.update({"existing_evaluation_data": existing_evaluations})

        context.update(
            {
                "selected_user": selected_user,
                "evaluator_choices": evaluator_choices.exclude(
                    pk__in=existing_evaluators
                ),
                "selected_choices": evaluator_choices.filter(
                    pk__in=existing_evaluators
                ),
                "year_and_quarter": year_and_quarter,
                "user_evaluation": user_evaluation,
                "existing_evaluators": existing_evaluators,
            }
        )

        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/modify_user_evaluation.html",
            "modify_user_evaluation_section",
            context,
        )

        response = retarget(response, "#modify_user_evaluation_section")
        response = reswap(response, "outerHTML")
        return response
