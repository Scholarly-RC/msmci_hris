import datetime

from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.timezone import make_aware
from django_htmx.http import (
    HttpResponseClientRedirect,
    push_url,
    reswap,
    retarget,
    trigger_client_event,
)
from render_block import render_block_to_string

from performance.actions import (
    add_self_evaluation,
    modify_content_data_rating,
    modify_qualitative_content_data,
    process_evaluator_modification,
    reset_selected_evaluation,
    add_poll_choice,
    remove_poll_choice,
)
from performance.models import Evaluation, UserEvaluation, Poll
from performance.utils import (
    check_if_user_is_evaluator,
    get_existing_evaluators_ids,
    get_user_evaluator_choices,
    get_year_and_quarter_from_user_evaluation,
    redirect_user,
    check_item_already_exists_on_poll_choices,
)


# Create your views here.
def performance_management(request):
    return redirect(reverse("performance:performance_evaluation"))


def performance_evaluation(request):
    context = {"evaluation_section": "self"}
    current_user = request.user

    user_evaluations = current_user.evaluatee_evaluations.filter(
        is_finalized=True
    ).order_by("-year")

    current_user_evaluation = (
        user_evaluations.filter(
            id=request.POST.get("selected_year_and_quarter")
        ).first()
        or user_evaluations.first()
    )

    context.update(
        {
            "user_evaluations": user_evaluations,
            "current_user_evaluation": current_user_evaluation,
        }
    )

    if current_user_evaluation:

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


def performance_peer_evaluation(request, evaluation_id=""):
    context = {"evaluation_section": "peer"}
    current_user = request.user

    peer_evaluations = (
        current_user.evaluator_evaluations.exclude(
            user_evaluation__evaluatee=current_user
        )
        .filter(user_evaluation__is_finalized=True)
        .order_by("-user_evaluation__year")
    )

    if evaluation_id:
        selected_peer_evaluation = Evaluation.objects.filter(id=evaluation_id).first()
        if not selected_peer_evaluation:
            return redirect_user(
                request.htmx, reverse("performance:performance_peer_evaluation")
            )
        is_user_evaluator = check_if_user_is_evaluator(
            selected_peer_evaluation, current_user
        )
        if not is_user_evaluator:
            return redirect_user(
                request.htmx, reverse("performance:performance_peer_evaluation")
            )
        context.update({"selected_peer_evaluation": selected_peer_evaluation})
    else:
        context.update({"peer_evaluations": peer_evaluations})

    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/performance_management.html",
            "performance_and_learning_management_section",
            context,
        )
        if evaluation_id:
            response = push_url(
                response,
                reverse(
                    "performance:selected_performance_peer_evaluation",
                    kwargs={"evaluation_id": evaluation_id},
                ),
            )
        else:
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


def switch_performance_evalution(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_evaluation_url = data.get("selected_evaluation")
        return HttpResponseClientRedirect(selected_evaluation_url)


def submit_evaluation_rating(request, for_peer=""):
    context = {}
    if request.htmx and request.method == "POST":
        data = request.POST
        current_evaluation_id = data.get("current_evaluation")

        if "positive_feedback" in data:
            current_value = data.get("positive_feedback")
            modify_qualitative_content_data(
                current_evaluation_id, "positive_feedback", current_value
            )
        elif "improvement_suggestion" in data:
            current_value = data.get("improvement_suggestion")
            modify_qualitative_content_data(
                current_evaluation_id, "improvement_suggestion", current_value
            )
        else:
            modify_content_data_rating(data)

        current_evaluation = Evaluation.objects.get(id=current_evaluation_id)

        response = HttpResponse()
        if for_peer == "True":
            context.update({"selected_peer_evaluation": current_evaluation})
            response.content = render_block_to_string(
                "performance/performance_management.html",
                "peer_evaluation_counter_and_submit_section",
                context,
            )
            response = retarget(response, "#peer_evaluation_counter_and_submit_section")

        else:
            context.update({"current_evaluation": current_evaluation})
            response.content = render_block_to_string(
                "performance/performance_management.html",
                "evaluation_counter_and_submit_section",
                context,
            )
            response = retarget(response, "#evaluation_counter_and_submit_section")
        response = reswap(response, "outerHTML")
        return response


def submit_self_evaluation(request):
    context = {"evaluation_section": "self"}

    if request.htmx and request.method == "POST":
        data = request.POST
        current_evaluation_id = data.get("current_evaluation")
        current_evaluation = Evaluation.objects.get(id=current_evaluation_id)
        current_evaluation.date_submitted = make_aware(datetime.datetime.now())
        current_evaluation.save()

        current_user_evaluation = current_evaluation.user_evaluation

        user_evaluations = (
            current_user_evaluation.evaluatee.evaluatee_evaluations.filter(
                is_finalized=True
            ).order_by("-year")
        )

        current_submitted_evaluation_data = (
            current_user_evaluation.get_questionnaire_content_data_with_self_and_peer_rating_mean()
        )

        context.update(
            {
                "user_evaluations": user_evaluations,
                "current_user_evaluation": current_user_evaluation,
                "current_evaluation": current_evaluation,
                "current_submitted_evaluation_data": current_submitted_evaluation_data,
            }
        )

        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/performance_management.html",
            "performance_and_learning_management_section",
            context,
        )
        response = retarget(response, "#performance_and_learning_management_section")
        response = reswap(response, "outerHTML")
        return response


