from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models import BooleanField, Case, Value, When

from attendance.utils.date_utils import get_date_object, get_date_object_from_date_str


def get_user_daily_shift_record(department, year: int, month: int, day: int):
    """
    Retrieves the daily shift record for a specific department on a given date.
    """
    DailyShiftRecordModel = apps.get_model("attendance", "DailyShiftRecord")
    selected_date = get_date_object(year=year, month=month, day=day)
    selected_daily_shift_record = DailyShiftRecordModel.objects.filter(
        date=selected_date, department=department
    ).first()

    return selected_daily_shift_record


def get_user_daily_shift_record_shifts(user, year: int, month: int, day: int):
    """
    Retrieves the shift record for a specific user on a given date.
    """
    user_daily_shift_record = get_user_daily_shift_record(
        user.userdetails.department, year, month, day
    )

    if user_daily_shift_record:
        return user_daily_shift_record.shifts.filter(user=user).first()


def get_user_clocked_time(user, year: int, month: int, day: int):
    """
    Retrieves the user's clock-in ("IN") and clock-out ("OUT") times for a specified date,
    returning them as separate querysets within a dictionary. The date is determined by the
    provided year, month, and day, and attendance records are fetched from the `AttendanceRecord` model.
    """
    selected_date = get_date_object(year=year, month=month, day=day)

    AttendanceRecordModel = apps.get_model("attendance", "AttendanceRecord")

    clocked_time = AttendanceRecordModel.objects.filter(
        user_biometric_detail=user.biometricdetail, timestamp__date=selected_date
    ).order_by("timestamp")

    clocked_time_data = {
        "IN": clocked_time.filter(punch="IN"),
        "OUT": clocked_time.filter(punch="OUT"),
    }

    return clocked_time_data


def get_employees_list_per_department():
    """
    Retrieves a list of active users, annotated with department existence and sorted by department and name.
    """
    all_users = (
        get_user_model()
        .objects.filter(is_active=True)
        .annotate(
            department_exists=Case(
                When(userdetails__department__isnull=True, then=Value(False)),
                default=Value(True),
                output_field=BooleanField(),
            )
        )
        .order_by("-userdetails__department", "first_name", "-department_exists")
    )
    return all_users


def get_employees_with_attendance_record():
    return (
        get_user_model()
        .objects.filter(is_active=True, daily_shift_schedules__clock_in__isnull=False)
        .distinct()
        .order_by("first_name")
    )


def get_employees_with_same_day_different_shit(user=None, date=None):
    DailyShiftRecordModel = apps.get_model("attendance", "DailyShiftRecord")
    if date:
        selected_date = get_date_object_from_date_str(date)
        has_record_on_date = DailyShiftRecordModel.objects.filter(date=selected_date)
        if has_record_on_date:
            department = user.userdetails.department
            shifts = DailyShiftRecordModel.objects.get(
                department=department, date=selected_date
            ).shifts.all()
            user_shift = shifts.filter(user=user).first()
            if user_shift:
                selected_shift = user_shift.shift
                swappable_shifts = shifts.exclude(shift=selected_shift)
                return swappable_shifts

    return DailyShiftRecordModel.objects.none()
