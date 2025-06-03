import mimetypes
import os
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Prefetch, Q
from django.http import FileResponse, HttpResponse
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

from core.actions import process_add_app_log_entry
from core.decorators import hr_required
from core.notification import create_notification
from performance.actions import (
    add_poll_choice,
    add_self_evaluation,
    modify_content_data_rating,
    modify_qualitative_content_data,
    modify_user_file_confidentiality,
    process_evaluator_modification,
    process_notify_all_user_for_new_post_or_poll,
    process_upload_resources,
    remove_poll_choice,
    reset_selected_evaluation,
    share_resource_to_user,
    submit_poll_choice,
)
from performance.forms import PostContentForm, PostForm
from performance.models import (
    Evaluation,
    Poll,
    Post,
    PostContent,
    SharedResource,
    UserEvaluation,
)
from performance.utils import (
    check_if_user_already_voted,
    check_if_user_is_evaluator,
    check_item_already_exists_on_poll_choices,
    get_existing_evaluators_ids,
    get_poll_and_post_combined_list,
    get_polls_and_posts_by_date_and_filter,
    get_user_evaluator_choices,
    get_users_for_shared_resources,
    get_users_per_shared_resources,
    get_users_shared_resources,
    get_year_and_quarter_from_user_evaluation,
    redirect_user,
)


# Performance Evaluation Section Views
@login_required(login_url="/login")
def performance_management(request):
    return redirect(reverse("performance:performance_evaluation"))


@login_required(login_url="/login")
def performance_evaluation(request):
    context = {"evaluation_section": "self"}
    current_user = request.user

    if current_user.userdetails.is_hr():
        return redirect(reverse("performance:performance_peer_evaluation"))

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


