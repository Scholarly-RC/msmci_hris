import calendar
import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models.deletion import RestrictedError
from django.http import HttpResponse
from django.http.request import QueryDict
from django.shortcuts import render
from django.urls import reverse
from django.utils.timezone import make_aware
from django.views.decorators.csrf import csrf_exempt
from django_htmx.http import push_url, reswap, retarget, trigger_client_event
from django_q.tasks import async_task
from render_block import render_block_to_string

from attendance.actions import (
    manually_set_user_clocked_time,
    process_add_holiday,
    process_adding_shift_swap_request,
    process_apply_department_fixed_or_dynamic_shift,
    process_approving_swap_request,
    process_bulk_daily_shift_schedule,
    process_create_new_shift,
    process_create_overtime_request,
    process_daily_shift_schedule,
    process_delete_holiday,
    process_delete_user_clocked_time,
    process_deleting_overtime_request,
    process_modify_department_shift,
    process_rejecting_swap_request,
    process_removing_shift,
    process_respond_to_overtime_request,
    process_update_clocked_time,
)
from attendance.models import (
    AttendanceRecord,
    DailyShiftRecord,
    Holiday,
    OverTime,
    Shift,
    ShiftSwap,
)
from attendance.utils.assign_shift_utils import get_employee_assignments
from attendance.utils.attendance_utils import (
    get_employees_list_per_department,
    get_employees_with_same_day_different_shit,
    get_user_clocked_time,
    get_user_daily_shift_record_shifts,
)
from attendance.utils.date_utils import (
    get_current_local_date,
    get_date_object,
    get_date_object_from_date_str,
    get_day_name_from_date,
    get_list_of_months,
    get_number_of_days_in_a_month,
    get_readable_date,
)
from attendance.utils.holiday_utils import (
    get_holiday_for_specific_day,
    get_holiday_for_specific_month_and_year,
    get_holidays,
    get_holidays_year_list,
)
from attendance.utils.overtime_utils import (
    check_user_has_approved_overtime_on_specific_date,
    get_all_overtime_request,
    get_overtime_request_approvers,
    get_overtime_request_status_list,
    get_overtime_requests_year_list,
    get_user_overtime_approver,
    get_user_overtime_requests,
    get_user_overtime_requests_to_approve,
)
from attendance.utils.shift_utils import get_all_shifts
from attendance.utils.swap_utils import (
    get_pending_swap_requests,
    get_user_shift_swap_request,
    get_users_involved_with_swap_requests,
    get_years_for_existing_swap_requests,
)
from attendance.validations import (
    add_holiday_validation,
    add_new_clocked_time_validation,
    create_new_shift_validation,
    request_swap_validation,
)
from core.decorators import hr_required
from core.models import BiometricDetail, Department
from core.notification import create_notification
from hris.utils import create_global_alert_instance
from leave.utils import (
    check_user_has_approved_leave_on_specific_date,
    get_department_heads,
)
from payroll.utils import get_department_list


### Attendance Management ###
@login_required(login_url="/login")
def attendance_management(request, year="", month=""):
    context = {"list_of_months": get_list_of_months()}
    current_user = request.user
    now = datetime.now()
    selected_year = request.POST.get("attendance_year") or year or now.year
    selected_month = request.POST.get("attendance_month") or month or now.month
    selected_year = int(selected_year)
    selected_month = int(selected_month)

    context.update({"selected_year": selected_year, "selected_month": selected_month})
    number_of_days = get_number_of_days_in_a_month(
        year=selected_year, month=selected_month
    )[1]
    monthly_record_data = []
    for day in range(1, number_of_days + 1):
        daily_user_shift = get_user_daily_shift_record_shifts(
            user=current_user,
            year=selected_year,
            month=selected_month,
            day=day,
        )

        clocked_time_data = get_user_clocked_time(
            user=current_user,
            year=selected_year,
            month=selected_month,
            day=day,
        )

        day_name = get_day_name_from_date(
            date=get_date_object(year=selected_year, month=selected_month, day=day)
        )

        monthly_record_data.append(
            {
                "day": day,
                "day_name": day_name,
                "daily_user_shift": daily_user_shift,
                "clocked_time_data": clocked_time_data,
                "holidays": get_holiday_for_specific_day(
                    day=day, month=selected_month, year=selected_year
                ),
                "approved_overtime": check_user_has_approved_overtime_on_specific_date(
                    user=current_user, day=day, month=selected_month, year=selected_year
                ),
                "approved_leave": check_user_has_approved_leave_on_specific_date(
                    user=current_user, day=day, month=selected_month, year=selected_year
                ),
            }
        )
    context.update({"monthly_record_data": monthly_record_data})
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "attendance/attendance_management.html",
            "user_attendance_table",
            context,
        )
        response = push_url(
            response,
            reverse(
                "attendance:attendance_management_filtered",
                kwargs={
                    "year": selected_year,
                    "month": selected_month,
                },
            ),
        )
        response = retarget(response, "#user_attendance_table")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "attendance/attendance_management.html", context)


