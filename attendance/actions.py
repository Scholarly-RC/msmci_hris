import datetime

from django.apps import apps
from django.db import transaction

from attendance.utils.assign_shift_utils import get_employee_assignments
from attendance.utils.biometric_utils import process_biometric_data_from_device
from attendance.utils.date_utils import get_date_object, get_time_object


@transaction.atomic
def process_daily_shift_schedule(department, year, month, day, employee, shift):
    daily_shift_schedule_model = apps.get_model("attendance", "DailyShiftSchedule")
    daily_shift_records_model = apps.get_model("attendance", "DailyShiftRecord")

    selected_date = get_date_object(int(year), int(month), int(day))
    try:
        daily_shift_record, daily_shift_record_created = (
            daily_shift_records_model.objects.get_or_create(
                department=department, date=selected_date
            )
        )

        new_daily_shift_schedule, new_daily_shift_schedule_created = (
            daily_shift_schedule_model.objects.get_or_create(user=employee, shift=shift)
        )

        if new_daily_shift_schedule not in daily_shift_record.shifts.all():
            daily_shift_record.shifts.add(new_daily_shift_schedule)
        else:
            daily_shift_record.shifts.remove(new_daily_shift_schedule)

    except Exception as error:
        raise error


@transaction.atomic
def process_bulk_daily_shift_schedule(
    department, year, month, day, shifts, selected_shift, employees, deselect: bool
):
    daily_shift_schedule_model = apps.get_model("attendance", "DailyShiftSchedule")
    daily_shift_records_model = apps.get_model("attendance", "DailyShiftRecord")

    selected_date = get_date_object(int(year), int(month), int(day))
    try:
        daily_shift_record, daily_shift_record_created = (
            daily_shift_records_model.objects.get_or_create(
                department=department, date=selected_date
            )
        )

        _, list_of_assigned_users = get_employee_assignments(
            daily_shift_record, shifts, employees
        )

        current_employee_id_list = employees.values_list("id", flat=True)

        shift_schedules = daily_shift_schedule_model.objects.filter(
            shift=selected_shift, user__id__in=current_employee_id_list
        )

        if shift_schedules:
            if not deselect:
                shift_schedules = shift_schedules.exclude(
                    user_id__in=list_of_assigned_users
                )

                daily_shift_record.shifts.add(*shift_schedules)
            else:
                shift_schedules = shift_schedules.filter(
                    user_id__in=list_of_assigned_users
                )
                daily_shift_record.shifts.remove(*shift_schedules)

    except Exception as error:
        raise error


@transaction.atomic
def add_user_attendance_record(attendance_data):
    attendance_record_model = apps.get_model("attendance", "AttendanceRecord")

    user_biometric_detail, user_id_from_device, timestamp, punch = (
        process_biometric_data_from_device(attendance_data)
    )

    attendane_record = attendance_record_model.objects.create(
        user_id_from_device=user_id_from_device,
        punch=punch,
        timestamp=timestamp,
        user_biometric_detail=user_biometric_detail,
    )


@transaction.atomic
def manually_set_user_clocked_time(user, selected_date, clock_in_time, clock_out_time):
    attendance_record_model = apps.get_model("attendance", "AttendanceRecord")
    clock_in_punch = attendance_record_model.Punch.TIME_IN.value
    clock_out_punch = attendance_record_model.Punch.TIME_OUT.value

    biometric_detail_model = apps.get_model("core", "BiometricDetail")
    user_biometric_detail = biometric_detail_model.objects.get(user=user)

    current_modified_clock_in_record, current_modified_clock_in_record_created = (
        attendance_record_model.objects.get_or_create(
            user_biometric_detail=user_biometric_detail,
            user_id_from_device=user_biometric_detail.user_id_in_device,
            timestamp__date=selected_date,
            punch=clock_in_punch,
        )
    )

    if clock_in_time:
        clock_in_time = get_time_object(clock_in_time)
        clock_in_datetime = datetime.datetime.combine(selected_date, clock_in_time)
        current_modified_clock_in_record.timestamp = clock_in_datetime
        current_modified_clock_in_record.save()

    current_modified_clock_out_record, current_modified_clock_out_record_created = (
        attendance_record_model.objects.get_or_create(
            user_biometric_detail=user_biometric_detail,
            user_id_from_device=user_biometric_detail.user_id_in_device,
            timestamp__date=selected_date,
            punch=clock_out_punch,
        )
    )

    if clock_out_time:
        clock_out_time = get_time_object(clock_out_time)
        clock_out_datetime = datetime.datetime.combine(selected_date, clock_out_time)
        current_modified_clock_out_record.timestamp = clock_out_datetime
        current_modified_clock_out_record.save()
