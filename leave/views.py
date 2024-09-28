from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render
from django_htmx.http import reswap, retarget, trigger_client_event
from render_block import render_block_to_string

from core.utils import get_users_sorted_by_department
from hris.utils import create_global_alert_instance
from leave.actions import (
    process_create_leave_request,
    process_delete_submit_leave_request,
    process_set_department_approver,
    process_set_user_leave_credit,
    process_submit_leave_request_response,
)
from leave.models import Leave
from leave.utils import (
    get_approvers_per_department,
    get_department_heads,
    get_directors,
    get_leave_to_review,
    get_leave_types,
    get_predidents,
    get_user_leave,
)
from payroll.utils import get_department_list
from performance.utils import get_user_with_hr_role


# Create your views here.
def user_leave(request):
    context = {}
    user = request.user
    leave = get_user_leave(user)
    context.update(
        {"leave_data": leave, "approver": not user.userdetails.is_employee()}
    )
    return render(request, "leave/user_leave.html", context)


def user_leave_request(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            data = request.GET
            leave_types = get_leave_types()
            context["leave_types"] = leave_types
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
                user = request.user
                process_create_leave_request(user, data)
                leave = get_user_leave(user)
                context["leave_data"] = leave
                response.content = render_block_to_string(
                    "leave/user_leave.html",
                    "leave_list",
                    context,
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
                context["leave"] = leave, leave.get_user_status(user)
                response.content = render_block_to_string(
                    "leave/user_leave.html",
                    "review_leave_request_card",
                    context,
                )
                response = create_global_alert_instance(
                    response,
                    f"You have {leave.get_user_status(user)} the Leave request by {leave.user.userdetails.get_user_fullname()} on {leave.date}.",
                    type="SUCCESS",
                )
                response = retarget(response, "closest .review-leave-request-card")
                response = reswap(response, "outerHTML")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error has occured while responing to the selected leave request. Details: {error}",
                    type="DANGER",
                )
                response = reswap(response, "none")
                return response


def leave_management(request):
    context = {}
    user = request.user
    leave_to_review = get_leave_to_review(user)
    context["leave_data"] = leave_to_review
    return render(request, "leave/leave_management.html", context)


def review_leave_request(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        user = request.user
        if request.method == "POST":
            try:
                data = request.POST
                leave = process_submit_leave_request_response(user, data)
                context["leave"] = leave, leave.get_user_status(user)
                response.content = render_block_to_string(
                    "leave/leave_management.html",
                    "review_leave_request_card",
                    context,
                )
                response = create_global_alert_instance(
                    response,
                    f"You have {leave.get_user_status(user)} the leave request submitted by {leave.user.userdetails.get_user_fullname()} on {leave.date}.",
                    type="SUCCESS",
                )
                response = retarget(response, "closest .review-leave-request-card")
                response = reswap(response, "outerHTML")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while processing the selected leave request. Details: {error}",
                    type="DANGER",
                )
                response = reswap(response, "none")
                return response


def delete_leave_request(request, leave_id=""):
    context = {}
    if request.htmx:
        response = HttpResponse()
        user = request.user
        leave = Leave.objects.get(id=leave_id)
        if request.method == "DELETE":
            process_delete_submit_leave_request(leave)
            leave_to_review = get_leave_to_review(user)
            context["leave_data"] = leave_to_review
            response = create_global_alert_instance(
                response,
                "The selected leave request has been deleted successfully.",
                "SUCCESS",
            )
            response = retarget(response, "#leave_list")
            response = reswap(response, "outerHTML")

        if request.method == "POST":
            data = request.POST
            context["leave"] = leave, leave.get_user_status(user)
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
            department_heads = get_department_heads(
                selected_department=selected_department
            )
            approvers_context = get_approvers_per_department(selected_department)
            context.update(approvers_context)
            context.update(
                {
                    "departments": departments,
                    "selected_department": selected_department,
                    "department_heads": department_heads,
                    "directors": get_directors(),
                    "presidents": get_predidents(),
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
                    f"An error occurred while updating the selected department. Details: {error}",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response


def leave_credit_settings(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            users = get_users_sorted_by_department()
            context["users"] = users
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


def edit_leave_credit_settings(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            data = request.GET
            user_id = data.get("user")
            context["user"] = User.objects.get(id=user_id)
            if not "back" in data:
                context["edit_credit"] = True
            response.content = render_block_to_string(
                "leave/leave_management.html",
                "specific_user_row",
                context,
            )
            response = retarget(response, "closest tr")
            response = reswap(response, "outerHTML")
            return response

        if request.method == "POST":
            try:
                data = request.POST
                leave_credit, user = process_set_user_leave_credit(data)
                context.update({"user": user})
                response.content = render_block_to_string(
                    "leave/leave_management.html",
                    "specific_user_row",
                    context,
                )
                response = create_global_alert_instance(
                    response,
                    f"Leave credit of selected user has been successfully updated.",
                    "SUCCESS",
                )
                response = retarget(response, "closest tr")
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


# App Shared View


def leave_module_close_modals(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        event_name = data.get("event_name")
        response = HttpResponse()
        response = trigger_client_event(response, event_name, after="swap")
        return response