@login_required(login_url="/login")
def sync_user_attendance(request, year="", month=""):
    context = {"list_of_months": get_list_of_months()}
    current_user = request.user
    now = datetime.now()
    selected_year = request.POST.get("attendance_year") or now.year
    selected_month = request.POST.get("attendance_month") or now.month
    selected_year = int(selected_year)
    selected_month = int(selected_month)

    context.update({"selected_year": selected_year, "selected_month": selected_month})

    number_of_days = get_number_of_days_in_a_month(
        year=selected_year, month=selected_month
    )[1]
    monthly_record_data = []
    for day in range(1, number_of_days + 1):
        daily_user_shift = get_user_daily_shift_record_shifts(
            user=current_user,
            year=selected_year,
            month=selected_month,
            day=day,
        )

        clocked_time_data = get_user_clocked_time(
            user=current_user,
            year=selected_year,
            month=selected_month,
            day=day,
        )

        day_name = get_day_name_from_date(
            date=get_date_object(year=selected_year, month=selected_month, day=day)
        )

        monthly_record_data.append(
            {
                "day": day,
                "day_name": day_name,
                "daily_user_shift": daily_user_shift,
                "clocked_time_data": clocked_time_data,
                "holidays": get_holiday_for_specific_day(
                    day=day, month=selected_month, year=selected_year
                ),
            }
        )
    context.update({"monthly_record_data": monthly_record_data})

    if request.htmx and request.method == "POST":
        current_biometric_data = BiometricDetail.objects.get(user=current_user)

        response = HttpResponse()
        response.content = render_block_to_string(
            "attendance/attendance_management.html",
            "user_attendance_table",
            context,
        )
        response = retarget(response, "#user_attendance_table")
        response = reswap(response, "outerHTML")

        if current_biometric_data.user_id_in_device:
            attendance_records = AttendanceRecord.objects.filter(
                user_biometric_detail__isnull=True,
                user_id_from_device=current_biometric_data.user_id_in_device,
            )

            if attendance_records.exists():
                for attendance_record in attendance_records:
                    setattr(
                        attendance_record,
                        "user_biometric_detail",
                        current_biometric_data,
                    )
                    attendance_record.save()
            response = create_global_alert_instance(
                response, "Attendance data successfully synced.", "SUCCESS"
            )
        else:
            response = create_global_alert_instance(
                response,
                "Your Biometric Device User ID has not been set. Please configure it in your profile before proceeding.",
                "DANGER",
            )
            response = reswap(response, "none")
        return response


