from datetime import datetime

from django.apps import apps

from attendance.utils.date_utils import get_date_object_from_date_str, get_time_object


def add_holiday_validation(payload):
    context = {}

    holiday_name = payload.get("holiday_name").strip()

    if not holiday_name:
        context["empty_holiday_name"] = "Holiday name required."

    return context


def create_new_shift_validation(payload):
    context = {}

    ShiftModel = apps.get_model("attendance", "Shift")

    shift_description = payload.get("shift_description", "").strip()
    start_time = payload.get("start_time")
    end_time = payload.get("end_time")

    start_time_2 = payload.get("start_time_2")
    end_time_2 = payload.get("end_time_2")

    if not shift_description:
        context["shift_description_error"] = "Shift description is required."

    if not start_time:
        context["start_time_error"] = "Start time is required."

    if not end_time:
        context["end_time_error"] = "End time is required."

    if (start_time_2 or end_time_2) and (not start_time_2 or not end_time_2):
        context["second_time_error"] = (
            "A second start and end time are required for multiple time-in-time-out shifts."
        )

    if start_time and end_time:
        start_time = get_time_object(start_time)
        end_time = get_time_object(end_time)

        if ShiftModel.objects.filter(
            start_time=start_time,
            end_time=end_time,
            start_time_2=start_time_2 if start_time_2 != "" else None,
            end_time_2=end_time_2 if end_time_2 != "" else None,
        ).exists():
            context["shift_conflict_error"] = (
                "A shift with the same start and end time already exists."
            )

    return context


def add_new_clocked_time_validation(payload):
    context = {}
    UserModel = apps.get_model("auth", "User")
    AttendanceRecordModel = apps.get_model("attendance", "AttendanceRecord")

    selected_user_id = payload.get("selected_user")
    selected_user = UserModel.objects.get(id=selected_user_id)
    selected_date = get_date_object_from_date_str(payload.get("selected_date"))
    selected_time = get_time_object(payload.get("clocked_time"))
    selected_datetime = datetime.combine(selected_date, selected_time)
    punch = payload.get("punch")

    if selected_user.biometricdetail.attendance_records.filter(
        timestamp=selected_datetime, punch=punch
    ).exists():
        context["selected_time_already_exists_error"] = (
            "An attendance record for the selected time and punch already exists."
        )

    return context
