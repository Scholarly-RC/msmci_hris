import datetime

from django.apps import apps
from django.contrib.auth.models import User
from django.db.models import BooleanField, Case, Q, Value, When

from attendance.utils.biometric_utils import get_biometric_detail_from_user_id
from attendance.utils.date_utils import (
    get_date_object,
    get_twenty_four_hour_time_str_from_time_object,
)


def get_user_daily_shift_record(department, year: int, month: int, day: int):
    """
    Retrieves the daily shift record for a specific department on a given date.
    """
    daily_shift_record_model = apps.get_model("attendance", "DailyShiftRecord")
    selected_date = get_date_object(year=year, month=month, day=day)
    selected_daily_shift_record = daily_shift_record_model.objects.filter(
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


def get_user_clocked_time(user, year: int, month: int, day: int, shift):
    """
    Retrieves and calculates the clock-in and clock-out times for a user on a specific date,
    including their time differences from the expected shift times.
    """
    attendance_record_model = apps.get_model("attendance", "AttendanceRecord")

    selected_date = get_date_object(year=year, month=month, day=day)
    user_biometric_detail = get_biometric_detail_from_user_id(user_id=user.id)
    clock_in_punch = attendance_record_model.Punch.TIME_IN.value
    clock_out_punch = attendance_record_model.Punch.TIME_OUT.value

    current_attendance_record = attendance_record_model.objects.filter(
        user_biometric_detail=user_biometric_detail, timestamp__date=selected_date
    )

    punch_records = {
        clock_in_punch: current_attendance_record.filter(punch=clock_in_punch),
        clock_out_punch: current_attendance_record.filter(punch=clock_out_punch),
    }

    def _get_timestamp_time(punch, base_time):
        records_with_punch = punch_records[punch]
        record = records_with_punch.first()
        return record.get_timestamp_localtime().time() if record else None

    clock_in_timestamp = (
        _get_timestamp_time(clock_in_punch, shift.start_time) if shift else None
    )

    clock_out_timestamp = (
        _get_timestamp_time(clock_out_punch, shift.end_time) if shift else None
    )

    def _get_time_difference(from_time, to_time):
        # Combine the time with the selected date
        from_time = datetime.datetime.combine(selected_date, from_time)
        to_time = datetime.datetime.combine(selected_date, to_time)

        # Calculate the difference between the two datetime objects
        time_difference = to_time - from_time
        time_difference_total_seconds = time_difference.total_seconds()

        # Get the total difference in minutes
        total_minutes_difference = int(time_difference_total_seconds // 60)

        # Calculate hours and remaining minutes
        hours_difference = abs(total_minutes_difference) // 60
        minutes_difference = abs(total_minutes_difference) % 60

        # Build the output string
        if total_minutes_difference > 0:
            if hours_difference > 0:
                return (
                    f"+{hours_difference}h {minutes_difference}m"
                    if minutes_difference > 0
                    else f"+{hours_difference}h"
                )
            return f"+{minutes_difference}m"
        elif total_minutes_difference < 0:
            if hours_difference > 0:
                return (
                    f"-{hours_difference}h {minutes_difference}m"
                    if minutes_difference > 0
                    else f"-{hours_difference}h"
                )
            return f"-{minutes_difference}m"
        else:
            return "On Time"

    clock_in_time_difference = (
        _get_time_difference(clock_in_timestamp, shift.start_time)
        if clock_in_timestamp
        else None
    )
    clock_out_time_difference = (
        _get_time_difference(shift.end_time, clock_out_timestamp)
        if clock_out_timestamp
        else None
    )

    clock_in_time_str = (
        get_twenty_four_hour_time_str_from_time_object(clock_in_timestamp)
        if clock_in_timestamp
        else ""
    )

    clock_out_time_str = (
        get_twenty_four_hour_time_str_from_time_object(clock_out_timestamp)
        if clock_out_timestamp
        else ""
    )

    clocked_time = {
        "clock_in": clock_in_timestamp,
        "clock_out": clock_out_timestamp,
        "clock_in_str": clock_in_time_str,
        "clock_out_str": clock_out_time_str,
        "clock_in_time_diff_formatted": clock_in_time_difference,
        "clock_out_time_diff_formatted": clock_out_time_difference,
    }

    return clocked_time


def get_employees_list_per_department():
    """
    Retrieves a list of active users, annotated with department existence and sorted by department and name.
    """
    all_users = (
        User.objects.filter(is_active=True)
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
        User.objects.filter(
            Q(biometricdetail__user_id_in_device__isnull=False)
            & Q(biometricdetail__attendance_records__isnull=False)
        )
        .distinct()
        .order_by("first_name")
    )