@login_required(login_url="/login")
def request_swap(request):
    context = {}
    if request.htmx and request.method == "GET":
        data = request.GET
        user = request.user
        response = HttpResponse()
        errors = request_swap_validation(user=user)
        if errors:
            for error in errors:
                response = create_global_alert_instance(
                    response, errors[error], "WARNING"
                )
                response = reswap(response, "none")
                return response

        context["current_user"] = user

        if "review_pending" in data:
            swap_requests = get_pending_swap_requests(approver=user)
            involved_users = get_users_involved_with_swap_requests(approver=user)
            years = get_years_for_existing_swap_requests()
            if "request_swap_selected_user" in data:
                selected_user = data.get("request_swap_selected_user")
                if selected_user != "":
                    context["request_swap_selected_user"] = int(selected_user)
                    swap_requests = swap_requests.filter(
                        Q(requested_by__id=selected_user)
                        | Q(requested_for__id=selected_user)
                    )
            if "request_swap_selected_year" in data:
                selected_year = data.get("request_swap_selected_year")
                if selected_year != "":
                    context["request_swap_selected_year"] = int(selected_year)
                    swap_requests = swap_requests.filter(
                        requested_shift__date__year=selected_year
                    )

            context.update(
                {
                    "for_review_pending": True,
                    "swap_requests": swap_requests,
                    "involved_users": involved_users,
                    "years": years,
                }
            )

        else:
            department_heads = get_department_heads(
                selected_department=user.userdetails.department
            ).exclude(id=user.id)

            swap_requests = get_user_shift_swap_request(user=user)

            context.update(
                {"department_heads": department_heads, "swap_requests": swap_requests}
            )

        response.content = render_block_to_string(
            "attendance/attendance_management.html",
            "request_swap_modal_container",
            context,
        )
        response = trigger_client_event(response, "openRequestSwapModal", after="swap")
        response = retarget(response, "#request_swap_modal_container")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def reload_request_swap_user_list(request):
    context = {}
    if request.htmx and request.method == "GET":
        user = request.user
        response = HttpResponse()
        data = request.GET
        swap_date = data.get("swap_date", None)
        shifts = get_employees_with_same_day_different_shit(user=user, date=swap_date)
        context.update({"shifts": shifts})
        response.content = render_block_to_string(
            "attendance/attendance_management.html",
            "request_swap_user_shift_selection",
            context,
        )
        response = trigger_client_event(response, "openRequestSwapModal", after="swap")
        response = retarget(response, "#request_swap_user_shift_selection")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def submit_request_swap(request):
    context = {}
    if request.htmx and request.method == "POST":
        try:
            user = request.user
            response = HttpResponse()
            data = request.POST
            shift_swap = process_adding_shift_swap_request(requestor=user, payload=data)
            response = trigger_client_event(
                response, "reloadRequestSwapContent", after="swap"
            )
            create_notification(
                f"A shift swap request on <b>{shift_swap.requested_shift.date}</b> was submitted by <b>{shift_swap.requested_by.userdetails.get_user_fullname().title()}</b>.",
                date=get_current_local_date(),
                sender_id=shift_swap.requested_by.id,
                recipient_id=shift_swap.approver.id,
                url=reverse("attendance:attendance_management"),
            )
            create_notification(
                f"<b>{shift_swap.requested_by.userdetails.get_user_fullname().title()}</b> has submitted a shift swap request with you on <b>{shift_swap.requested_shift.date}</b>.",
                date=get_current_local_date(),
                sender_id=shift_swap.approver.id,
                recipient_id=shift_swap.requested_for.id,
                url=reverse("attendance:attendance_management"),
            )
            response = create_global_alert_instance(
                response,
                "Your shift swap request has been successfully submitted.",
                "SUCCESS",
            )
            response = reswap(response, "none")
            return response

        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while processing your shift swap request. Please try again later. Details: {error}.",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def respond_to_swap_request(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            data = request.GET
            request_swap_id = data.get("request_swap")
            context["swap_data"] = ShiftSwap.objects.get(id=request_swap_id)
            if "cancel" not in data:
                context["for_confirmation"] = True

                if "approve" in data:
                    context["for_approve"] = True
                elif "reject" in data:
                    context["for_reject"] = True

            response.content = render_block_to_string(
                "attendance/attendance_management.html",
                "shift_review_action_section",
                context,
            )
            response = retarget(response, "closest td")
            response = reswap(response, "outerHTML")
            return response

        if request.method == "POST":
            data = request.POST
            swap_request_id = data.get("request_swap")
            try:
                if "swap_approved" in data:
                    shift_swap = process_approving_swap_request(
                        swap_request_id=swap_request_id
                    )
                    context["swap_data"] = shift_swap
                    response.content = render_block_to_string(
                        "attendance/attendance_management.html",
                        "swap_request_item",
                        context,
                    )
                    create_notification(
                        f"Your shift swap request for <b>{shift_swap.requested_shift.date}</b> with <b>{shift_swap.requested_for.userdetails.get_user_fullname().title()}</b> has been approved by <b>{shift_swap.approver.userdetails.get_user_fullname().title()}</b>.",
                        date=get_current_local_date(),
                        sender_id=shift_swap.approver.id,
                        recipient_id=shift_swap.requested_by.id,
                        url=reverse("attendance:attendance_management"),
                    )
                    create_notification(
                        f"Your shift on <b>{shift_swap.requested_shift.date}</b> has been successfully swapped with <b>{shift_swap.requested_by.userdetails.get_user_fullname().title()}</b>.",
                        date=get_current_local_date(),
                        sender_id=shift_swap.approver.id,
                        recipient_id=shift_swap.requested_for.id,
                        url=reverse("attendance:attendance_management"),
                    )
                    response = create_global_alert_instance(
                        response,
                        "Selected shift swap request has been successfully approved.",
                        "SUCCESS",
                    )
                    response = retarget(response, "closest tr")
                    response = reswap(response, "outerHTML")
                    return response
                elif "swap_rejected" in data:
                    shift_swap = process_rejecting_swap_request(
                        swap_request_id=swap_request_id
                    )
                    context["swap_data"] = shift_swap
                    response.content = render_block_to_string(
                        "attendance/attendance_management.html",
                        "swap_request_item",
                        context,
                    )

                    create_notification(
                        f"Your shift swap request for <b>{shift_swap.requested_shift.date}</b> with <b>{shift_swap.requested_for.userdetails.get_user_fullname().title()}</b> has been rejected by <b>{shift_swap.approver.userdetails.get_user_fullname().title()}</b>.",
                        date=get_current_local_date(),
                        sender_id=shift_swap.approver.id,
                        recipient_id=shift_swap.requested_by.id,
                        url=reverse("attendance:attendance_management"),
                    )
                    create_notification(
                        f"The shift swap request for <b>{shift_swap.requested_shift.date}</b> with <b>{shift_swap.requested_by.userdetails.get_user_fullname().title()}</b> has been rejected by <b>{shift_swap.approver.userdetails.get_user_fullname().title()}</b>.",
                        date=get_current_local_date(),
                        sender_id=shift_swap.approver.id,
                        recipient_id=shift_swap.requested_for.id,
                        url=reverse("attendance:attendance_management"),
                    )

                    response = create_global_alert_instance(
                        response,
                        "The selected shift swap request has been successfully rejected.",
                        "SUCCESS",
                    )
                    response = retarget(response, "closest tr")
                    response = reswap(response, "outerHTML")
                    return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while processing the shift swap request. Please try again later. Error details: {error}.",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response


