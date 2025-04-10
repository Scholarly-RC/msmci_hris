from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, QueryDict
from django.shortcuts import render
from django.urls import reverse
from django.utils.timezone import make_aware
from django_htmx.http import reswap, retarget, trigger_client_event
from render_block import render_block_to_string

from attendance.utils.date_utils import get_list_of_months
from core.actions import process_add_app_log_entry
from core.decorators import hr_required
from core.notification import create_notification
from core.utils import get_users_sorted_by_department
from hris.utils import create_global_alert_instance
from leave.actions import (
    process_add_user_used_leave_credits,
    process_create_leave_request,
    process_delete_submit_leave_request,
    process_reset_user_leave_credits,
    process_set_department_approver,
    process_set_user_leave_credit,
    process_submit_leave_request_response,
)
from leave.enums import LeaveRequestAction
from leave.models import Leave
from leave.utils import (
    get_approvers_per_department,
    get_department_heads,
    get_directors,
    get_leave_to_review,
    get_leave_types,
    get_leave_year_list,
    get_presidents,
    get_user_leave,
)
from payroll.utils import get_department_list
from performance.utils import get_user_with_hr_role


# Create your views here.
@login_required(login_url="/login")
def user_leave(request):
    context = {}
    user = request.user
    leave = get_user_leave(user)
    context.update(
        {
            "leave_data": leave,
            "approver": not user.userdetails.is_employee(),
            "total_leave_credits": user.leavecredit.credits,
            "remaining_leave_credits": user.leavecredit.get_remaining_leave_credits(),
        }
    )
    return render(request, "leave/user_leave.html", context)


@login_required(login_url="/login")
def user_leave_request(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        user = request.user
        if request.method == "GET":
            data = request.GET
            leave_types = get_leave_types()

            has_remaining_leave_credits = user.leavecredit.get_remaining_leave_credits()
            context.update(
                {
                    "leave_types": leave_types,
                    "has_remaining_leave_credits": has_remaining_leave_credits,
                }
            )
            response.content = render_block_to_string(
                "leave/user_leave.html",
                "create_leave_request_container",
                context,
            )
            response = trigger_client_event(
                response, "openCreateLeaveRequestModal", after="swap"
            )
            response = retarget(response, "#create_leave_request_container")
            response = reswap(response, "outerHTML")
            return response

        if request.method == "POST":
            try:
                data = request.POST
                new_leave = process_create_leave_request(user, data)
                leave = get_user_leave(user)
                context["leave_data"] = leave

                create_notification(
                    content=f"A leave request has been submitted by <b>{new_leave.user.userdetails.get_user_fullname()}</b> and is awaiting your response.",
                    date=make_aware(datetime.now()),
                    sender_id=new_leave.user.id,
                    recipient_id=new_leave.first_approver_data["approver"],
                    url=reverse("leave:user_leave"),
                )

                response.content = render_block_to_string(
                    "leave/user_leave.html",
                    "leave_list",
                    context,
                )
                process_add_app_log_entry(
                    request.user.id, f"Created a leave request ({new_leave})."
                )
                response = create_global_alert_instance(
                    response, "Leave request created successfully.", "SUCCESS"
                )
                response = trigger_client_event(
                    response, "closeCreateLeaveRequestModal", after="swap"
                )
                response = retarget(response, "#leave_list")
                response = reswap(response, "outerHTML")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while creating the leave request: {error}",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response


@login_required(login_url="/login")
def user_review_leave_request(request):
    context = {}
    if request.htmx:
        user = request.user
        response = HttpResponse()
        if request.method == "GET":

            leave_to_review = get_leave_to_review(user)

            context["leave_data"] = leave_to_review

            response.content = render_block_to_string(
                "leave/user_leave.html",
                "review_leave_request_container",
                context,
            )

            response = trigger_client_event(
                response, "openReviewLeaveRequestModal", after="swap"
            )
            response = retarget(response, "#review_leave_request_container")
            response = reswap(response, "outerHTML")
            return response

        if request.method == "POST":
            try:
                data = request.POST
                leave = process_submit_leave_request_response(user, data)
                user_response = leave.get_user_status(user)
                context["leave"] = leave, user_response

                create_notification(
                    content=f"<b>{user.userdetails.get_user_fullname()}</b> has <b>{user_response}</b> your leave request dated <b>{leave.date}</b>.",
                    date=make_aware(datetime.now()),
                    sender_id=leave.get_first_approver().id,
                    recipient_id=leave.user.id,
                    url=reverse("leave:user_leave"),
                )

                if user_response == LeaveRequestAction.APPROVED.value:
                    create_notification(
                        content=f"<b>{user.userdetails.get_user_fullname()}</b> has <b>{user_response}</b> the leave request of <b>{leave.user.userdetails.get_user_fullname()}</b> on <b>{leave.date}</b>.",
                        date=make_aware(datetime.now()),
                        sender_id=leave.get_first_approver().id,
                        recipient_id=leave.get_second_approver().id,
                        url=reverse("leave:leave_management"),
                    )

                response.content = render_block_to_string(
                    "leave/user_leave.html",
                    "review_leave_request_card",
                    context,
                )
                process_add_app_log_entry(
                    request.user.id, f"{user_response} a leave request ({leave})."
                )
                response = create_global_alert_instance(
                    response,
                    f"You have {user_response} the Leave request by {leave.user.userdetails.get_user_fullname()} on {leave.date}.",
                    type="SUCCESS",
                )
                response = retarget(response, "closest .review-leave-request-card")
                response = reswap(response, "outerHTML")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error has occured while responing to the selected leave request. Details: {error}",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response


@login_required(login_url="/login")
@hr_required("/")
def leave_management(request):
    context = {}
    user = request.user
    users = get_users_sorted_by_department()
    selected_month = request.POST.get("selected_month") or 0
    selected_year = request.POST.get("selected_year") or 0
    months = get_list_of_months()
    years = get_leave_year_list()
    selected_user_id = request.POST.get("selected_user") or 0
    leave_to_review = get_leave_to_review(
        user=user,
        specific_user_id=selected_user_id,
        month=selected_month,
        year=selected_year,
    )
    context.update(
        {
            "current_user": user,
            "leave_data": leave_to_review,
            "users": users.select_related("leavecredit"),
            "months": months,
            "years": years,
            "selected_user_id": int(selected_user_id),
            "selected_month": int(selected_month),
            "selected_year": int(selected_year),
        }
    )

    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "leave/leave_management.html",
            "leave_management_section",
            context,
        )
        response = retarget(response, "#leave_management_section")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "leave/leave_management.html", context)


