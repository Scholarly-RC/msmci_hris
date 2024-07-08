from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from attendance.utils.biometric_utils import get_biometric_data


def attendance_management(request):
    context = {}
    return render(request, "attendance/attendance_management.html", context)


@csrf_exempt
def get_attendance_request(request):
    return HttpResponse("OK")


@csrf_exempt
def attendance_cdata(request):
    if request.method == "POST":
        get_biometric_data()

    return HttpResponse("OK")