@login_required(login_url="/login")
def request_overtime(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        user = request.user
        if request.method == "GET":
            data = request.GET
            approvers = get_user_overtime_approver(user)
            overtime_requests = get_user_overtime_requests(user)
            overtime_years = get_overtime_requests_year_list(overtime_requests)

            if "year_filter" in data:
                year = data.get("selected_year")
                if year and year != "0":
                    overtime_requests = overtime_requests.filter(date__year=year)

                context["overtime_requests"] = overtime_requests

                response.content = render_block_to_string(
                    "attendance/attendance_management.html",
                    "user_overtime_requests_table",
                    context,
                )
                response = retarget(response, "#user_overtime_requests_table")
                response = reswap(response, "outerHTML")
                return response

            context.update(
                {
                    "user": user,
                    "approvers": approvers,
                    "overtime_requests": overtime_requests,
                    "overtime_years": overtime_years,
                }
            )
            response.content = render_block_to_string(
                "attendance/attendance_management.html",
                "request_overtime_container",
                context,
            )
            response = trigger_client_event(
                response, "openRequestOvertimeModal", after="swap"
            )
            response = retarget(response, "#request_overtime_container")
            response = reswap(response, "outerHTML")
            return response


@login_required(login_url="/login")
def submit_overtime_request(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        user = request.user
        if request.method == "POST":
            data = request.POST
            overtime_request = process_create_overtime_request(user, data)
            approvers = get_user_overtime_approver(user)
            overtime_requests = get_user_overtime_requests(user)
            overtime_years = get_overtime_requests_year_list(overtime_requests)

            context.update(
                {
                    "user": user,
                    "approvers": approvers,
                    "overtime_requests": overtime_requests,
                    "overtime_years": overtime_years,
                }
            )
            response.content = render_block_to_string(
                "attendance/attendance_management.html",
                "request_overtime_container",
                context,
            )
            create_notification(
                content=f"<b>{overtime_request.get_requestor_display()}</b> has submitted an overtime request for <b>{overtime_request.get_display_date()}</b>.",
                date=make_aware(datetime.now()),
                sender_id=overtime_request.user.id,
                recipient_id=overtime_request.approver.id,
                url=(
                    reverse("attendance:attendance_management")
                    if not overtime_request.approver.userdetails.is_hr()
                    else reverse("attendance:overtime_management")
                ),
            )
            response = create_global_alert_instance(
                response, "Overtime successfully submitted for review.", "SUCCESS"
            )
            response = retarget(response, "#request_overtime_container")
            response = reswap(response, "outerHTML")
            return response


@login_required(login_url="/login")
def view_overtime_request_to_approve(request):
    context = {}
    if request.htmx and request.method == "GET":
        response = HttpResponse()
        data = request.GET
        user = request.user
        if "back" in data:
            response = trigger_client_event(
                response, "openRequestOvertimeModal", after="swap"
            )
            response = trigger_client_event(
                response, "closeOvertimeRequestsToApproveModal", after="swap"
            )
            response = reswap(response, "none")
            return response

        requests_to_approve = get_user_overtime_requests_to_approve(user)
        overtime_years = get_overtime_requests_year_list(requests_to_approve)

        if "year_filter" in data:
            year = data.get("selected_year")
            if year and year != "0":
                requests_to_approve = requests_to_approve.filter(date__year=year)

            context["requests_to_approve"] = requests_to_approve
            response.content = render_block_to_string(
                "attendance/attendance_management.html",
                "overtime_requests_to_approve_table",
                context,
            )
            response = retarget(response, "#overtime_requests_to_approve_table")
            response = reswap(response, "outerHTML")
            return response

        context.update(
            {
                "requests_to_approve": requests_to_approve,
                "overtime_years": overtime_years,
            }
        )
        response.content = render_block_to_string(
            "attendance/attendance_management.html",
            "overtime_request_to_approve_container",
            context,
        )
        response = trigger_client_event(
            response, "openOvertimeRequestsToApproveModal", after="swap"
        )
        response = trigger_client_event(
            response, "closeRequestOvertimeModal", after="swap"
        )
        response = retarget(response, "#overtime_request_to_approve_container")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def respond_to_overtime_request(request):
    context = {}
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        try:
            user = request.user
            data = request.POST
            overtime_request = process_respond_to_overtime_request(user, data)
            context["overtime_request"] = overtime_request
            response.content = render_block_to_string(
                "attendance/attendance_management.html",
                "specific_overtime_request_to_respond",
                context,
            )
            response = create_global_alert_instance(
                response,
                f"You have successfully {overtime_request.get_status_display()} the selected overtime request.",
                "SUCCESS",
            )
            create_notification(
                content=f"Your overtime request for <b>{overtime_request.get_display_date()}</b> has been <b>{overtime_request.get_status_display()}</b> by <b>{overtime_request.get_approver_display()}</b>.",
                date=make_aware(datetime.now()),
                sender_id=overtime_request.approver.id,
                recipient_id=overtime_request.user.id,
                url=reverse("attendance:attendance_management"),
            )
            response = retarget(response, "closest tr")
            response = reswap(response, "outerHTML")
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while processing your response to the overtime request. Details: {error}.",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
@hr_required("/")
def overtime_management(request):
    context = {}

    if "overtime_filter" in request.POST:
        filter_data = request.POST
    else:
        filter_data = {}

    overtime_requests = get_all_overtime_request(filter_data=filter_data)
    overtime_requests_year_list = get_overtime_requests_year_list(overtime_requests)
    departments = get_department_list()
    overtime_status_list = get_overtime_request_status_list()
    approvers = get_overtime_request_approvers()
    user = request.user
    context.update(
        {
            "user": user,
            "overtime_requests": overtime_requests,
            "overtime_requests_year_list": overtime_requests_year_list,
            "departments": departments,
            "overtime_status_list": overtime_status_list,
            "approvers": approvers,
        }
    )
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "attendance/overtime_management.html",
            "overtime_request_table",
            context,
        )
        response = retarget(response, "#overtime_request_table")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "attendance/overtime_management.html", context)


@login_required(login_url="/login")
def overtime_management_respond_to_request(request):
    context = {}
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        try:
            user = request.user
            data = request.POST
            overtime_request = process_respond_to_overtime_request(user, data)
            context["overtime_request"] = overtime_request
            response.content = render_block_to_string(
                "attendance/attendance_management.html",
                "specific_overtime_request_to_respond",
                context,
            )
            response = create_global_alert_instance(
                response,
                f"You have successfully {overtime_request.get_status_display()} the selected overtime request.",
                "SUCCESS",
            )
            create_notification(
                content=f"Your overtime request for <b>{overtime_request.get_display_date()}</b> has been <b>{overtime_request.get_status_display()}</b> by <b>{overtime_request.get_approver_display()}</b>.",
                date=make_aware(datetime.now()),
                sender_id=overtime_request.approver.id,
                recipient_id=overtime_request.user.id,
                url=reverse("attendance:attendance_management"),
            )
            response = retarget(response, "closest tr")
            response = reswap(response, "outerHTML")
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while processing your response to the overtime request. Details: {error}.",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def delete_overtime_request(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        user = request.user
        if request.method == "DELETE":
            try:
                data = QueryDict(request.body)
                process_deleting_overtime_request(data)
                response = create_global_alert_instance(
                    response,
                    "The selected overtime record has been successfully deleted.",
                    "SUCCESS",
                )
                response = retarget(response, "closest tr")
                response = reswap(response, "delete")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while attempting to delete the selected overtime record. Please try again. Details: {error}",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response

        if request.method == "POST":
            data = request.POST
            if not "cancel" in data:
                context["confirm_remove"] = True

            context["user"] = user
            overtime_request_id = data.get("overtime_request")
            context["overtime_request"] = OverTime.objects.get(id=overtime_request_id)
            response.content = render_block_to_string(
                "attendance/overtime_management.html",
                "specific_overtime_request_action_button",
                context,
            )
            response = retarget(response, "closest td")
            response = reswap(response, "outerHTML")
            return response