@login_required(login_url="/login")
def performance_peer_evaluation(request, evaluation_id=""):
    context = {"evaluation_section": "peer"}
    current_user = request.user
    context["user"] = current_user

    peer_evaluations = (
        current_user.evaluator_evaluations.select_related(
            "user_evaluation__evaluatee__userdetails"
        )
        .exclude(user_evaluation__evaluatee=current_user)
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


@login_required(login_url="/login")
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


@login_required(login_url="/login")
def submit_self_evaluation(request):
    context = {"evaluation_section": "self"}

    if request.htmx and request.method == "POST":
        data = request.POST
        current_evaluation_id = data.get("current_evaluation")
        current_evaluation = Evaluation.objects.get(id=current_evaluation_id)
        current_evaluation.date_submitted = make_aware(datetime.now())
        current_evaluation.save()

        process_add_app_log_entry(
            request.user.id,
            f"Submitted self evaluation {current_evaluation}.",
        )

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


@login_required(login_url="/login")
def submit_peer_evaluation(request):
    context = {"evaluation_section": "peer"}

    if request.htmx and request.method == "POST":
        data = request.POST
        current_evaluation_id = data.get("current_evaluation")
        current_evaluation = Evaluation.objects.get(id=current_evaluation_id)
        current_evaluation.date_submitted = make_aware(datetime.now())
        current_evaluation.save()

        process_add_app_log_entry(
            request.user.id,
            f"Submitted peer evaluation {current_evaluation}.",
        )

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


# Performance and Learning Management Section Switch View
@login_required(login_url="/login")
def switch_performance_management_section(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_evaluation_url = data.get("section")
        return HttpResponseClientRedirect(selected_evaluation_url)


# User Evaluation Management View
@login_required(login_url="/login")
@hr_required("/")
def user_evaluation_management(request, year=""):
    context = {}

    users = (
        User.objects.select_related("userdetails__department")
        .filter(is_superuser=False, is_active=True)
        .order_by("-userdetails__department")
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

    selected_year = request.POST.get("evaluation_year") or year or datetime.now().year
    selected_year = int(selected_year)

    first_quarter_value = UserEvaluation.Quarter.FIRST_QUARTER.value
    second_quarter_value = UserEvaluation.Quarter.SECOND_QUARTER.value

    # Prefetch evaluations for the selected year and quarters to avoid querying them individually later
    evaluations_qs = UserEvaluation.objects.filter(
        year=selected_year, quarter__in=[first_quarter_value, second_quarter_value]
    )
    users = users.prefetch_related(
        Prefetch("evaluatee_evaluations", queryset=evaluations_qs)
    )

    employee_details = []
    for user in users:
        first_quarter_evaluation = next(
            (
                eval
                for eval in user.evaluatee_evaluations.all()
                if eval.quarter == first_quarter_value
            ),
            None,
        )
        second_quarter_evaluation = next(
            (
                eval
                for eval in user.evaluatee_evaluations.all()
                if eval.quarter == second_quarter_value
            ),
            None,
        )

        employee_details.append(
            {
                "user": user,
                "current_first_quarter_user_evaluation": first_quarter_evaluation,
                "current_second_quarter_user_evaluation": second_quarter_evaluation,
            }
        )

    context.update(
        {
            "employee_details": employee_details,
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


@login_required(login_url="/login")
def modify_user_evaluation(request, pk, quarter, year=""):
    context = {}
    selected_user = User.objects.select_related("userdetails").get(id=pk)

    evaluator_choices = get_user_evaluator_choices(selected_user)

    selected_year = year or datetime.now().year
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

        existing_evaluations = user_evaluation.evaluations.select_related(
            "evaluator__userdetails", "questionnaire"
        ).all()
        context.update({"existing_evaluation_data": existing_evaluations})

    context.update(
        {
            "selected_user": selected_user,
            "evaluator_choices": evaluator_choices.select_related(
                "userdetails"
            ).exclude(pk__in=existing_evaluators),
            "selected_choices": evaluator_choices.select_related("userdetails").filter(
                pk__in=existing_evaluators
            ),
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


@login_required(login_url="/login")
def finalize_user_evaluation_toggle(request, user_evaluation_id):
    context = {}
    user = request.user
    user_evaluation = UserEvaluation.objects.get(id=user_evaluation_id)
    user_evaluation.is_finalized = not user_evaluation.is_finalized
    user_evaluation.save()

    process_add_app_log_entry(
        request.user.id,
        f"{'Finalized' if user_evaluation.is_finalized else 'Cancelled'} user evaluation of {user_evaluation.get_evaluatee_display()} {user_evaluation.get_year_and_quarter()}.",
    )

    selected_user = user_evaluation.evaluatee

    evaluator_choices = get_user_evaluator_choices(selected_user)

    year_and_quarter = get_year_and_quarter_from_user_evaluation(user_evaluation)

    existing_evaluators = get_existing_evaluators_ids(user_evaluation)

    if user_evaluation.is_finalized:
        create_notification(
            content=f"Your self-evaluation form is now available.",
            date=make_aware(datetime.now()),
            sender_id=user.id,
            recipient_id=user_evaluation.evaluatee.id,
            url=reverse("performance:performance_evaluation"),
        )

        evaluator_choices = evaluator_choices.filter(id__in=existing_evaluators)

        for evaluator_choice in evaluator_choices:
            create_notification(
                content=f"You are assigned as an evaluator of <b>{user_evaluation.get_evaluatee_display()}</b> for <b>{user_evaluation.get_year_and_quarter()}</b>.",
                date=make_aware(datetime.now()),
                sender_id=user.id,
                recipient_id=evaluator_choice.id,
                url=reverse("performance:performance_peer_evaluation"),
            )

        existing_evaluations = user_evaluation.evaluations.select_related(
            "evaluator__userdetails", "questionnaire"
        ).all()
        context.update({"existing_evaluation_data": existing_evaluations})

    context.update(
        {
            "selected_user": selected_user,
            "evaluator_choices": evaluator_choices.select_related(
                "userdetails"
            ).exclude(pk__in=existing_evaluators),
            "selected_choices": evaluator_choices.select_related("userdetails").filter(
                pk__in=existing_evaluators
            ),
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


@login_required(login_url="/login")
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

            existing_evaluations = user_evaluation.evaluations.select_related(
                "evaluator__userdetails", "questionnaire"
            ).all()
            context.update({"existing_evaluation_data": existing_evaluations})

        context.update(
            {
                "selected_user": selected_user,
                "evaluator_choices": evaluator_choices.select_related(
                    "userdetails"
                ).exclude(pk__in=existing_evaluators),
                "selected_choices": evaluator_choices.select_related(
                    "userdetails"
                ).filter(pk__in=existing_evaluators),
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


@login_required(login_url="/login")
def reset_evaluation(request):
    context = {}
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_evaluation_id = data.get("selected_evaluation")

        selected_evaluation = Evaluation.objects.get(id=selected_evaluation_id)

        reset_selected_evaluation(selected_evaluation)

        process_add_app_log_entry(
            request.user.id, f"User evaluation reset ({selected_evaluation})."
        )

        context.update({"evaluation": selected_evaluation})

        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/modify_user_evaluation.html",
            "evaluation_display",
            context,
        )

        response = reswap(response, "outerHTML")
        return response


# Poll and Post Section Views


@login_required(login_url="/login")
def poll_and_post_section(request):
    context = {}
    date_filter = request.POST.get("date_filter") or request.GET.get("date_filter")
    filters = request.POST.getlist("filter") or request.GET.getlist("filter")
    polls = get_polls_and_posts_by_date_and_filter(date_filter, filters)
    context.update(
        {"polls_and_posts": polls, "filters": filters, "date_filter": date_filter}
    )
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/poll_and_post_section.html",
            "poll_and_post_section",
            context,
        )

        filter_str = ""
        if filters:
            filter_str = f"?filter={'&filter='.join(filters)}"

        if date_filter:
            filter_str += (
                f"&date={date_filter}" if filter_str else f"?date={date_filter}"
            )

        response = push_url(
            response,
            reverse(
                "performance:poll_and_post_section",
            )
            + filter_str,
        )
        response = retarget(response, "#poll_and_post_section")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "performance/poll_and_post_section.html", context)


@login_required(login_url="/login")
def select_poll_content(request, content_id=""):
    context = {}
    user = request.user
    poll = Poll.objects.get(id=content_id)
    user_already_voted = check_if_user_already_voted(poll, user)
    context.update(
        {
            "selected_poll": poll,
            "user_already_voted": user_already_voted,
        }
    )
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/poll_and_post_section.html",
            "poll_and_post_static_modal_content",
            context,
        )
        response = trigger_client_event(
            response, "selectPollOrPostContent", after="swap"
        )
        response = retarget(response, "#poll_and_post_static_modal_content")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def select_post_content(request, content_id=""):
    context = {}
    post = Post.objects.get(id=content_id)
    context.update(
        {
            "selected_post": post,
        }
    )
    process_add_app_log_entry(request.user.id, f"Has viewed the {post.title} post.")
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/poll_and_post_section.html",
            "poll_and_post_static_modal_content",
            context,
        )
        response = trigger_client_event(
            response, "selectPollOrPostContent", after="swap"
        )
        response = retarget(response, "#poll_and_post_static_modal_content")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def submit_poll_vote(request, poll_id=""):
    context = {}
    user = request.user
    poll = Poll.objects.get(id=poll_id)
    if request.htmx and request.method == "POST":
        data = request.POST
        choice = data.get("selected_choice")
        poll = submit_poll_choice(poll, choice, user)
        user_already_voted = check_if_user_already_voted(poll, user)
        process_add_app_log_entry(
            request.user.id, f"Submitted a vote on poll {poll.name}."
        )
        context.update(
            {"selected_poll": poll, "user_already_voted": user_already_voted}
        )
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/poll_and_post_section.html",
            "poll_and_post_static_modal_content",
            context,
        )
        response = retarget(response, "#poll_and_post_static_modal_content")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def view_poll_result(request, poll_id=""):
    context = {}
    poll = Poll.objects.get(id=poll_id)
    if request.htmx and request.method == "POST":
        context.update({"selected_poll": poll, "show_poll_result": True})
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/poll_and_post_section.html",
            "poll_and_post_static_modal_content",
            context,
        )
        response = trigger_client_event(response, "showPollResult", after="swap")
        response = retarget(response, "#poll_and_post_static_modal_content")
        response = reswap(response, "outerHTML")
        return response


# Poll and Post Management Views
@login_required(login_url="/login")
@hr_required("/")
def poll_management(request, poll_id=""):
    context = {}
    poll_and_post_combined_list = get_poll_and_post_combined_list()
    context.update({"poll_and_post_combined_list": poll_and_post_combined_list})

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
                process_notify_all_user_for_new_post_or_poll(
                    request.user.id, type="POLL"
                )
                process_add_app_log_entry(
                    request.user.id, f"Created {current_poll.name} poll."
                )

        poll_and_post_combined_list = get_poll_and_post_combined_list()
        context.update({"poll_and_post_combined_list": poll_and_post_combined_list})

        if current_poll:
            context.update({"selected_poll": current_poll})

        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/poll_and_post_management.html",
            "poll_management_section",
            context,
        )
        if current_poll:
            response = push_url(
                response,
                reverse(
                    "performance:poll_management_with_selected_poll",
                    kwargs={"poll_id": current_poll.id},
                ),
            )
        else:
            response = push_url(
                response,
                reverse(
                    "performance:poll_management",
                ),
            )
        response = trigger_client_event(
            response, "showDescriptionPopover", after="swap"
        )
        response = retarget(response, "#poll_management_section")
        response = reswap(response, "outerHTML")
        return response

    if poll_id:
        selected_poll = Poll.objects.get(id=poll_id)
        context.update({"selected_poll": selected_poll})

    return render(request, "performance/poll_and_post_management.html", context)


@login_required(login_url="/login")
def post_management(request, post_id=""):
    context = {}
    poll_and_post_combined_list = get_poll_and_post_combined_list()
    context.update(
        {"for_post": True, "poll_and_post_combined_list": poll_and_post_combined_list}
    )

    if request.htmx and request.method == "POST":
        data = request.POST
        post_title = data.get("post_title", "").strip()
        post_description = data.get("post_description", "").strip()
        content = data.get("content", "")

        current_post = None

        if post_id:
            current_post = Post.objects.get(id=post_id)
            if not "for_redirect" in data:
                if post_title:
                    current_post.title = post_title
                current_post.description = post_description
                current_post.save()
                current_post.body.content = content
                current_post.body.save()
                if content != "":
                    process_notify_all_user_for_new_post_or_poll(request.user.id)

                process_add_app_log_entry(
                    request.user.id,
                    f"Modified {current_post.title} post. Current details: {{'title': {current_post.title}, 'description': {current_post.description}, 'content':{current_post.body.content}}}",
                )
        else:
            if not "for_redirect" in data:
                current_post = Post.objects.create(
                    title=post_title,
                    description=post_description,
                    body=PostContent.objects.create(),
                )
                process_add_app_log_entry(
                    request.user.id, f"Created {current_post.title} post."
                )

        poll_and_post_combined_list = get_poll_and_post_combined_list()
        context.update({"poll_and_post_combined_list": poll_and_post_combined_list})

        if current_post:
            current_content_form = PostContentForm(instance=current_post.body)
            context.update(
                {
                    "selected_post": current_post,
                    "current_content_form": current_content_form,
                }
            )

        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/poll_and_post_management.html",
            "poll_management_section",
            context,
        )
        if current_post:
            response = push_url(
                response,
                reverse(
                    "performance:post_management_with_selected_poll",
                    kwargs={"post_id": current_post.id},
                ),
            )
        else:
            response = push_url(
                response,
                reverse(
                    "performance:post_management",
                ),
            )
        response = trigger_client_event(
            response, "showDescriptionPopover", after="swap"
        )
        response = retarget(response, "#poll_management_section")
        response = reswap(response, "outerHTML")
        return response

    if post_id:
        selected_post = Post.objects.get(id=post_id)
        current_content_form = PostContentForm(instance=selected_post.body)
        context.update(
            {
                "selected_post": selected_post,
                "current_content_form": current_content_form,
            }
        )

    return render(request, "performance/poll_and_post_management.html", context)


@login_required(login_url="/login")
def poll_statistics(request, poll_id=""):
    context = {"show_poll_stats": True}
    poll_and_post_combined_list = get_poll_and_post_combined_list()
    context.update({"poll_and_post_combined_list": poll_and_post_combined_list})
    selected_poll = Poll.objects.get(id=poll_id)
    context.update({"selected_poll": selected_poll})

    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/poll_and_post_management.html",
            "poll_management_section",
            context,
        )

        response = push_url(
            response,
            reverse("performance:poll_statistics", kwargs={"poll_id": poll_id}),
        )
        response = trigger_client_event(response, "showStatGraph", after="swap")
        response = retarget(response, "#poll_management_section")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "performance/poll_and_post_management.html", context)


