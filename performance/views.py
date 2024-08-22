import datetime
import mimetypes
import os

from django.contrib.auth.models import User
from django.db.models import Q
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

from performance.actions import (
    add_poll_choice,
    add_self_evaluation,
    modify_content_data_rating,
    modify_qualitative_content_data,
    process_evaluator_modification,
    process_upload_documents,
    remove_poll_choice,
    reset_selected_evaluation,
    submit_poll_choice,
)
from performance.forms import PostContentForm, PostForm
from performance.models import (
    Evaluation,
    Poll,
    Post,
    PostContent,
    SharedDocument,
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
    get_user_shared_files,
    get_year_and_quarter_from_user_evaluation,
    redirect_user,
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


def select_post_content(request, content_id=""):
    context = {}
    user = request.user
    post = Post.objects.get(id=content_id)
    context.update(
        {
            "selected_post": post,
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


def close_content_modal(request):
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response = trigger_client_event(response, "closePollContent", after="swap")
        return response


def submit_poll_vote(request, poll_id=""):
    context = {}
    user = request.user
    poll = Poll.objects.get(id=poll_id)
    if request.htmx and request.method == "POST":
        data = request.POST
        choice = data.get("selected_choice")
        poll = submit_poll_choice(poll, choice, user)
        user_already_voted = check_if_user_already_voted(poll, user)
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
        else:
            if not "for_redirect" in data:
                current_post = Post.objects.create(
                    title=post_title,
                    description=post_description,
                    body=PostContent.objects.create(),
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


def delete_selected_poll(request, poll_id=""):
    context = {}
    current_poll = Poll.objects.get(id=poll_id)

    if request.htmx and request.method == "DELETE":
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


def delete_selected_post(request, post_id=""):
    context = {"for_post": True}
    current_post = Post.objects.get(id=post_id)

    if request.htmx and request.method == "DELETE":
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


def toggle_poll_status(request, poll_id=""):
    context = {}

    if request.htmx and request.method == "POST":
        poll = Poll.objects.get(id=poll_id)
        poll.in_progress = not poll.in_progress
        poll.save()

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


# Shared Document Views


def shared_documents(request):
    context = {}
    user = request.user
    search_query = request.GET.get("q", "")
    shared_files = get_user_shared_files(user).filter(
        document_name__icontains=search_query
    )
    context.update({"shared_files": shared_files, "search_query": search_query})
    return render(request, "performance/shared_documents_section.html", context)


def upload_documents(request):
    context = {}
    user = request.user
    if request.htmx and request.method == "POST":
        shared_files, errors = process_upload_documents(user, request.FILES)
        response = HttpResponse()
        if errors:
            context.update({"file_upload_errors": errors})
            response.content = render_block_to_string(
                "performance/shared_documents_section.html",
                "file_upload_error_section",
                context,
            )
            response = push_url(response, reverse("performance:shared_documents"))
            response = retarget(response, "#file_upload_error_section")
            response = reswap(response, "outerHTML")
        else:
            context.update({"shared_files": shared_files})
            response.content = render_block_to_string(
                "performance/shared_documents_section.html",
                "shared_documents_section",
                context,
            )
            response = push_url(response, reverse("performance:shared_documents"))
            response = retarget(response, "#shared_documents_section")
            response = reswap(response, "outerHTML")
        return response


def search_documents(request):
    context = {}
    user = request.user
    if request.htmx and request.method == "POST":
        data = request.POST
        search_query = data.get("document_search", "")
        shared_files = get_user_shared_files(user).filter(
            document_name__icontains=search_query
        )
        context.update({"shared_files": shared_files, "search_query": search_query})
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_documents_section.html",
            "shared_documents_section",
            context,
        )

        redirect_url = reverse("performance:shared_documents")
        if search_query:
            redirect_url += f"?q={search_query}" if search_query else ""

        response = push_url(response, redirect_url)
        response = retarget(response, "#shared_documents_section")
        response = reswap(response, "outerHTML")
        return response


def download_document(request, document_id=""):
    context = {}
    user = request.user
    document = SharedDocument.objects.get(id=document_id)

    # TODO: Raise error if user is not permitted
    # TODO: Raise error if file size is too large
    file = document.document

    file_name = file.name
    content_type, _ = mimetypes.guess_type(file_name)

    if content_type is None:
        if file_name.lower().endswith(".doc"):
            content_type = "application/msword"
        elif file_name.lower().endswith(".docx"):
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            content_type = "application/octet-stream"

    response = FileResponse(file, content_type=content_type)
    response["Content-Disposition"] = (
        f'attachment; filename="{os.path.basename(file_name)}"'
    )

    return response


def delete_document(request, document_id=""):
    context = {}
    user = request.user
    if request.htmx and request.method == "DELETE":
        document_to_delete = SharedDocument.objects.get(id=document_id)
        document_to_delete.document.delete()
        document_to_delete.document_pdf.delete()
        document_to_delete.delete()
        search_query = request.GET.get("q", "")
        shared_files = get_user_shared_files(user).filter(
            document_name__icontains=search_query
        )
        context.update({"shared_files": shared_files, "search_query": search_query})
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_documents_section.html",
            "shared_documents_section",
            context,
        )
        response = trigger_client_event(
            response, "closeDeleteConfirmationModal", after="swap"
        )
        response = retarget(response, "#shared_documents_section")
        response = reswap(response, "outerHTML")
        return response

    if request.htmx and request.method == "POST":
        document_to_delete = SharedDocument.objects.get(id=document_id)
        context.update({"document_to_delete": document_to_delete})
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_documents_section.html",
            "delete_confirmation_modal_content",
            context,
        )
        response = trigger_client_event(
            response, "initializeDeleteConfirmationModal", after="swap"
        )
        response = retarget(response, "#delete_confirmation_modal_content")
        response = reswap(response, "outerHTML")
        return response


def close_delete_confirmation_modal(request):
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response = trigger_client_event(
            response, "closeDeleteConfirmationModal", after="swap"
        )
        return response


def preview_document(request, document_id=""):
    context = {}
    if request.htmx and request.method == "POST":
        document_to_preview = SharedDocument.objects.get(id=document_id)
        context.update({"document_to_preview": document_to_preview})
        response = HttpResponse()
        response.content = render_block_to_string(
            "performance/shared_documents_section.html",
            "preview_file_modal_content",
            context,
        )
        response = trigger_client_event(
            response, "initializePreviewFileModal", after="swap"
        )
        response = retarget(response, "#preview_file_modal_content")
        response = reswap(response, "outerHTML")
        return response


def close_preview_file_modal(request):
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response = trigger_client_event(response, "closePreviewFileModal", after="swap")
        return response