@login_required(login_url="/login")
@hr_required("/")
def user_attendance_management(request, user_id="", year="", month=""):
    context = {}
    users = get_employees_list_per_department()
    now = datetime.now()
    selected_year = request.POST.get("attendance_year") or year or now.year
    selected_month = request.POST.get("attendance_month") or month or now.month
    selected_user_id = request.POST.get("selected_user") or user_id
    selected_year = int(selected_year)
    selected_month = int(selected_month)

    context.update(
        {
            "list_of_months": get_list_of_months(),
            "users": users,
            "selected_year": selected_year,
            "selected_month": selected_month,
        }
    )

    if selected_user_id and selected_user_id != "0":
        selected_user = User.objects.get(id=selected_user_id)
        context.update({"selected_user": selected_user})

        number_of_days = get_number_of_days_in_a_month(
            year=selected_year, month=selected_month
        )[1]
        monthly_record_data = []
        for day in range(1, number_of_days + 1):
            daily_user_shift = get_user_daily_shift_record_shifts(
                user=selected_user,
                year=selected_year,
                month=selected_month,
                day=day,
            )

            clocked_time_data = get_user_clocked_time(
                user=selected_user,
                year=selected_year,
                month=selected_month,
                day=day,
            )

            day_name = get_day_name_from_date(
                date=get_date_object(year=selected_year, month=selected_month, day=day)
            )

            monthly_record_data.append(
                {
                    "day": day,
                    "day_name": day_name,
                    "daily_user_shift": daily_user_shift,
                    "clocked_time_data": clocked_time_data,
                    "holidays": get_holiday_for_specific_day(
                        day=day, month=selected_month, year=selected_year
                    ),
                    "approved_overtime": check_user_has_approved_overtime_on_specific_date(
                        user=selected_user,
                        day=day,
                        month=selected_month,
                        year=selected_year,
                    ),
                    "approved_leave": check_user_has_approved_leave_on_specific_date(
                        user=selected_user,
                        day=day,
                        month=selected_month,
                        year=selected_year,
                    ),
                }
            )
        context.update({"monthly_record_data": monthly_record_data})

    if request.htmx and request.POST:
        response = HttpResponse()
        response.content = render_block_to_string(
            "attendance/user_attendance_management.html",
            "user_management_attendance_table_container",
            context,
        )
        response = push_url(
            response,
            reverse(
                "attendance:user_attendance_management_filtered",
                kwargs={
                    "user_id": selected_user_id,
                    "year": selected_year,
                    "month": selected_month,
                },
            ),
        )
        response = retarget(response, "#user_management_attendance_table_container")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "attendance/user_attendance_management.html", context)