@login_required(login_url="/login")
def modify_poll_choices(request, poll_id=""):
    context = {}
    current_poll = Poll.objects.get(id=poll_id)

    if request.htmx and request.method == "POST":
        data = request.POST
        item_to_remove = data.get("item_to_remove", "")

        response = HttpResponse()
        response = reswap(response, "outerHTML")

        if item_to_remove:
            updated_poll = remove_poll_choice(current_poll, item_to_remove)
        else:
            new_item = data.get("new_added_item", "")
            poll_choice_color = data.get("poll_choice_color", "")

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
                    "performance/poll_and_post_management.html",
                    "new_item_error_display_section",
                    context,
                )
                response = retarget(response, "#new_item_error_display_section")
                return response

            updated_poll = add_poll_choice(current_poll, new_item, poll_choice_color)

        poll_and_post_combined_list = get_poll_and_post_combined_list()
        context.update(
            {
                "poll_and_post_combined_list": poll_and_post_combined_list,
                "selected_poll": updated_poll,
            }
        )

        response.content = render_block_to_string(
            "performance/poll_and_post_management.html",
            "poll_management_section",
            context,
        )
        response = retarget(response, "#poll_management_section")
        return response


@login_required(login_url="/login")
def delete_selected_poll(request, poll_id=""):
    context = {}
    current_poll = Poll.objects.get(id=poll_id)

    if request.htmx and request.method == "DELETE":
        process_add_app_log_entry(request.user.id, f"Deleted {current_poll.name} poll.")
        current_poll.delete()
        poll_and_post_combined_list = get_poll_and_post_combined_list()
        context.update({"poll_and_post_combined_list": poll_and_post_combined_list})
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/poll_and_post_management.html",
            "poll_management_section",
            context,
        )
        response = push_url(
            response,
            reverse(
                "performance:poll_management",
            ),
        )
        response = retarget(response, "#poll_management_section")
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
            "performance/poll_and_post_management.html",
            "delete_poll_confirmation_section",
            context,
        )
        response = retarget(response, "#delete_poll_confirmation_section")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def delete_selected_post(request, post_id=""):
    context = {"for_post": True}
    current_post = Post.objects.get(id=post_id)

    if request.htmx and request.method == "DELETE":
        process_add_app_log_entry(
            request.user.id, f"Deleted {current_post.title} post."
        )
        current_post.body.delete()
        current_post.delete()
        poll_and_post_combined_list = get_poll_and_post_combined_list()
        context.update({"poll_and_post_combined_list": poll_and_post_combined_list})

        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/poll_and_post_management.html",
            "poll_management_section",
            context,
        )
        response = push_url(
            response,
            reverse(
                "performance:post_management",
            ),
        )
        response = retarget(response, "#poll_management_section")
        response = reswap(response, "outerHTML")
        return response

    if request.htmx and request.method == "POST":
        data = request.POST
        cancel_delete = "cancel_delete" in data
        context.update(
            {
                "for_delete_confirmation": not cancel_delete,
                "selected_post": current_post,
            }
        )
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/poll_and_post_management.html",
            "delete_post_confirmation_section",
            context,
        )
        response = retarget(response, "#delete_post_confirmation_section")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def toggle_poll_status(request, poll_id=""):
    context = {}

    if request.htmx and request.method == "POST":
        poll = Poll.objects.get(id=poll_id)
        poll.in_progress = not poll.in_progress
        poll.save()

        process_add_app_log_entry(
            request.user.id,
            f"Marked {poll.name} poll as {"In Progress" if poll.in_progress else "Complete"}.",
        )

        context.update({"selected_poll": poll})
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/poll_and_post_management.html",
            "modify_poll_section",
            context,
        )
        response = retarget(response, "#modify_poll_section")
        response = reswap(response, "outerHTML")
        return response


