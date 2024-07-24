from django.urls import include, path

from attendance import views as attendance_views

app_name = "attendance"

urlpatterns = [
    ### BIOMETRIC URLS ###
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
    ### SHIFT MANGEMENT URLS ###
    path(
        "shift-management/asign/user/<str:department>/<str:year>/<str:month>/<str:day>",
        attendance_views.assign_user_to_shift,
        name="assign_user_to_shift",
    ),
    path(
        "shift-management/asign/<str:department>/<str:year>/<str:month>/<str:day>",
        attendance_views.assign_shift,
        name="assign_shift",
    ),
    path(
        "shift-management/<str:department>/<str:year>/<str:month>",
        attendance_views.shift_management,
        name="shift_management_filtered",
    ),
    path(
        "shift-management",
        attendance_views.shift_management,
        name="shift_management",
    ),
    ### ATTENDANCE MANAGEMENT URLS ###
    path(
        "user-attendance-management/toggle-user-management-record-edit",
        attendance_views.toggle_user_management_record_edit,
        name="toggle_user_management_record_edit",
    ),
    path(
        "user-attendance-management/<str:user_id>/<str:year>/<str:month>",
        attendance_views.user_attendance_management,
        name="user_attendance_management_filtered",
    ),
    path(
        "user-attendance-management",
        attendance_views.user_attendance_management,
        name="user_attendance_management",
    ),
    path(
        "sync-user-attendance-data",
        attendance_views.sync_user_attendance,
        name="sync_user_attendance",
    ),
    path(
        "<str:year>/<str:month>",
        attendance_views.attendance_management,
        name="attendance_management_filtered",
    ),
    path(
        "",
        attendance_views.attendance_management,
        name="attendance_management",
    ),
]