# Add Admin Checks
@login_required(login_url="/login")
def modify_user_clocked_time(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            data = request.GET
            selected_user = User.objects.get(id=data.get("selected_user"))
            selected_year = int(data.get("attendance_year"))
            selected_month = int(data.get("attendance_month"))
            selected_day = int(data.get("selected_day"))
            selected_date = get_date_object(
                year=selected_year, month=selected_month, day=selected_day
            )
            response = trigger_client_event(
                response,
                "reloadModifyClockedTimeList",
                {"userId": selected_user.id, "selectedDate": str(selected_date)},
                after="swap",
            )
            response = trigger_client_event(
                response, "openModifyClockedTimeModal", after="swap"
            )
            response = reswap(response, "none")
            return response


# Add Admin Checks
@login_required(login_url="/login")
def reload_modify_clocked_time_list(request):
    context = {}
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        data = request.POST
        details = json.loads(data.get("details", {}))
        user_id = details.get("userId")
        selected_user = User.objects.get(id=user_id)
        selected_date = get_date_object_from_date_str(details.get("selectedDate"))

        clocked_time_data = get_user_clocked_time(
            user=selected_user.id,
            year=selected_date.year,
            month=selected_date.month,
            day=selected_date.day,
        )
        context.update(
            {
                "clocked_time_data": clocked_time_data,
                "selected_user": selected_user,
                "selected_date": selected_date,
                "selected_date_str": str(selected_date),
            }
        )
        response.content = render_block_to_string(
            "attendance/user_attendance_management.html",
            "modify_clocked_time_modal_container",
            context,
        )
        response = retarget(response, "#modify_clocked_time_modal_container")
        response = reswap(response, "outerHTML")
        return response


# Add Admin Checks
@login_required(login_url="/login")
def add_user_clocked_time(request):
    context = {}
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        try:
            data = request.POST
            errors = add_new_clocked_time_validation(payload=data)
            if errors:
                for error in errors:
                    response = create_global_alert_instance(
                        response, errors[error], "WARNING"
                    )
                    response = reswap(response, "none")
                    return response

            attendance_record = manually_set_user_clocked_time(payload=data)
            response = trigger_client_event(
                response,
                "reloadModifyClockedTimeList",
                {
                    "userId": attendance_record.user_biometric_detail.user.id,
                    "selectedDate": str(attendance_record.timestamp.date()),
                },
                after="swap",
            )
            response = create_global_alert_instance(
                response,
                "The clocked time for the selected date has been successfully updated.",
                "SUCCESS",
            )
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while modifying the clocked time for the selected date. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


# Add Admin Checks
@login_required(login_url="/login")
def delete_user_clocked_time(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "POST":
            data = request.POST
            punch = data.get("punch")
            attendance_record_id = data.get("attendance_record")
            attendance_record = AttendanceRecord.objects.get(id=attendance_record_id)
            context["data"] = attendance_record

            if punch == "IN":
                section = "clocked_in_action_section"
            else:
                section = "clocked_out_action_section"

            context["delete_confirmation"] = "cancel" not in data

            response.content = render_block_to_string(
                "attendance/user_attendance_management.html",
                section,
                context,
            )

            response = retarget(response, "closest td")
            response = reswap(response, "outerHTML")
            return response

        if request.method == "DELETE":
            try:
                data = QueryDict(request.body)
                process_delete_user_clocked_time(payload=data)
                response = create_global_alert_instance(
                    response,
                    f"Selected user's clocked time has been successfully deleted.",
                    "SUCCESS",
                )
                response = retarget(response, "closest tr")
                response = reswap(response, "delete")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while deleting a user clocked time. Details: {error}",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response


# Add Admin Checks
@login_required(login_url="/login")
def edit_user_clocked_time(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            data = request.GET
            if "cancel" not in data:
                attendance_record_id = data.get("attendance_record")
                selected_date = data.get("selected_date")
                attendance_record = AttendanceRecord.objects.get(
                    id=attendance_record_id
                )
                context.update(
                    {
                        "for_update": True,
                        "attendance_record": attendance_record,
                        "selected_date_str": selected_date,
                    }
                )
            response.content = render_block_to_string(
                "attendance/user_attendance_management.html",
                "modify_clocked_time_section",
                context,
            )
            response = retarget(response, "#modify_clocked_time_section")
            response = reswap(response, "outerHTML")
            return response

        if request.method == "POST":
            data = request.POST
            try:
                attendance_record = process_update_clocked_time(payload=data)
                response = create_global_alert_instance(
                    response,
                    f"The clocked time for the selected user has been successfully updated.",
                    "SUCCESS",
                )
                response = trigger_client_event(
                    response,
                    "reloadModifyClockedTimeList",
                    {
                        "userId": attendance_record.user_biometric_detail.user.id,
                        "selectedDate": str(attendance_record.timestamp.date()),
                    },
                    after="swap",
                )
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while updating the clocked time for the user. Error details: {error}",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response


### Shift Management ###
@login_required(login_url="/login")
@hr_required("/")
def shift_management(request, department="", year="", month=""):
    context = {"list_of_months": get_list_of_months()}
    now = datetime.now()
    shift_year = request.POST.get("shift_year") or year or now.year
    shift_month = request.POST.get("shift_month") or month or now.month
    shift_department = request.POST.get("shift_department") or department

    if isinstance(shift_year, str):
        shift_year = int(shift_year)

    if isinstance(shift_month, str):
        shift_month = int(shift_month)

    calendar.setfirstweekday(calendar.SUNDAY)
    list_of_days = calendar.monthcalendar(shift_year, shift_month)
    list_of_departments = Department.objects.filter(is_active=True).order_by("name")
    selected_department = (
        list_of_departments.get(id=shift_department)
        if shift_department
        else list_of_departments.first()
    )

    process_apply_department_fixed_or_dynamic_shift(
        department=selected_department, month=shift_month, year=shift_year
    )

    holidays = get_holiday_for_specific_month_and_year(shift_month, shift_year)

    context.update(
        {
            "list_of_days": list_of_days,
            "selected_month": shift_month,
            "selected_year": shift_year,
            "selected_department": selected_department,
            "list_of_departments": list_of_departments,
            "holidays": holidays,
        }
    )
    if request.htmx and request.POST:
        data = request.POST
        response = HttpResponse()
        response.content = render_block_to_string(
            "attendance/shift_management.html", "shift_management_content", context
        )
        response = push_url(
            response,
            reverse(
                "attendance:shift_management_filtered",
                kwargs={
                    "year": shift_year,
                    "month": shift_month,
                    "department": shift_department,
                },
            ),
        )
        response = retarget(response, "#shift_management_content")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "attendance/shift_management.html", context)


@login_required(login_url="/login")
def update_shift_calendar(request):
    context = {}
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        data = request.POST
        shift_month = int(data.get("shift_month"))
        shift_year = int(data.get("shift_year"))
        shift_department_id = int(data.get("shift_department"))
        selected_department = Department.objects.get(id=shift_department_id)

        list_of_days = calendar.monthcalendar(shift_year, shift_month)
        holidays = get_holiday_for_specific_month_and_year(shift_month, shift_year)

        process_apply_department_fixed_or_dynamic_shift(
            department=selected_department, month=shift_month, year=shift_year
        )

        context.update(
            {
                "list_of_days": list_of_days,
                "holidays": holidays,
                "selected_month": shift_month,
                "selected_year": shift_year,
                "selected_department": selected_department,
            }
        )
        response.content = render_block_to_string(
            "attendance/shift_management.html", "shift_calendar", context
        )
        response = retarget(response, "#shift_calendar")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def assign_shift(request, department="", year="", month="", day=""):
    shift_year = year
    shift_month = month
    shift_department = department
    shift_day = day
    selected_department = Department.objects.get(id=department)
    employees = User.objects.filter(
        is_active=True, userdetails__department=selected_department
    ).order_by("first_name")

    shifts = selected_department.shifts.order_by("start_time")

    if isinstance(shift_year, str):
        shift_year = int(shift_year)

    if isinstance(shift_month, str):
        shift_month = int(shift_month)

    if isinstance(shift_day, str):
        shift_day = int(shift_day)

    selected_date = get_date_object(shift_year, shift_month, shift_day)

    current_daily_shift_record, current_daily_shift_record_created = (
        DailyShiftRecord.objects.get_or_create(
            date=selected_date, department=selected_department
        )
    )

    employee_assignments, list_of_assigned_user_ids = get_employee_assignments(
        current_daily_shift_record=current_daily_shift_record,
        shifts=shifts,
        employees=employees,
    )

    selected_readable_date = get_readable_date(shift_year, int(shift_month), shift_day)

    unassigned_employees = employees.exclude(id__in=list_of_assigned_user_ids)

    context = {
        "selected_department": selected_department,
        "selected_month": shift_month,
        "selected_year": shift_year,
        "selected_day": shift_day,
        "selected_readable_date": selected_readable_date,
        "employees": unassigned_employees,
        "employee_assignments": employee_assignments,
    }

    if request.htmx:
        response = HttpResponse()
        response.content = render_block_to_string(
            "attendance/assign_shift.html", "assign_shift_content", context
        )
        response = push_url(
            response,
            reverse(
                "attendance:assign_shift",
                kwargs={
                    "year": shift_year,
                    "month": shift_month,
                    "department": shift_department,
                    "day": shift_day,
                },
            ),
        )
        response = retarget(response, "#shift_management_content")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "attendance/assign_shift.html", context)


@login_required(login_url="/login")
def assign_user_to_shift(request, department="", year="", month="", day=""):
    if request.htmx and request.POST:
        data = request.POST
        for_search = "for_search" in data

        shift_year = year
        shift_month = month
        shift_day = day
        selected_department = Department.objects.get(id=department)
        user_search_query = data.get("search_user", "")
        employees = User.objects.filter(
            is_active=True, userdetails__department=selected_department
        ).order_by("first_name")
        if user_search_query:
            search_params = (
                Q(first_name__icontains=user_search_query)
                | Q(last_name__icontains=user_search_query)
                | Q(userdetails__middle_name__icontains=user_search_query)
            )
            employees = employees.filter(search_params)

        shifts = selected_department.shifts.order_by("start_time")

        if not for_search:
            shift_id = data.get("shift_id")
            selected_shift = shifts.get(id=shift_id)
            if any(action in data for action in ["select_all", "deselect_all"]):
                deselect = "deselect_all" in data
                process_bulk_daily_shift_schedule(
                    selected_department,
                    shift_year,
                    shift_month,
                    shift_day,
                    shifts,
                    selected_shift,
                    employees,
                    deselect=deselect,
                )
            else:
                employee_id = data.get("selected_employee") or data.get(
                    "employee_id_to_remove"
                )
                selected_employee = employees.get(id=employee_id)
                process_daily_shift_schedule(
                    selected_department,
                    shift_year,
                    shift_month,
                    shift_day,
                    selected_employee,
                    selected_shift,
                )

        selected_date = get_date_object(
            int(shift_year), int(shift_month), int(shift_day)
        )

        current_daily_shift_record, current_daily_shift_record_created = (
            DailyShiftRecord.objects.get_or_create(
                date=selected_date, department=selected_department
            )
        )

        employee_assignments, list_of_assigned_user_ids = get_employee_assignments(
            current_daily_shift_record=current_daily_shift_record,
            shifts=shifts,
            employees=employees,
        )

        selected_readable_date = get_readable_date(
            shift_year, int(shift_month), shift_day
        )

        unassigned_employees = employees.exclude(id__in=list_of_assigned_user_ids)

        context = {
            "selected_department": selected_department,
            "selected_month": shift_month,
            "selected_year": shift_year,
            "selected_day": shift_day,
            "selected_readable_date": selected_readable_date,
            "employees": unassigned_employees,
            "employee_assignments": employee_assignments,
            "user_search_query": user_search_query,
        }

        response = HttpResponse()
        if for_search:
            response.content = render_block_to_string(
                "attendance/assign_shift.html", "shift_card_container", context
            )
            response = retarget(response, "#shift_card_container")
        else:
            response.content = render_block_to_string(
                "attendance/assign_shift.html", "assign_shift_content", context
            )
            response = retarget(response, "#assign_shift_content")

        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def shift_settings(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            shifts = get_all_shifts()
            departments = get_department_list()
            context.update({"shifts": shifts, "departments": departments})
            response.content = render_block_to_string(
                "attendance/shift_management.html",
                "shift_settings_container",
                context,
            )
            response = trigger_client_event(
                response, "openShiftSettingsModal", after="swap"
            )
            response = retarget(response, "#shift_settings_container")
            response = reswap(response, "outerHTML")
            return response
        if request.method == "POST":
            pass


@login_required(login_url="/login")
def create_new_shift(request):
    context = {}
    if request.htmx and request.POST:
        response = HttpResponse()
        try:
            data = request.POST
            errors = create_new_shift_validation(data)
            if errors:
                for error in errors:
                    response = create_global_alert_instance(
                        response, errors[error], "WARNING"
                    )
                    response = reswap(response, "none")
                    return response
            process_create_new_shift(data)
            shifts = get_all_shifts()
            departments = get_department_list()
            context.update({"shifts": shifts, "departments": departments})
            response.content = render_block_to_string(
                "attendance/shift_management.html",
                "shift_settings_container",
                context,
            )
            response = create_global_alert_instance(
                response, "Shift added successfully!", "SUCCESS"
            )
            response = retarget(response, "#shift_settings_container")
            response = reswap(response, "outerHTML")
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while adding a new shift. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def remove_selected_shift(request):
    context = {}
    if request.htmx and request.POST:
        response = HttpResponse()
        try:
            data = request.POST
            process_removing_shift(data)
            shifts = get_all_shifts()
            departments = get_department_list()
            context.update({"shifts": shifts, "departments": departments})
            response.content = render_block_to_string(
                "attendance/shift_management.html",
                "shift_settings_container",
                context,
            )
            response = create_global_alert_instance(
                response, "Shift removed successfully!", "SUCCESS"
            )
            response = retarget(response, "#shift_settings_container")
            response = reswap(response, "outerHTML")
            return response
        except RestrictedError as error:
            response = create_global_alert_instance(
                response,
                f"This shift is currently being used by a department and cannot be deleted.",
                "DANGER",
            )
            response = reswap(response, "none")
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while removing the selected shift. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def modify_department_shift(request):
    context = {}
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        try:
            data = request.POST
            department = process_modify_department_shift(data)
            process_apply_department_fixed_or_dynamic_shift(department=department)
            shifts = get_all_shifts()
            context.update({"shifts": shifts, "department": department})
            response.content = render_block_to_string(
                "attendance/shift_management.html",
                "department_shift_settings_section",
                context,
            )
            response = create_global_alert_instance(
                response,
                "The shift settings for the selected department have been successfully updated.",
                "SUCCESS",
            )
            response = retarget(response, "closest form")
            response = reswap(response, "outerHTML")
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while updating the shift settings for the selected department. Error details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


### Holiday Views ##
@login_required(login_url="/login")
def holiday_settings(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            data = request.GET
            selected_year = data.get("selected_year", "0")
            regular_holidays, special_holidays = get_holidays(year=selected_year)
            holiday_years = get_holidays_year_list()
            context.update(
                {
                    "regular_holidays": regular_holidays,
                    "special_holidays": special_holidays,
                    "holiday_years": holiday_years,
                    "selected_year": int(selected_year),
                }
            )
            if "year_filter" in data:
                response.content = render_block_to_string(
                    "attendance/shift_management.html",
                    "holiday_list_section",
                    context,
                )
                response = retarget(response, "#holiday_list_section")
            else:
                response.content = render_block_to_string(
                    "attendance/shift_management.html",
                    "holiday_settings_container",
                    context,
                )
                response = trigger_client_event(
                    response, "openHolidaySettingsModal", after="swap"
                )
                response = retarget(response, "#holiday_settings_container")
            response = reswap(response, "outerHTML")
            return response

        if request.method == "POST":
            try:
                data = request.POST
                errors = add_holiday_validation(data)
                if errors:
                    for error in errors:
                        response = create_global_alert_instance(
                            response, errors[error], "WARNING"
                        )
                        response = reswap(response, "none")
                        return response

                process_add_holiday(data)
                regular_holidays, special_holidays = get_holidays()
                holiday_years = get_holidays_year_list()
                context.update(
                    {
                        "regular_holidays": regular_holidays,
                        "special_holidays": special_holidays,
                        "holiday_years": holiday_years,
                    }
                )
                response.content = render_block_to_string(
                    "attendance/shift_management.html",
                    "holiday_settings_container",
                    context,
                )
                response = create_global_alert_instance(
                    response, "Holiday added successfully!", "SUCCESS"
                )
                response = trigger_client_event(
                    response, "updateCalendar", after="swap"
                )
                response = retarget(response, "#holiday_settings_container")
                response = reswap(response, "outerHTML")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while adding the holiday. Please try again. Details: {error}",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response


@login_required(login_url="/login")
def remove_holiday(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "DELETE":
            try:
                data = QueryDict(request.body)
                process_delete_holiday(data)
                response = create_global_alert_instance(
                    response, "Holiday has been successfully deleted.", "SUCCESS"
                )
                response = trigger_client_event(
                    response, "updateCalendar", after="swap"
                )
                response = retarget(response, "closest tr")
                response = reswap(response, "delete")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"Something went wrong while deleting the selected holiday. Details: {error}",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response

        if request.method == "POST":
            data = request.POST
            holiday_id = data.get("holiday")
            holiday = Holiday.objects.get(id=holiday_id)
            holiday_type = data.get("type")
            if "cancel" not in data:
                context["confirm_remove"] = True

            context["holiday"] = holiday

            if holiday_type == "special":
                response.content = render_block_to_string(
                    "attendance/shift_management.html",
                    "specific_special_holiday_row",
                    context,
                )
            elif holiday_type == "regular":
                response.content = render_block_to_string(
                    "attendance/shift_management.html",
                    "specific_regular_holiday_row",
                    context,
                )
            response = retarget(response, "closest tr")
            response = reswap(response, "outerHTML")
            return response


### Biometric ###
@csrf_exempt
def get_attendance_request(request):
    async_task("attendance.tasks.get_biometric_data", save=False)
    return HttpResponse("OK")


@csrf_exempt
def attendance_cdata(request):
    return HttpResponse("OK")


# App Shared View


def attendance_module_close_modals(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        event_name = data.get("event_name")
        response = HttpResponse()
        response = trigger_client_event(response, event_name, after="swap")
        return response
