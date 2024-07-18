import calendar
import datetime

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

from attendance.utils.biometric_utils import get_biometric_data
from attendance.utils.date_utils import get_list_of_months, get_readable_date
from attendance.models import Shift
from core.models import Department


### Attendance Management ###
def attendance_management(request):
    context = {}
    return render(request, "attendance/attendance_management.html", context)


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
    selected_date = get_readable_date(shift_year, int(shift_month), shift_day)
    shifts = Shift.objects.filter(is_active=True)

    context = {
        "selected_department": selected_department,
        "selected_date": selected_date,
        "shifts": shifts,
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


### Biometric ###
@csrf_exempt
def get_attendance_request(request):
    return HttpResponse("OK")


@csrf_exempt
def attendance_cdata(request):
    if request.method == "POST":
        get_biometric_data()

    return HttpResponse("OK")
