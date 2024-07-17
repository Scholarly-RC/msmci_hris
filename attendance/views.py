import calendar
import datetime
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from attendance.utils.biometric_utils import get_biometric_data
from attendance.utils.date_utils import get_list_of_months

from core.models import Department


def attendance_management(request):
    context = {}
    return render(request, "attendance/attendance_management.html", context)


def shift_management(request):
    context = {"list_of_months": get_list_of_months()}
    now = datetime.datetime.now()
    current_year = now.year
    current_month = now.month
    calendar.setfirstweekday(calendar.SUNDAY)
    list_of_days = calendar.monthcalendar(current_year, current_month)
    list_of_departments = Department.objects.filter(is_active=True).order_by("name")
    context.update(
        {
            "list_of_days": list_of_days,
            "selected_month": current_month,
            "selected_year": current_year,
            "list_of_departments": list_of_departments,
        }
    )
    return render(request, "attendance/shift_management.html", context)


@csrf_exempt
def get_attendance_request(request):
    return HttpResponse("OK")


@csrf_exempt
def attendance_cdata(request):
    if request.method == "POST":
        get_biometric_data()

    return HttpResponse("OK")