# Shared Resources Section Views


@login_required(login_url="/login")
def shared_resources(request, user_id=""):
    context = {}
    user = request.user

    selected_user_id = request.POST.get("selected_user", user_id)
    if selected_user_id:
        selected_user_id = int(selected_user_id)

    search_query = request.POST.get("resource_search", "")

    shared_files = get_users_shared_resources(user.id, selected_user_id).filter(
        resource_name__icontains=search_query
    )

    user_choices = get_users_for_shared_resources(user)

    context.update(
        {
            "current_user": user,
            "shared_files": shared_files,
            "resource_search": search_query,
            "user_choices": user_choices.select_related("userdetails"),
            "selected_user": selected_user_id,
        }
    )

    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_resources_section.html",
            "shared_resources_section",
            context,
        )

        redirect_url = (
            reverse(
                "performance:shared_resources_with_user",
                kwargs={"user_id": selected_user_id},
            )
            if selected_user_id
            else reverse("performance:shared_resources")
        )

        response = push_url(response, redirect_url)
        response = retarget(response, "#shared_resources_section")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "performance/shared_resources_section.html", context)


@login_required(login_url="/login")
def upload_resources(request):
    context = {}
    user = request.user
    user_choices = get_users_for_shared_resources(user)
    context["user_choices"] = user_choices
    if request.htmx and request.method == "POST":
        shared_files, errors, new_shared_resource = process_upload_resources(
            user, request.FILES
        )
        response = HttpResponse()
        if errors:
            context.update(
                {
                    "current_user": user,
                    "file_upload_errors": errors,
                }
            )
            response.content = render_block_to_string(
                "performance/shared_resources_section.html",
                "file_upload_error_section",
                context,
            )
            response = push_url(response, reverse("performance:shared_resources"))
            response = retarget(response, "#file_upload_error_section")
            response = reswap(response, "outerHTML")
        else:
            process_add_app_log_entry(
                request.user.id,
                f"Uploaded a resource ({new_shared_resource.get_full_filename()}).",
            )
            context.update({"shared_files": shared_files})
            response.content = render_block_to_string(
                "performance/shared_resources_section.html",
                "shared_resources_section",
                context,
            )
            response = push_url(response, reverse("performance:shared_resources"))
            response = retarget(response, "#shared_resources_section")
            response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def download_resource(request, resource_id=""):
    context = {}
    user = request.user
    resource = SharedResource.objects.get(id=resource_id)

    # TODO: Raise error if user is not permitted
    # TODO: Raise error if file size is too large
    file = resource.resource

    file_name = file.name
    content_type, _ = mimetypes.guess_type(file_name)

    content_type_mapping = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".ppt": "application/vnd.ms-powerpoint",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".mp4": "video/mp4",
    }

    file_extension = resource.get_file_extension()
    content_type = content_type_mapping.get(
        f".{file_extension}", "application/octet-stream"
    )

    response = FileResponse(file, content_type=content_type)

    response["Content-Disposition"] = (
        f'attachment; filename="{os.path.basename(file_name)}"'
    )

    return response


