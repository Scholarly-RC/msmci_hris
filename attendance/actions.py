import calendar
import logging
from datetime import datetime, timedelta

from django.apps import apps
from django.db import transaction
from django.utils import timezone
from django.utils.timezone import localtime, make_aware

from attendance.utils.assign_shift_utils import get_employee_assignments
from attendance.utils.date_utils import (
    get_date_object,
    get_date_object_from_date_str,
    get_day_name_from_date,
    get_number_of_days_in_a_month,
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
    DailyShiftScheduleModel = apps.get_model("attendance", "DailyShiftSchedule")
    DailyShiftRecordModel = apps.get_model("attendance", "DailyShiftRecord")

    selected_date = get_date_object(int(year), int(month), int(day))

    try:
        daily_shift_record, daily_shift_record_created = (
            DailyShiftRecordModel.objects.get_or_create(
                department=department, date=selected_date
            )
        )

        new_daily_shift_schedule, new_daily_shift_schedule_created = (
            DailyShiftScheduleModel.objects.get_or_create(
                user=employee, shift=shift, date=selected_date
            )
        )

        if new_daily_shift_schedule not in daily_shift_record.shifts.all():
            daily_shift_record.shifts.add(new_daily_shift_schedule)
        else:
            daily_shift_record.shifts.remove(new_daily_shift_schedule)
            new_daily_shift_schedule.clock_in = None
            new_daily_shift_schedule.clock_out = None
            new_daily_shift_schedule.save()

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
    DailyShiftScheduleModel = apps.get_model("attendance", "DailyShiftSchedule")
    DailyShiftRecordModel = apps.get_model("attendance", "DailyShiftRecord")

    selected_date = get_date_object(int(year), int(month), int(day))
    try:
        daily_shift_record, daily_shift_record_created = (
            DailyShiftRecordModel.objects.get_or_create(
                department=department, date=selected_date
            )
        )

        _, list_of_assigned_users = get_employee_assignments(
            daily_shift_record, shifts, employees
        )

        current_employee_id_list = employees.values_list("id", flat=True)

        shift_schedules = DailyShiftScheduleModel.objects.filter(
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
def manually_set_user_clocked_time(payload):
    """
    Updates or creates an attendance record for a user with the specified clock-in/out time.
    Uses the provided user ID, date, and time to set the record.
    """
    UserModel = apps.get_model("auth", "User")
    AttendanceRecordModel = apps.get_model("attendance", "AttendanceRecord")
    try:
        selected_user_id = payload.get("selected_user")
        selected_user = UserModel.objects.get(id=selected_user_id)
        selected_date = get_date_object_from_date_str(payload.get("selected_date"))
        selected_time = get_time_object(payload.get("clocked_time"))
        selected_datetime = datetime.combine(selected_date, selected_time)
        punch = payload.get("punch")

        attendance_record, attendance_record_created = (
            AttendanceRecordModel.objects.get_or_create(
                user_biometric_detail=selected_user.biometricdetail,
                user_id_from_device=selected_user.biometricdetail.user_id_in_device,
                timestamp=make_aware(selected_datetime),
                punch=punch,
            )
        )
        return attendance_record

    except Exception:
        logger.error(
            "An error occurred while manually setting user clocked time", exc_info=True
        )
        raise


@transaction.atomic
def process_delete_user_clocked_time(payload):
    """
    Deletes a user attendance record based on the provided payload.
    """
    AttendanceRecordModel = apps.get_model("attendance", "AttendanceRecord")
    try:
        attendance_record = AttendanceRecordModel.objects.get(
            id=payload.get("attendance_record")
        )
        attendance_record.delete()
    except Exception:
        logger.error(
            "An error occurred while deleting a user clocked time", exc_info=True
        )
        raise


@transaction.atomic
def process_update_clocked_time(payload):
    """
    Deletes a user attendance record based on the provided payload.
    """
    AttendanceRecordModel = apps.get_model("attendance", "AttendanceRecord")
    try:
        attendance_record = AttendanceRecordModel.objects.get(
            id=payload.get("attendance_record")
        )
        selected_date = get_date_object_from_date_str(payload.get("selected_date"))
        selected_time = get_time_object(payload.get("clocked_time"))
        selected_datetime = make_aware(datetime.combine(selected_date, selected_time))
        attendance_record.timestamp = selected_datetime
        attendance_record.save()

        return attendance_record
    except Exception:
        logger.error(
            "An error occurred while deleting a user clocked time", exc_info=True
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
        start_time_2 = payload.get("start_time_2")
        end_time_2 = payload.get("end_time_2")

        shift_model = ShiftModel.objects.create(
            description=shift_description,
            start_time=start_time,
            end_time=end_time,
            start_time_2=start_time_2 if start_time_2 != "" else None,
            end_time_2=end_time_2 if end_time_2 != "" else None,
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
        shift_ids = payload.getlist("selected_shift")
        workweek = payload.getlist("selected_workweek")

        department = DepartmentModel.objects.get(id=department_id)
        department.workweek = workweek
        department.save()
        department.shifts.clear()
        if shift_ids:
            shifts = ShiftModel.objects.filter(id__in=shift_ids)
            department.shifts.add(*shifts)

        return department
    except Exception:
        logger.error(
            "An error occurred while modifying department shift settings", exc_info=True
        )
        raise


@transaction.atomic
def process_apply_department_fixed_or_dynamic_shift(department, month, year):
    current_date = localtime(timezone.now()).date()

    number_of_days = get_number_of_days_in_a_month(year=year, month=month)[1]

    UserModel = apps.get_model("auth", "User")
    DailyShiftRecordModel = apps.get_model("attendance", "DailyShiftRecord")
    DailyShiftScheduleModel = apps.get_model("attendance", "DailyShiftSchedule")

    department_users = UserModel.objects.filter(
        userdetails__department=department, is_active=True
    )

    shift = department.shifts.first()

    if department_users:
        for user in department_users:
            affected_date = current_date
            for day in range(current_date.day, number_of_days):
                affected_date += timedelta(days=1)
                daily_shift_record, daily_shift_record_created = (
                    DailyShiftRecordModel.objects.get_or_create(
                        date=affected_date, department=department
                    )
                )
                if not shift:
                    daily_shift_record.shifts.clear()
                else:
                    daily_shift_schedule, daily_shift_schedule_created = (
                        DailyShiftScheduleModel.objects.get_or_create(
                            date=affected_date, shift=shift, user=user
                        )
                    )
                    if department.has_fixed_schedule() and department.workweek:
                        if (
                            get_day_name_from_date(date=affected_date)
                            in department.workweek
                        ):
                            if (
                                daily_shift_schedule
                                not in daily_shift_record.shifts.all()
                            ):
                                daily_shift_record.shifts.add(daily_shift_schedule)
                        else:
                            daily_shift_record.shifts.remove(daily_shift_schedule)
                    else:
                        daily_shift_record.shifts.clear()