def submit_peer_evaluation(request):
    context = {"evaluation_section": "peer"}

    if request.htmx and request.method == "POST":
        data = request.POST
        current_evaluation_id = data.get("current_evaluation")
        current_evaluation = Evaluation.objects.get(id=current_evaluation_id)
        current_evaluation.date_submitted = make_aware(datetime.datetime.now())
        current_evaluation.save()

        current_user = current_evaluation.evaluator

        peer_evaluations = (
            current_user.evaluator_evaluations.exclude(
                user_evaluation__evaluatee=current_user
            )
            .filter(user_evaluation__is_finalized=True)
            .order_by("-user_evaluation__year")
        )

        context.update({"peer_evaluations": peer_evaluations})

        if request.htmx and request.method == "POST":
            response = HttpResponse()
            response.content = render_block_to_string(
                "performance/performance_management.html",
                "performance_and_learning_management_section",
                context,
            )
            response = push_url(
                response,
                reverse("performance:performance_peer_evaluation"),
            )
            response = retarget(
                response, "#performance_and_learning_management_section"
            )
            response = reswap(response, "outerHTML")
            return response


def switch_performance_management_section(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_evaluation_url = data.get("section")
        return HttpResponseClientRedirect(selected_evaluation_url)


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

    existing_evaluators = get_existing_evaluators_ids(user_evaluation)

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

    existing_evaluators = get_existing_evaluators_ids(user_evaluation)

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

        existing_evaluators = get_existing_evaluators_ids(user_evaluation)

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


def reset_evaluation(request):
    context = {}
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_evaluation_id = data.get("selected_evaluation")

        selected_evaluation = Evaluation.objects.get(id=selected_evaluation_id)

        reset_selected_evaluation(selected_evaluation)

        context.update({"evaluation": selected_evaluation})

        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/modify_user_evaluation.html",
            "evaluation_display",
            context,
        )

        response = reswap(response, "outerHTML")
        return response


def polls_management(request, poll_id=""):
    context = {}
    all_polls = Poll.objects.all().order_by("-created")
    context.update({"all_polls": all_polls})

    if request.htmx and request.method == "POST":
        data = request.POST
        poll_name = data.get("poll_name", "").strip()
        poll_description = data.get("poll_description", "").strip()
        current_poll = None

        if poll_id:
            current_poll = Poll.objects.get(id=poll_id)
            if not "for_redirect" in data:
                if poll_name:
                    current_poll.name = poll_name
                current_poll.description = poll_description
                current_poll.save()
        else:
            if not "for_redirect" in data:
                current_poll = Poll.objects.create(
                    name=poll_name, description=poll_description
                )

        if current_poll:
            context.update({"selected_poll": current_poll})

        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/polls_management.html",
            "polls_management_section",
            context,
        )
        if current_poll:
            response = push_url(
                response,
                reverse(
                    "performance:polls_management_with_selected_poll",
                    kwargs={"poll_id": current_poll.id},
                ),
            )
        else:
            response = push_url(
                response,
                reverse(
                    "performance:polls_management",
                ),
            )
        response = retarget(response, "#polls_management_section")
        response = reswap(response, "outerHTML")
        return response

    if poll_id:
        selected_poll = all_polls.get(id=poll_id)
        context.update({"selected_poll": selected_poll})

    return render(request, "performance/polls_management.html", context)


def modify_poll_choices(request, poll_id=""):
    context = {}
    all_polls = Poll.objects.all().order_by("-created")
    context.update({"all_polls": all_polls})
    current_poll = all_polls.get(id=poll_id)

    if request.htmx and request.method == "POST":
        data = request.POST
        item_to_remove = data.get("item_to_remove", "")

        response = HttpResponse()
        response = reswap(response, "outerHTML")

        if item_to_remove:
            updated_poll = remove_poll_choice(current_poll, item_to_remove)
        else:
            new_item = data.get("new_added_item", "")
            if not new_item or new_item.strip() == "":
                context.update(
                    {"add_poll_item_error_message": "Poll item could mot be blank."}
                )
            item_exists = check_item_already_exists_on_poll_choices(
                current_poll, new_item
            )
            if item_exists:
                context.update(
                    {"add_poll_item_error_message": "Poll item already added."}
                )
            if "add_poll_item_error_message" in context:
                response.content = render_block_to_string(
                    "performance/polls_management.html",
                    "new_item_error_display_section",
                    context,
                )
                response = retarget(response, "#new_item_error_display_section")
                return response

            updated_poll = add_poll_choice(current_poll, new_item)

        context.update({"selected_poll": updated_poll})

        response.content = render_block_to_string(
            "performance/polls_management.html",
            "polls_management_section",
            context,
        )
        response = retarget(response, "#polls_management_section")
        return response


def delete_selected_poll(request, poll_id=""):
    context = {}
    all_polls = Poll.objects.all().order_by("-created")
    context.update({"all_polls": all_polls})
    current_poll = all_polls.get(id=poll_id)

    if request.htmx and request.method == "DELETE":
        current_poll.delete()
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/polls_management.html",
            "polls_management_section",
            context,
        )
        response = push_url(
            response,
            reverse(
                "performance:polls_management",
            ),
        )
        response = retarget(response, "#polls_management_section")
        response = reswap(response, "outerHTML")
        return response

    if request.htmx and request.method == "POST":
        data = request.POST
        cancel_delete = "cancel_delete" in data
        context.update(
            {
                "for_delete_confirmation": not cancel_delete,
                "selected_poll": current_poll,
            }
        )
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/polls_management.html",
            "delete_poll_confirmation_section",
            context,
        )
        response = retarget(response, "#delete_poll_confirmation_section")
        response = reswap(response, "outerHTML")
        return response
