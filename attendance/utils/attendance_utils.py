from datetime import datetime, time

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models import BooleanField, Case, Value, When
from django.utils.timezone import make_aware

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


def get_user_daily_shift_record_shifts(user, year: int, month: int, day_range):
    """
    Retrieves the user's shift records for each day in the given date range.
    Returns a dictionary with day as the key and the user's shift record as the value.
    If no shift record is found for a day, the value will be None.
    """
    DailyShiftRecordModel = apps.get_model("attendance", "DailyShiftRecord")

    daily_shift_record_data = {}

    selected_daily_shift_records = DailyShiftRecordModel.objects.filter(
        department=user.userdetails.department, date__year=year, date__month=month
    )

    daily_shift_record_dict = {}

    for record in selected_daily_shift_records:
        daily_shift_record_dict[record.date.day] = record

    for day in day_range:
        daily_shift_record = daily_shift_record_dict.get(day, None)

        if daily_shift_record:
            shift_record = daily_shift_record.shifts.filter(user=user).first()
            daily_shift_record_data[day] = shift_record
        else:
            daily_shift_record_data[day] = None

    return daily_shift_record_data


def get_user_clocked_time(user, year: int, month: int, day_range):
    """
    Retrieves the user's clock-in ("IN") and clock-out ("OUT") times for each day in the specified date range.
    Returns a dictionary with the day as the key and a sub-dictionary containing lists of "IN" and "OUT" records.
    """
    start_date = make_aware(
        datetime.combine(
            get_date_object(year=year, month=month, day=min(day_range)), time.min
        )
    )
    end_date = make_aware(
        datetime.combine(
            get_date_object(year=year, month=month, day=max(day_range)), time.max
        )
    )

    AttendanceRecordModel = apps.get_model("attendance", "AttendanceRecord")
    clocked_time_records = AttendanceRecordModel.objects.filter(
        user_biometric_detail=user.biometricdetail,
        timestamp__range=[start_date, end_date],
    ).order_by("timestamp")

    clocked_time_data_dict = {}

    for record in clocked_time_records:
        day = record.get_localtime_timestamp().day

        if day not in clocked_time_data_dict:
            clocked_time_data_dict[day] = {"IN": [], "OUT": []}

        if record.punch == "IN":
            clocked_time_data_dict[day]["IN"].append(record)
        elif record.punch == "OUT":
            clocked_time_data_dict[day]["OUT"].append(record)

    return {
        day: clocked_time_data_dict[day]
        for day in day_range
        if day in clocked_time_data_dict
    }


def get_employees_list_per_department():
    """
    Retrieves a list of active users, annotated with department existence and sorted by department and name.
    """
    all_users = (
        get_user_model()
        .objects.filter(is_active=True)
        .select_related("userdetails__department")
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
    """
    Retrieves a queryset of active employees who have at least one recorded attendance (clock-in).
    The results are ordered by the employee's first name.
    """
    return (
        get_user_model()
        .objects.filter(is_active=True, daily_shift_schedules__clock_in__isnull=False)
        .distinct()
        .order_by("first_name")
    )


def get_employees_with_same_day_different_shit(user=None, date=None):
    """
    Retrieves shifts for other employees in the same department on a specified date,
    excluding the shift of the given user. Returns a queryset of swappable shifts.
    If no matching records are found, returns an empty queryset.
    """
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