@login_required(login_url="/login")
def delete_resource(request, resource_id=""):
    context = {}
    user = request.user
    user_choices = get_users_for_shared_resources(user)
    context["user_choices"] = user_choices
    if request.htmx and request.method == "DELETE":
        resource_to_delete = SharedResource.objects.get(id=resource_id)
        process_add_app_log_entry(
            request.user.id,
            f"Deleted a resource ({resource_to_delete.get_full_filename()}).",
        )
        resource_to_delete.resource.delete()
        resource_to_delete.resource_pdf.delete()
        resource_to_delete.delete()
        search_query = request.GET.get("q", "")
        shared_files = get_users_shared_resources(user).filter(
            resource_name__icontains=search_query
        )
        context.update(
            {
                "current_user": user,
                "shared_files": shared_files,
                "search_query": search_query,
            }
        )
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_resources_section.html",
            "shared_resources_section",
            context,
        )
        response = trigger_client_event(
            response, "closeDeleteConfirmationModal", after="swap"
        )
        response = retarget(response, "#shared_resources_section")
        response = reswap(response, "outerHTML")
        return response

    if request.htmx and request.method == "POST":
        resource_to_delete = SharedResource.objects.get(id=resource_id)
        context.update({"resource_to_delete": resource_to_delete})
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_resources_section.html",
            "delete_confirmation_modal_content",
            context,
        )
        response = trigger_client_event(
            response, "initializeDeleteConfirmationModal", after="swap"
        )
        response = retarget(response, "#delete_confirmation_modal_content")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def resource_share_access(request, resource_id=""):
    context = {}
    user = request.user
    if request.htmx and request.method == "POST":
        resource_to_share = SharedResource.objects.get(id=resource_id)
        user_choices = get_users_per_shared_resources(user, resource_to_share)
        selected_users = resource_to_share.shared_to.all()
        context.update(
            {
                "resource_to_share": resource_to_share,
                "user_choices": user_choices.select_related("userdetails"),
                "selected_users": selected_users,
            }
        )
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_resources_section.html",
            "file_access_sharing_modal_content",
            context,
        )
        response = trigger_client_event(
            response, "initializeShareAccessModal", after="swap"
        )
        response = retarget(response, "#file_access_sharing_modal_content")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def resource_modify_users_with_share_access(request, resource_id=""):
    context = {}
    user = request.user
    if request.htmx and request.method == "POST":
        resource_to_share = SharedResource.objects.get(id=resource_id)
        selected_user_id = request.POST.get("selected_user", "") or request.POST.get(
            "selected_user_to_remove", ""
        )
        to_remove = "selected_user_to_remove" in request.POST
        resource_to_share = share_resource_to_user(
            resource_to_share,
            selected_user_id,
            to_remove,
        )
        user_choices = get_users_per_shared_resources(user, resource_to_share)
        selected_users = resource_to_share.shared_to.all()
        context.update(
            {
                "resource_to_share": resource_to_share,
                "user_choices": user_choices.select_related("userdetails"),
                "selected_users": selected_users,
            }
        )
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_resources_section.html",
            "file_access_sharing_modal_content",
            context,
        )
        response = trigger_client_event(
            response,
            "updateFileListAfterUpdate",
            after="swap",
        )
        response = retarget(response, "#file_access_sharing_modal_content")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def resource_update_file_list_after_modifying_share_access(request):
    context = {}
    user = request.user
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_user_id = data.get("selected_user_id", "")
        resource_search = data.get("resource_search", "")

        shared_files = get_users_shared_resources(user.id, selected_user_id).filter(
            resource_name__icontains=resource_search
        )

        context.update({"current_user": user, "shared_files": shared_files})

        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_resources_section.html",
            "file_list_content",
            context,
        )
        response = retarget(response, "#file_list_content")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def preview_resource(request, resource_id=""):
    context = {}
    user = request.user
    if request.htmx and request.method == "POST":
        resource_to_preview = SharedResource.objects.get(id=resource_id)
        user_has_access = not resource_to_preview.is_confidential or (
            resource_to_preview.is_confidential
            and user in resource_to_preview.confidential_access_users.all()
        )
        context.update(
            {
                "resource_to_preview": resource_to_preview,
                "user_has_access": user_has_access,
            }
        )
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_resources_section.html",
            "preview_file_modal_content",
            context,
        )
        event_name = (
            "initializeDocumentPreview"
            if not resource_to_preview.is_resource_media()
            else "initializeMediaPreview"
        )
        response = trigger_client_event(response, event_name, after="swap")
        response = retarget(response, "#preview_file_modal_content")
        response = reswap(response, "outerHTML")
        return response


