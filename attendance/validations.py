from django.apps import apps

from attendance.utils.date_utils import get_time_object


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

    if not shift_description:
        context["shift_description_error"] = "Shift description is required."

    if not start_time:
        context["start_time_error"] = "Start time is required."

    if not end_time:
        context["end_time_error"] = "End time is required."

    if start_time and end_time:
        start_time = get_time_object(start_time)
        end_time = get_time_object(end_time)

        if ShiftModel.objects.filter(start_time=start_time, end_time=end_time).exists():
            context["shift_conflict_error"] = (
                "A shift with the same start and end time already exists."
            )

    return context
