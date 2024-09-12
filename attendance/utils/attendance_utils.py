import datetime

from django.apps import apps
from django.contrib.auth.models import User
from django.db.models import (
    BooleanField,
    Case,
    DurationField,
    ExpressionWrapper,
    F,
    Value,
    When,
)
from django.db.models.functions import Abs
from django.utils.timezone import make_aware

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
        if records_with_punch.count() > 1 and base_time:
            current_target_datetime = datetime.datetime.combine(
                selected_date, base_time
            )
            current_target_datetime = make_aware(current_target_datetime)
            record = (
                records_with_punch.annotate(
                    time_diff=Abs(
                        ExpressionWrapper(
                            F("timestamp") - Value(current_target_datetime),
                            output_field=DurationField(),
                        )
                    )
                )
                .order_by("time_diff")
                .first()
            )
            records_with_punch.exclude(id=record.id).delete()
        else:
            record = current_attendance_record.filter(punch=punch).first()
        return record.get_timestamp_localtime().time() if record else None

    clock_in_timestamp = (
        _get_timestamp_time(clock_in_punch, shift.start_time) if shift else None
    )

    clock_out_timestamp = (
        _get_timestamp_time(clock_out_punch, shift.end_time) if shift else None
    )

    def _get_time_difference(from_time, to_time):
        from_time = datetime.datetime.combine(selected_date, from_time)
        to_time = datetime.datetime.combine(selected_date, to_time)

        # Calculate the difference between the two datetime objects
        time_difference = to_time - from_time
        time_difference_total_seconds = time_difference.total_seconds()

        # Get the difference in minutes
        hours_difference = time_difference_total_seconds // 3600
        minutes_difference = (time_difference_total_seconds % 3600) // 60

        return int(hours_difference), int(minutes_difference)

    clock_in_time_difference = (
        _get_time_difference(shift.start_time, clock_in_timestamp)
        if clock_in_timestamp
        else None
    )
    clock_out_time_difference = (
        _get_time_difference(shift.end_time, clock_out_timestamp)
        if clock_out_timestamp
        else None
    )

    def _format_time_difference(hours, minutes):
        if hours == 0 and minutes == 0:
            return "On time"
        formatted_time = ""
        if hours:
            formatted_time += f"{hours}h "
        if minutes:
            formatted_time += f"{minutes}m"
        return formatted_time.strip()

    clock_in_time_diff_formatted = (
        _format_time_difference(*clock_in_time_difference)
        if clock_in_time_difference
        else None
    )
    clock_out_time_diff_formatted = (
        _format_time_difference(*clock_out_time_difference)
        if clock_out_time_difference
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
        "clock_in_time_diff_formatted": clock_in_time_diff_formatted,
        "clock_out_time_diff_formatted": clock_out_time_diff_formatted,
    }

    return clocked_time


def get_all_holidays_list():
    """
    Retrieves a list of all holidays from the Holiday model.
    """
    holiday_model = apps.get_model("attendance", "Holiday")
    all_holidays = holiday_model.objects.all()
    return all_holidays


def get_holiday_for_specific_month_and_year(month: int, year: int):
    """
    Retrieves holidays for a specific month and year, combining regular and non-regular holidays.
    """
    holidays_for_this_specific_month_and_year = (
        get_all_holidays_list()
        .filter(month=month, year=year, is_regular=False)
        .values_list("day", "name")
    )
    regular_holidays_for_this_specific_month_and_year = (
        get_all_holidays_list()
        .filter(month=month, is_regular=True)
        .values_list("day", "name")
    )
    combined_holidays = (
        holidays_for_this_specific_month_and_year
        | regular_holidays_for_this_specific_month_and_year
    )
    return combined_holidays


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
