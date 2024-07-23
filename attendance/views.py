import calendar
import datetime

from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django_htmx.http import (
    HttpResponseClientRedirect,
    push_url,
    reswap,
    retarget,
    trigger_client_event,
)
from render_block import render_block_to_string

from attendance.actions import (
    process_bulk_daily_shift_schedule,
    process_daily_shift_schedule,
)
from attendance.biometric_device import get_biometric_data
from attendance.models import AttendanceRecord, DailyShiftRecord, Shift
from attendance.utils.assign_shift_utils import get_employee_assignments
from attendance.utils.attendance_utils import (
    get_user_clocked_time,
    get_user_daily_shift_record,
)
from attendance.utils.date_utils import (
    get_date_object,
    get_list_of_months,
    get_number_of_days_in_a_month,
    get_readable_date,
)
from core.models import BiometricDetail, Department


### Attendance Management ###
def attendance_management(request, year="", month=""):
    context = {"list_of_months": get_list_of_months()}
    current_user = request.user
    now = datetime.datetime.now()
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
        daily_user_shift = get_user_daily_shift_record(
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
            }
        )
    context.update({"monthly_record_data": monthly_record_data})
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "attendance/attendance_management.html",
            "attendance_management_section",
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
        response = retarget(response, "#attendance_management_section")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "attendance/attendance_management.html", context)


def sync_user_attendance(request, year="", month=""):
    context = {"list_of_months": get_list_of_months()}
    current_user = request.user
    now = datetime.datetime.now()
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
        daily_user_shift = get_user_daily_shift_record(
            user=current_user,
            year=selected_year,
            month=selected_month,
            day=day,
        )
        monthly_record_data.append({"day": day, "daily_user_shift": daily_user_shift})
    context.update({"monthly_record_data": monthly_record_data})

    if request.htmx and request.method == "POST":
        current_biometric_data = BiometricDetail.objects.get(user=current_user)

        if current_biometric_data.user_id_in_device:
            attendance_records = AttendanceRecord.objects.filter(
                user_biometric_detail__isnull=True,
                user_id_from_device=current_biometric_data.user_id_in_device,
            )

            if attendance_records.exists():
                for attendance_record in attendance_record:
                    setattr(
                        attendance_record,
                        "user_biometric_detail",
                        current_biometric_data,
                    )
                    attendance_record.save()

            context.update(
                {
                    "show_alert": True,
                    "error": False,
                    "alert_message": "Attendance data successfully synced.",
                }
            )
            response = HttpResponse()
            response.content = render_block_to_string(
                "attendance/attendance_management.html",
                "attendance_management_section",
                context,
            )
            response = retarget(response, "#attendance_management_section")
            response = reswap(response, "outerHTML")
            return response


### Shift Management ###
def shift_management(request, department="", year="", month=""):
    context = {"list_of_months": get_list_of_months()}
    now = datetime.datetime.now()
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

    context.update(
        {
            "list_of_days": list_of_days,
            "selected_month": shift_month,
            "selected_year": shift_year,
            "selected_department": selected_department,
            "list_of_departments": list_of_departments,
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


### Biometric ###
@csrf_exempt
def get_attendance_request(request):
    return HttpResponse("OK")


@csrf_exempt
def attendance_cdata(request):
    if request.method == "POST":
        get_biometric_data()

    return HttpResponse("OK")
