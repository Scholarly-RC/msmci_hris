from django.apps import apps
from django.db import transaction

from attendance.utils.assign_shift_utils import get_employee_assignments
from attendance.utils.date_utils import get_date_object
from attendance.utils.biometric_utils import process_biometric_data_from_device

from attendance.models import AttendanceRecord


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

                print(shift_schedules)

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
    user, user_id_from_device, timestamp, punch = process_biometric_data_from_device(
        attendance_data
    )

    attendane_record, attendane_record_created = AttendanceRecord.objects.get_or_create(
        user_id_from_device=user_id_from_device,
        punch=punch,
        defaults={"timestamp": timestamp, "user": user},
    )