# Shared Resources Management Views
@login_required(login_url="/login")
@hr_required("/")
def shared_resources_management(request, user_id=""):
    context = {}
    user = request.user
    user_choices = get_users_for_shared_resources(user)

    selected_user_id = request.POST.get("selected_user", user_id)
    if selected_user_id:
        selected_user_id = int(selected_user_id)

    search_query = request.POST.get("resource_search", "")

    shared_files = get_users_shared_resources(user.id, selected_user_id).filter(
        resource_name__icontains=search_query
    )

    context.update(
        {
            "current_user": user,
            "shared_files": shared_files,
            "search_query": "",
            "user_choices": user_choices.select_related("userdetails"),
            "selected_user": selected_user_id,
            "search_query": search_query,
        }
    )
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_resources_management.html",
            "shared_resources_management_section",
            context,
        )

        redirect_url = (
            reverse(
                "performance:shared_resources_management_with_user",
                kwargs={"user_id": selected_user_id},
            )
            if selected_user_id
            else reverse("performance:shared_resources_management")
        )

        response = push_url(response, redirect_url)

        response = retarget(response, "#shared_resources_management_section")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "performance/shared_resources_management.html", context)


@login_required(login_url="/login")
def shared_resources_management_upload(request):
    context = {}
    user = request.user
    if request.htmx and request.method == "POST":
        shared_files, errors, new_shared_resource = process_upload_resources(
            user, request.FILES
        )
        user_choices = get_users_for_shared_resources(user)
        context["user_choices"] = user_choices
        response = HttpResponse()
        if errors:
            context.update({"current_user": user, "file_upload_errors": errors})
            response.content = render_block_to_string(
                "performance/shared_resources_section.html",
                "file_upload_error_section",
                context,
            )
            response = push_url(response, reverse("performance:shared_resources"))
            response = retarget(response, "#file_upload_error_section")
            response = reswap(response, "outerHTML")
        else:
            process_add_app_log_entry(
                request.user.id,
                f"Uploaded a resource ({new_shared_resource.get_full_filename()}).",
            )
            context.update({"shared_files": shared_files})
            response.content = render_block_to_string(
                "performance/shared_resources_management.html",
                "shared_resources_management_section",
                context,
            )
            response = push_url(
                response, reverse("performance:shared_resources_management")
            )
            response = retarget(response, "#shared_resources_management_section")
            response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def shared_resources_management_preview_resource(request, resource_id=""):
    context = {}
    if request.htmx and request.method == "POST":
        resource_to_preview = SharedResource.objects.get(id=resource_id)
        context.update({"resource_to_preview": resource_to_preview})
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_resources_management.html",
            "preview_file_modal_content",
            context,
        )
        event_name = (
            "initializeDocumentPreview"
            if not resource_to_preview.is_resource_media()
            else "initializeMediaPreview"
        )
        response = trigger_client_event(response, event_name, after="swap")
        response = retarget(response, "#preview_file_modal_content")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def shared_resource_management_delete(request, resource_id=""):
    context = {}
    user = request.user
    if request.htmx and request.method == "DELETE":
        user_choices = get_users_for_shared_resources(user)
        context["user_choices"] = user_choices
        resource_to_delete = SharedResource.objects.get(id=resource_id)
        process_add_app_log_entry(
            request.user.id,
            f"Deleted a resource ({resource_to_delete.get_full_filename()}).",
        )
        resource_to_delete.resource.delete()
        resource_to_delete.resource_pdf.delete()
        resource_to_delete.delete()
        search_query = request.GET.get("q", "")
        shared_files = get_users_shared_resources(user).filter(
            resource_name__icontains=search_query
        )
        context.update(
            {
                "current_user": user,
                "shared_files": shared_files,
                "search_query": search_query,
            }
        )
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_resources_management.html",
            "shared_resources_management_section",
            context,
        )
        response = trigger_client_event(
            response, "closeDeleteConfirmationModal", after="swap"
        )
        response = retarget(response, "#shared_resources_management_section")
        response = reswap(response, "outerHTML")
        return response

    if request.htmx and request.method == "POST":
        resource_to_delete = SharedResource.objects.get(id=resource_id)
        context.update({"resource_to_delete": resource_to_delete})
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_resources_management.html",
            "resource_management_delete_confirmation_modal_content",
            context,
        )
        response = trigger_client_event(
            response, "initializeDeleteConfirmationModal", after="swap"
        )
        response = retarget(
            response, "#resource_management_delete_confirmation_modal_content"
        )
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def shared_resource_management_share_access(request, resource_id=""):
    context = {}
    user = request.user
    if request.htmx and request.method == "POST":
        resource_to_share = SharedResource.objects.get(id=resource_id)
        user_choices = get_users_per_shared_resources(user, resource_to_share)
        selected_users = resource_to_share.shared_to.all()
        context.update(
            {
                "resource_to_share": resource_to_share,
                "user_choices": user_choices.select_related("userdetails"),
                "selected_users": selected_users,
            }
        )
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_resources_management.html",
            "file_access_sharing_modal_content",
            context,
        )
        response = trigger_client_event(
            response, "initializeShareAccessModal", after="swap"
        )
        response = retarget(response, "#file_access_sharing_modal_content")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def shared_resource_management_confidential_state_toggle(request, resource_id=""):
    context = {}
    user = request.user
    if request.htmx and request.method == "POST":
        resource_to_toggle = SharedResource.objects.get(id=resource_id)
        resource_to_toggle.is_confidential = not resource_to_toggle.is_confidential
        if not resource_to_toggle.is_confidential:
            resource_to_toggle.confidential_access_users.clear()
        resource_to_toggle.save()

        process_add_app_log_entry(
            request.user.id,
            f"Marked {resource_to_toggle.get_full_filename()} as {"confidential" if resource_to_toggle.is_confidential else "nonconfidential"}.",
        )

        user_choices = get_users_per_shared_resources(user, resource_to_toggle)
        selected_users = resource_to_toggle.shared_to.all()

        context.update(
            {
                "resource_to_share": resource_to_toggle,
                "user_choices": user_choices.select_related("userdetails"),
                "selected_users": selected_users,
            }
        )

        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_resources_management.html",
            "file_access_sharing_modal_content",
            context,
        )

        response = retarget(response, "#file_access_sharing_modal_content")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def shared_resource_management_modify_user_confidential_access(request):
    context = {}
    if request.htmx and request.method == "POST":
        data = request.POST
        resource_id = data.get("resource_id", "")
        selected_user_id = data.get("selected_user_id", "")
        resource, selected_user = modify_user_file_confidentiality(
            resource_id, selected_user_id
        )
        process_add_app_log_entry(
            request.user.id,
            f"{"Granted" if selected_user in resource.confidential_access_users.all() else "Removed"} {selected_user.userdetails.get_user_fullname()} confidential access to {resource.get_full_filename()}.",
        )
        context.update({"resource_to_share": resource, "user": selected_user})
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_resources_management.html",
            "user_confidential_switch",
            context,
        )
        response = retarget(response, "#user_confidential_switch")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def shared_resource_management_modify_users_with_share_access(request, resource_id=""):
    context = {}
    user = request.user
    if request.htmx and request.method == "POST":
        resource_to_share = SharedResource.objects.get(id=resource_id)
        selected_user_id = request.POST.get("selected_user", "") or request.POST.get(
            "selected_user_to_remove", ""
        )
        to_remove = "selected_user_to_remove" in request.POST
        resource_to_share = share_resource_to_user(
            resource_to_share,
            selected_user_id,
            to_remove,
        )
        user_choices = get_users_per_shared_resources(user, resource_to_share)
        selected_users = resource_to_share.shared_to.all()
        if to_remove:
            process_add_app_log_entry(
                request.user.id,
                f"Removed {user_choices.get(id=selected_user_id).userdetails.get_user_fullname()} access to {resource_to_share.get_full_filename()}.",
            )
        else:
            process_add_app_log_entry(
                request.user.id,
                f"Added {selected_users.get(id=selected_user_id).userdetails.get_user_fullname()} access to {resource_to_share.get_full_filename()}.",
            )

        context.update(
            {
                "current_user": user,
                "resource_to_share": resource_to_share,
                "user_choices": user_choices.select_related("userdetails"),
                "selected_users": selected_users,
            }
        )
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_resources_management.html",
            "file_access_sharing_modal_content",
            context,
        )
        response = trigger_client_event(
            response,
            "updateFileListAfterUpdate",
            after="swap",
        )
        response = retarget(response, "#file_access_sharing_modal_content")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def shared_resource_management_update_file_list_after_modifying_share_access(request):
    context = {}
    user = request.user
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_user_id = data.get("selected_user_id", "")
        resource_search = data.get("resource_search", "")

        shared_files = get_users_shared_resources(user.id, selected_user_id).filter(
            resource_name__icontains=resource_search
        )

        context.update({"current_user": user, "shared_files": shared_files})

        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_resources_management.html",
            "file_list_content",
            context,
        )
        response = retarget(response, "#file_list_content")
        response = reswap(response, "outerHTML")
        return response


# App Shared View
def performance_module_close_modals(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        event_name = data.get("event_name")
        response = HttpResponse()
        response = trigger_client_event(response, event_name, after="swap")
        response = reswap(response, "none")
        return response
