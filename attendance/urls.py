from django.urls import include, path

from attendance import views as attendance_views

app_name = "attendance"

urlpatterns = [
    path(
        "iclock/cdata",
        attendance_views.attendance_cdata,
        name="attendance_cdata",
    ),
    path(
        "iclock/getrequest",
        attendance_views.get_attendance_request,
        name="get_attendance_request",
    ),
    path(
        "shift",
        attendance_views.shift_management,
        name="shift_management",
    ),
    path(
        "",
        attendance_views.attendance_management,
        name="attendance_management",
    ),
]
