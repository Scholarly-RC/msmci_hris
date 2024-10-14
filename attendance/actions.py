from datetime import datetime
import logging

from django.apps import apps
from django.db import transaction

from attendance.utils.assign_shift_utils import get_employee_assignments
from attendance.utils.biometric_utils import process_biometric_data_from_device
from attendance.utils.date_utils import (
    get_date_object,
    get_date_object_from_date_str,
    get_time_object,
)
from hris.exceptions import InvalidApproverPermission, InvalidApproverResponse

logger = logging.getLogger(__name__)


@transaction.atomic
def process_daily_shift_schedule(department, year, month, day, employee, shift):
    """
    Updates the shift schedule for a specific day.
    Adds or removes a shift assignment for an employee based on the current schedule.
    If the shift assignment does not already exist for the day, it is added; otherwise, it is removed.
    """
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

    except Exception:
        logger.error(
            "An error occurred while processing the daily shift schedule", exc_info=True
        )
        raise


@transaction.atomic
def process_bulk_daily_shift_schedule(
    department, year, month, day, shifts, selected_shift, employees, deselect: bool
):
    """
    Updates shift schedules for multiple employees on a specific day.
    Adds or removes shift assignments based on the `deselect` flag:
    - If `deselect` is False, it adds the selected shift to employees who are not already assigned.
    - If `deselect` is True, it removes the selected shift from employees who are assigned.
    """
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

    except Exception:
        logger.error(
            "An error occurred while processing bulk daily shift schedules",
            exc_info=True,
        )
        raise


@transaction.atomic
def manually_set_user_clocked_time(user, selected_date, clock_in_time, clock_out_time):
    """
    Manually sets or updates the clock-in and clock-out times for a user on a specific date.
    If provided, updates the clock-in and/or clock-out times in the attendance records.
    """
    try:
        DailyShiftRecordModel = apps.get_model("attendance", "DailyShiftRecord")

        daily_shift_records = DailyShiftRecordModel.objects.get(
            date=selected_date, department=user.userdetails.department
        )

        daily_clocked_time_shift = daily_shift_records.shifts.get(user=user)

        if clock_in_time:
            clock_in_time = get_time_object(clock_in_time)
            daily_clocked_time_shift.clock_in = datetime.combine(
                selected_date, clock_in_time
            )
        else:
            daily_clocked_time_shift.clock_in = None

        if clock_out_time:
            clock_out_time = get_time_object(clock_out_time)
            daily_clocked_time_shift.clock_out = datetime.combine(
                selected_date, clock_out_time
            )
        else:
            daily_clocked_time_shift.clock_out = None

        daily_clocked_time_shift.save()

    except Exception:
        logger.error(
            "An error occurred while manually setting user clocked time", exc_info=True
        )
        raise


@transaction.atomic
def process_add_holiday(payload):
    try:
        HolidayModel = apps.get_model("attendance", "Holiday")
        name = payload.get("holiday_name").strip()
        date_str = payload.get("holiday_date")
        date = get_date_object_from_date_str(date_str)
        is_regular = "is_holiday_regular" in payload

        holiday = HolidayModel.objects.create(
            name=name,
            year=date.year,
            month=date.month,
            day=date.day,
            is_regular=is_regular,
        )

        return holiday
    except Exception:
        logger.error("An error occurred while adding a holiday", exc_info=True)
        raise


@transaction.atomic
def process_delete_holiday(payload):
    try:
        HolidayModel = apps.get_model("attendance", "Holiday")
        holiday_id = payload.get("holiday")
        holiday = HolidayModel.objects.get(id=holiday_id)
        holiday.delete()
    except Exception:
        logger.error("An error occurred while deleting a holiday", exc_info=True)
        raise


@transaction.atomic
def process_create_overtime_request(user, payload):
    try:
        UserModel = apps.get_model("auth", "User")
        OvertimeModel = apps.get_model("attendance", "OverTime")
        pending_status = OvertimeModel.Status.PENDING.value
        selected_approver_id = payload.get("selected_approver")
        selected_approver = UserModel.objects.get(id=selected_approver_id)
        date_str = payload.get("overtime_date")
        overtime_date = get_date_object_from_date_str(date_str)

        overtime = OvertimeModel.objects.create(
            user=user,
            approver=selected_approver,
            date=overtime_date,
            status=pending_status,
        )
        return overtime
    except Exception:
        logger.error(
            "An error occurred while creating an overtime request", exc_info=True
        )
        raise


@transaction.atomic
def process_respond_to_overtime_request(user, payload):
    try:
        OvertimeModel = apps.get_model("attendance", "OverTime")
        overtime_status = OvertimeModel.Status
        overtime_request_id = payload.get("overtime_request")
        response = payload.get("response")
        overtime_request = OvertimeModel.objects.get(id=overtime_request_id)

        if overtime_request.approver != user:
            raise InvalidApproverPermission(
                "You do not have permission to respond to this overtime request."
            )

        if response == "APPROVE":
            overtime_request.status = overtime_status.APPROVED.value
        elif response == "REJECT":
            overtime_request.status = overtime_status.REJECTED.value
        else:
            raise InvalidApproverResponse(
                "Only 'Approve' or 'Reject' responses are allowed."
            )

        overtime_request.save()

        return overtime_request
    except Exception:
        logger.error(
            "An error occurred while responding to an overtime request", exc_info=True
        )
        raise


@transaction.atomic
def process_deleting_overtime_request(payload):
    try:
        OvertimeModel = apps.get_model("attendance", "OverTime")
        overtime_request_id = payload.get("overtime_request")
        overtime_request = OvertimeModel.objects.get(id=overtime_request_id)
        overtime_request.delete()
    except Exception:
        logger.error(
            "An error occurred while deleting an overtime request", exc_info=True
        )
        raise


@transaction.atomic
def process_create_new_shift(payload):
    try:
        ShiftModel = apps.get_model("attendance", "Shift")

        shift_description = payload.get("shift_description").strip()
        start_time = get_time_object(payload.get("start_time"))
        end_time = get_time_object(payload.get("end_time"))

        shift_model = ShiftModel.objects.create(
            description=shift_description, start_time=start_time, end_time=end_time
        )

        return shift_model
    except Exception:
        logger.error("An error occurred while creating a new shift", exc_info=True)
        raise


@transaction.atomic
def process_removing_shift(payload):
    try:
        ShiftModel = apps.get_model("attendance", "Shift")
        shift_id = payload.get("shift")
        shift = ShiftModel.objects.get(id=shift_id)
        shift.delete()
    except Exception:
        logger.error("An error occurred while removing a shift", exc_info=True)
        raise


@transaction.atomic
def process_modify_department_shift(payload):
    try:
        DepartmentModel = apps.get_model("core", "Department")
        ShiftModel = apps.get_model("attendance", "Shift")

        department_id = payload.get("department")
        shift_id = payload.get("shift")

        department = DepartmentModel.objects.get(id=department_id)
        shift = ShiftModel.objects.get(id=shift_id)

        if "selected" in payload:
            shift.departments.add(department)
        else:
            shift.departments.remove(department)

        return shift, department
    except Exception:
        logger.error(
            "An error occurred while modifying department shift", exc_info=True
        )
        raise