@login_required(login_url="/login")
def review_leave_request(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        user = request.user
        if request.method == "POST":
            try:
                data = request.POST
                leave = process_submit_leave_request_response(user, data)
                user_response = leave.get_user_status(user)
                context["leave"] = leave, user_response
                create_notification(
                    content=f"<b>{user.userdetails.get_user_fullname()}</b> has <b>{user_response}</b> your leave request dated <b>{leave.date}</b>.",
                    date=make_aware(datetime.now()),
                    sender_id=leave.get_first_approver().id,
                    recipient_id=leave.user.id,
                    url=reverse("leave:user_leave"),
                )

                if (
                    user_response == LeaveRequestAction.APPROVED.value
                    and leave.type == Leave.LeaveType.PAID.value
                ):
                    process_add_user_used_leave_credits(leave.user)

                response.content = render_block_to_string(
                    "leave/leave_management.html",
                    "review_leave_request_card",
                    context,
                )
                process_add_app_log_entry(
                    request.user.id, f"{user_response} a leave request ({leave})."
                )
                response = create_global_alert_instance(
                    response,
                    f"You have {user_response} the leave request submitted by {leave.user.userdetails.get_user_fullname()} on {leave.date}.",
                    type="SUCCESS",
                )
                response = retarget(response, "closest .review-leave-request-card")
                response = reswap(response, "outerHTML")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while processing the selected leave request. Details: {error}",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response


@login_required(login_url="/login")
def delete_leave_request(request, leave_id=""):
    context = {}
    if request.htmx:
        response = HttpResponse()
        user = request.user
        leave = Leave.objects.get(id=leave_id)
        if request.method == "DELETE":
            data = QueryDict(request.body)
            context.update(data)
            deleted_leave_details = process_delete_submit_leave_request(leave)

            selected_user = data.get("selected_user")
            selected_month = data.get("selected_month")
            selected_year = data.get("selected_year")
            leave_to_review = get_leave_to_review(
                user,
                specific_user_id=selected_user,
                month=selected_month,
                year=selected_year,
            )
            context["leave_data"] = leave_to_review
            process_add_app_log_entry(
                request.user.id, f"Deleted a leave request ({deleted_leave_details})."
            )
            response = create_global_alert_instance(
                response,
                "The selected leave request has been deleted successfully.",
                "SUCCESS",
            )
            response = retarget(response, "#leave_list")
            response = reswap(response, "outerHTML")

        if request.method == "POST":
            data = request.POST
            user_response = leave.get_user_status(user)
            context["leave"] = leave, user_response
            if not "cancel" in data:
                context["delete_confirmation"] = True
            response.content = render_block_to_string(
                "leave/leave_management.html",
                "leave_card_button_group",
                context,
            )
            response = retarget(response, "closest .leave-card-button-group")
            response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def approver_settings(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            departments = get_department_list()
            if "selected_department" in request.GET:
                selected_department = departments.get(
                    id=request.GET.get("selected_department")
                )
            else:
                selected_department = departments.first()

            approvers_context = get_approvers_per_department(selected_department)
            context.update(approvers_context)
            context.update(
                {
                    "departments": departments,
                    "selected_department": selected_department,
                    "department_heads": get_department_heads(
                        selected_department=selected_department
                    ),
                    "directors": get_directors(),
                    "presidents": get_presidents(),
                    "hrs": get_user_with_hr_role(),
                }
            )
            response.content = render_block_to_string(
                "leave/leave_management.html",
                "approver_settings_container",
                context,
            )
            response = trigger_client_event(
                response, "openApproverSettingsModal", after="swap"
            )
            response = retarget(response, "#approver_settings_container")
            response = reswap(response, "outerHTML")
            return response

        if request.method == "POST":
            try:
                data = request.POST
                leave_approver = process_set_department_approver(data)
                process_add_app_log_entry(
                    request.user.id,
                    f"Updated approver settings. Details: ({leave_approver})",
                )
                response = create_global_alert_instance(
                    response,
                    f"The leave approvers for the department '{leave_approver.department}' have been successfully set.",
                    "SUCCESS",
                )
                response = reswap(response, "none")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while updating approvers for the selected department. Details: {error}",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response


@login_required(login_url="/login")
def leave_credit_settings(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            users = get_users_sorted_by_department()
            context["users"] = users.select_related("leavecredit")
            response.content = render_block_to_string(
                "leave/leave_management.html",
                "leave_credit_settings_container",
                context,
            )
            response = trigger_client_event(
                response, "openLeaveCreditSettingsModal", after="swap"
            )
            response = retarget(response, "#leave_credit_settings_container")
            response = reswap(response, "outerHTML")
            return response


@login_required(login_url="/login")
def update_leave_credit_settings_list(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "POST":
            users = get_users_sorted_by_department()
            context["users"] = users.select_related("leavecredit")
            response.content = render_block_to_string(
                "leave/leave_management.html",
                "leave_credit_settings_container",
                context,
            )
            response = retarget(response, "#leave_credit_settings_container")
            response = reswap(response, "outerHTML")
            return response


@login_required(login_url="/login")
def edit_leave_credit_settings(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            data = request.GET
            if "back" in data:
                response = trigger_client_event(
                    response, "closeEditUserLeaveCreditSettingsModal", after="swap"
                )
                response = trigger_client_event(
                    response, "openLeaveCreditSettingsModal", after="swap"
                )
                response = reswap(response, "none")
                return response

            user_id = data.get("user")
            context["user"] = User.objects.get(id=user_id)
            response.content = render_block_to_string(
                "leave/leave_management.html",
                "edit_user_leave_credit_settings_container",
                context,
            )
            response = trigger_client_event(
                response, "openEditUserLeaveCreditSettingsModal", after="swap"
            )
            response = trigger_client_event(
                response, "closeLeaveCreditSettingsModal", after="swap"
            )
            response = retarget(response, "#edit_user_leave_credit_settings_container")
            response = reswap(response, "outerHTML")
            return response

        if request.method == "POST":
            try:
                data = request.POST
                leave_credit, user = process_set_user_leave_credit(data)
                context.update({"user": user})
                response.content = render_block_to_string(
                    "leave/leave_management.html",
                    "edit_user_leave_credit_settings_container",
                    context,
                )
                process_add_app_log_entry(
                    request.user.id,
                    f"Updated user ({user.userdetails.get_user_fullname()}) leave credit. Details: {leave_credit.credits}.",
                )
                response = create_global_alert_instance(
                    response,
                    f"Leave credit of selected user has been successfully updated.",
                    "SUCCESS",
                )
                response = trigger_client_event(
                    response, "updateleaveCreditList", after="swap"
                )
                response = retarget(
                    response, "#edit_user_leave_credit_settings_container"
                )
                response = reswap(response, "outerHTML")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"Something went wrong while updating the selected user's leave credit. Details: {error}",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response


@login_required(login_url="/login")
def reset_used_leave_credits(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            data = request.GET
            if not "cancel" in data:
                context["confirm_reset"] = True
            context["user"] = data.get("user")
            response.content = response.content = render_block_to_string(
                "leave/leave_management.html",
                "reset_button_section",
                context,
            )
            response = retarget(response, "#reset_button_section")
            response = reswap(response, "outerHTML")
            return response

        if request.method == "POST":
            try:
                data = request.POST
                _, user = process_reset_user_leave_credits(data.get("user"))
                context["user"] = user
                response.content = response.content = render_block_to_string(
                    "leave/leave_management.html",
                    "edit_user_leave_credit_settings_container",
                    context,
                )
                process_add_app_log_entry(
                    request.user.id,
                    f"Reset user ({user.userdetails.get_user_fullname()})'s leave credits.",
                )
                response = create_global_alert_instance(
                    response,
                    f"Leave credits for the selected user have been successfully reset.",
                    "SUCCESS",
                )
                response = trigger_client_event(
                    response, "updateleaveCreditList", after="swap"
                )
                response = retarget(
                    response, "#edit_user_leave_credit_settings_container"
                )
                response = reswap(response, "outerHTML")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while attempting to reset the leave credits for the selected user. Error details: {error}",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response


# App Shared View


def leave_module_close_modals(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        event_name = data.get("event_name")
        response = HttpResponse()
        response = trigger_client_event(response, event_name, after="swap")
        response = reswap(response, "none")
        return response
