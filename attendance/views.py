import calendar
from datetime import datetime

from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse
from django.http.request import QueryDict
from django.shortcuts import render
from django.urls import reverse
from django.utils.timezone import make_aware
from django.views.decorators.csrf import csrf_exempt
from django_htmx.http import push_url, reswap, retarget, trigger_client_event
from render_block import render_block_to_string

from attendance.actions import (
    manually_set_user_clocked_time,
    process_add_holiday,
    process_bulk_daily_shift_schedule,
    process_create_new_shift,
    process_create_overtime_request,
    process_daily_shift_schedule,
    process_delete_holiday,
    process_deleting_overtime_request,
    process_modify_department_shift,
    process_removing_shift,
    process_respond_to_overtime_request,
)
from attendance.biometric_device import get_biometric_data
from attendance.models import (
    AttendanceRecord,
    DailyShiftRecord,
    Holiday,
    OverTime,
    Shift,
)
from attendance.utils.assign_shift_utils import get_employee_assignments
from attendance.utils.attendance_utils import (
    get_employees_list_per_department,
    get_user_clocked_time,
    get_user_daily_shift_record_shifts,
)
from attendance.utils.date_utils import (
    get_date_object,
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
from attendance.validations import add_holiday_validation, create_new_shift_validation
from core.models import BiometricDetail, Department
from core.notification import create_notification
from hris.utils import create_global_alert_instance
from payroll.utils import get_department_list


### Attendance Management ###
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
        current_shift = daily_user_shift.shift if daily_user_shift else None
        clocked_time = get_user_clocked_time(
            user=current_user,
            year=selected_year,
            month=selected_month,
            day=day,
            shift=current_shift,
        )

        monthly_record_data.append(
            {
                "day": day,
                "daily_user_shift": daily_user_shift,
                "clocked_time": clocked_time,
                "holidays": get_holiday_for_specific_day(
                    day=day, month=selected_month, year=selected_year
                ),
                "approved_overtime": check_user_has_approved_overtime_on_specific_date(
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
        current_shift = daily_user_shift.shift if daily_user_shift else None
        clocked_time = get_user_clocked_time(
            user=current_user,
            year=selected_year,
            month=selected_month,
            day=day,
            shift=current_shift,
        )
        monthly_record_data.append(
            {
                "day": day,
                "daily_user_shift": daily_user_shift,
                "clocked_time": clocked_time,
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
            current_shift = daily_user_shift.shift if daily_user_shift else None
            clocked_time = get_user_clocked_time(
                user=selected_user,
                year=selected_year,
                month=selected_month,
                day=day,
                shift=current_shift,
            )
            monthly_record_data.append(
                {
                    "day": day,
                    "daily_user_shift": daily_user_shift,
                    "clocked_time": clocked_time,
                    "holidays": get_holiday_for_specific_day(
                        day=day, month=selected_month, year=selected_year
                    ),
                    "approved_overtime": check_user_has_approved_overtime_on_specific_date(
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


def toggle_user_management_record_edit(request):
    context = {}
    if request.htmx and request.POST:
        data = request.POST
        selected_year = request.POST.get("attendance_year")
        selected_month = request.POST.get("attendance_month")
        selected_day = request.POST.get("selected_day")
        selected_year = int(selected_year)
        selected_month = int(selected_month)
        selected_day = int(selected_day)
        selected_user_id = request.POST.get("selected_user")
        selected_user = User.objects.get(id=selected_user_id)

        if "toggle_edit_mode" in data:
            edit_mode = data.get("toggle_edit_mode") == "on"
            context.update({"record_edit_mode": edit_mode})
        elif "save_record" in data:
            clock_in_time = data.get("clock_in_time")
            clock_out_time = data.get("clock_out_time")
            selected_date = get_date_object(selected_year, selected_month, selected_day)
            manually_set_user_clocked_time(
                selected_user, selected_date, clock_in_time, clock_out_time
            )

        daily_user_shift = get_user_daily_shift_record_shifts(
            user=selected_user,
            year=selected_year,
            month=selected_month,
            day=selected_day,
        )
        current_shift = daily_user_shift.shift if daily_user_shift else None
        clocked_time = get_user_clocked_time(
            user=selected_user,
            year=selected_year,
            month=selected_month,
            day=selected_day,
            shift=current_shift,
        )

        user_shift_data = {
            "day": selected_day,
            "daily_user_shift": daily_user_shift,
            "clocked_time": clocked_time,
        }

        context.update({"user_shift_data": user_shift_data})

        response = HttpResponse()
        response.content = render_block_to_string(
            "attendance/user_attendance_management.html",
            "user_table_record",
            context,
        )
        response = reswap(response, "outerHTML")
        return response
        # selected_user_id = data.get("selected_user")
        # attendance_year = data.get("attendance_year")
        # attendance_month = data.get("attendance_month")
        # attendance_day = data.get("selected_day")
        # attendance_year = int(attendance_year)
        # attendance_month = int(attendance_month)
        # attendance_day = int(attendance_day)


### Shift Management ###
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


def assign_shift(request, department="", year="", month="", day=""):
    shift_year = year
    shift_month = month
    shift_department = department
    shift_day = day
    selected_department = Department.objects.get(id=department)
    employees = User.objects.filter(
        userdetails__department=selected_department
    ).order_by("first_name")
    shifts = Shift.objects.filter(is_active=True)

    selected_date = get_date_object(int(shift_year), int(shift_month), int(shift_day))

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
            userdetails__department=selected_department
        ).order_by("first_name")
        if user_search_query:
            search_params = (
                Q(first_name__icontains=user_search_query)
                | Q(last_name__icontains=user_search_query)
                | Q(userdetails__middle_name__icontains=user_search_query)
            )
            employees = employees.filter(search_params)

        shifts = Shift.objects.filter(is_active=True)

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

        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while removing the selected shift. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


def modify_department_shift(request):
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        try:
            data = request.POST
            shift, department = process_modify_department_shift(data)
            action = "removed" if "selected" not in data else "added"
            response = create_global_alert_instance(
                response,
                f"The selected shift has been successfully {action} for the {department} department.",
                "SUCCESS",
            )
            response = reswap(response, "none")
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while modifying the shift for the selected department. Error details: {error}.",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


### Holiday Views ##
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
    return HttpResponse("OK")


@csrf_exempt
def attendance_cdata(request):
    if request.method == "POST":
        get_biometric_data()

    return HttpResponse("OK")


# App Shared View


def attendance_module_close_modals(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        event_name = data.get("event_name")
        response = HttpResponse()
        response = trigger_client_event(response, event_name, after="swap")
        return response
