import datetime

from django.apps import apps
from django.db.models import DurationField, ExpressionWrapper, F, Func, Min, Value
from django.db.models.functions import Abs
from django.utils.timezone import make_aware

from attendance.models import AttendanceRecord
from attendance.utils.biometric_utils import get_biometric_detail_from_user_id
from attendance.utils.date_utils import get_date_object


def get_user_daily_shift_record(user, year: int, month: int, day: int):
    daily_shift_record_model = apps.get_model("attendance", "DailyShiftRecord")
    selected_date = get_date_object(year=year, month=month, day=day)
    selected_daily_shift_record = daily_shift_record_model.objects.filter(
        date=selected_date, department=user.userdetails.department
    ).first()

    if selected_daily_shift_record:
        shift = selected_daily_shift_record.shifts.filter(user=user).first()
        return shift


def get_user_clocked_time(user, year: int, month: int, day: int, shift):
    selected_date = get_date_object(year=year, month=month, day=day)
    user_biometric_detail = get_biometric_detail_from_user_id(user_id=user.id)
    clock_in_punch = AttendanceRecord.Punch.TIME_IN.value
    clock_out_punch = AttendanceRecord.Punch.TIME_OUT.value

    current_attendance_record = AttendanceRecord.objects.filter(
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

    clock_in_timestamp = _get_timestamp_time(
        clock_in_punch, shift.start_time if shift else None
    )

    clock_out_timestamp = _get_timestamp_time(
        clock_out_punch, shift.end_time if shift else None
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
        if clock_in_timestamp
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

    clocked_time = {
        "clock_in": clock_in_timestamp,
        "clock_out": clock_out_timestamp,
        "clock_in_time_diff_formatted": clock_in_time_diff_formatted,
        "clock_out_time_diff_formatted": clock_out_time_diff_formatted,
    }

    return clocked_time
