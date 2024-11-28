import logging
from datetime import datetime
from decimal import Decimal

from django.apps import apps
from django.db import transaction
from django.utils.timezone import make_aware

from payroll.utils import (
    get_deduction_configuration_object,
    get_deduction_configuration_with_submitted_changes,
    get_minimum_wage_object,
    get_mp2_object,
)

logger = logging.getLogger(__name__)


@transaction.atomic
def process_adding_job(payload):
    """
    Adds a new job position to the payroll system. This includes creating a new job with the specified
    title, job code, and salary grade, and associating it with the selected departments.
    """
    try:
        JobModel = apps.get_model("payroll", "Job")
        DepartmentModel = apps.get_model("core", "Department")
        selected_department = DepartmentModel.objects.filter(
            id__in=payload.getlist("selected_department")
        )

        new_job = JobModel.objects.create(
            title=payload.get("job_title"),
            code=payload.get("job_code"),
            salary_grade=payload.get("salary_grade"),
        )
        new_job.department.add(*selected_department)

        return new_job

    except Exception as error:
        logger.error("Failed to add new job", exc_info=True)
        raise


@transaction.atomic
def process_modifying_job(payload):
    """
    Modifies an existing job position in the payroll system. This updates the job's title, job code, salary grade,
    and associates it with the selected departments.
    """
    try:
        JobModel = apps.get_model("payroll", "Job")
        DepartmentModel = apps.get_model("core", "Department")

        selected_department = DepartmentModel.objects.filter(
            id__in=payload.getlist("selected_department", [])
        )

        job = JobModel.objects.get(id=payload.get("job", ""))
        job.title = payload.get("job_title")
        job.code = payload.get("job_code")
        job.salary_grade = payload.get("salary_grade")
        job.save()

        job.department.add(*selected_department)

        return job

    except Exception as error:
        logger.error("Failed to modify job", exc_info=True)
        raise


@transaction.atomic
def process_deleting_job(job_id):
    """
    Deletes a job position from the payroll system based on the provided job ID.
    """
    try:
        JobModel = apps.get_model("payroll", "Job")
        job = JobModel.objects.get(id=job_id)
        job.delete()

    except Exception as error:
        logger.error("Failed to delete job", exc_info=True)
        raise


@transaction.atomic
def process_setting_minimum_wage_amount(amount):
    """
    Sets the minimum wage amount for the company. This updates the current minimum wage and logs its history
    with the specified amount and the date it was set.
    """
    try:
        minimum_wage = get_minimum_wage_object()
        minimum_wage.amount = amount
        current_date = make_aware(datetime.now()).date().strftime("%Y-%m-%d")
        minimum_wage.history.append({"amount": amount, "date_set": current_date})
        minimum_wage.save()

        return minimum_wage

    except Exception as error:
        logger.error("Failed to set minimum wage amount", exc_info=True)
        raise


@transaction.atomic
def process_setting_deduction_config(payload):
    """
    Updates the deduction configuration based on the provided payload. This modifies the deduction settings
    and logs the history of changes made.
    """
    try:
        deduction_configuration = get_deduction_configuration_object()
        modified_payload = get_deduction_configuration_with_submitted_changes(
            payload, deduction_configuration
        )

        if modified_payload != deduction_configuration.config:
            deduction_configuration.config = modified_payload
            current_date = make_aware(datetime.now()).date().strftime("%Y-%m-%d")
            deduction_configuration.history.append(
                {"date_set": current_date, "config": modified_payload}
            )
            deduction_configuration.save()

        return deduction_configuration

    except Exception as error:
        logger.error("Failed to set deduction configuration", exc_info=True)
        raise


@transaction.atomic
def process_toggle_user_mp2_status(payload):
    """
    Toggles a user's MP2 status by adding or removing them from the MP2 group.
    Returns the updated MP2 object, user, and a boolean indicating if the user was added or removed.
    """
    try:
        UserModel = apps.get_model("auth", "User")

        mp2 = get_mp2_object()

        user_id = payload.get("selected_user", "")

        user = UserModel.objects.get(id=user_id)

        if user in mp2.users.all():
            mp2.users.remove(user)
            added = False
        else:
            mp2.users.add(user)
            added = True

        return mp2, user, added
    except Exception as error:
        logger.error("Failed to toggle MP2 status", exc_info=True)
        raise


@transaction.atomic
def process_setting_mp2_amount(payload):
    """
    Sets the MP2 amount to the specified value and saves the change.
    Returns the updated MP2 object.
    """
    try:
        amount = payload.get("mp2_amount", 0)
        mp2 = get_mp2_object()

        mp2.amount = Decimal(amount)
        mp2.save()

        return mp2
    except Exception as error:
        logger.error("Failed to set MP2 amount", exc_info=True)
        raise


@transaction.atomic
def process_get_or_create_user_payslip(
    user_id: int, month: int, year: int, period: str
):
    """
    Retrieves or creates a payslip for a user based on the given month, year, and period.
    Updates the payslip's salary and returns the user and the created/updated payslip.
    """
    try:
        PayslipModel = apps.get_model("payroll", "Payslip")
        UserModel = apps.get_model("auth", "User")

        user = UserModel.objects.get(id=user_id)

        payslip, _ = PayslipModel.objects.get_or_create(
            user=user,
            month=month,
            year=year,
            period=period,
            defaults={
                "rank": user.userdetails.rank,
            },
        )

        payslip.update_salary()

        return user, payslip
    except Exception as error:
        logger.error("Error getting or creating payslip for user", exc_info=True)
        raise


@transaction.atomic
def process_add_or_create_fixed_compensation(name: str, month: int, year: int):
    """
    Creates or retrieves a fixed compensation entry for a specified month and year.
    Returns the created or existing compensation object.
    """
    try:
        FixedCompensationModel = apps.get_model("payroll", "FixedCompensation")
        name = name.strip().title()
        return FixedCompensationModel.objects.get_or_create(
            name=name, month=month, year=year
        )

    except Exception as error:
        logger.error("Error adding or creating fixed compensation", exc_info=True)
        raise


@transaction.atomic
def process_modifying_fixed_compensation(payload):
    """
    Modifies an existing fixed compensation entry's amount based on the provided data.
    Returns the updated compensation object.
    """
    try:
        FixedCompensationModel = apps.get_model("payroll", "FixedCompensation")
        compensation = FixedCompensationModel.objects.get(
            id=payload.get("selected_compensation")
        )
        compensation.amount = Decimal(payload.get("amount"))
        compensation.save()
        return compensation
    except Exception as error:
        logger.error("Error modifying fixed compensation ID", exc_info=True)
        raise


@transaction.atomic
def process_removing_fixed_compensation(payload):
    """
    Deletes a specified fixed compensation entry.
    """
    try:
        FixedCompensationModel = apps.get_model("payroll", "FixedCompensation")
        compensation = FixedCompensationModel.objects.get(
            id=payload.get("selected_compensation")
        )
        compensation.delete()
    except Exception as error:
        logger.error("Error removing fixed compensation ID", exc_info=True)
        raise


@transaction.atomic
def process_modifying_fixed_compensation_users(
    user_id: int, compensation_id: int, remove: bool = False
):
    """
    Adds or removes a user from a fixed compensation entry based on the remove flag.
    Returns the updated compensation object and user.
    """
    try:
        FixedCompensationModel = apps.get_model("payroll", "FixedCompensation")
        UserModel = apps.get_model("auth", "User")
        user = UserModel.objects.get(id=user_id)
        compensation = FixedCompensationModel.objects.get(id=compensation_id)

        if not remove:
            compensation.users.add(user)
        else:
            compensation.users.remove(user)

        return compensation, user

    except Exception as error:
        logger.error("Error modifying fixed compensation for user ID", exc_info=True)
        raise


@transaction.atomic
def process_adding_variable_payslip_deduction(payload):
    """
    Adds a variable deduction to a specified payslip with the given deduction name and amount.
    Returns the newly created variable deduction object.
    """
    try:
        VariableDeduction = apps.get_model("payroll", "VariableDeduction")
        PayslipModel = apps.get_model("payroll", "Payslip")
        selected_payslip_id = payload.get("payslip")
        selected_payslip = PayslipModel.objects.get(id=selected_payslip_id)

        deduction_name = payload.get("deduction_name").strip()
        deduction_amount = Decimal(payload.get("deduction_amount", 0))

        new_deduction = VariableDeduction.objects.create(
            name=deduction_name, payslip=selected_payslip, amount=deduction_amount
        )

        return new_deduction
    except Exception as error:
        logger.error("Error adding variable payslip deduction", exc_info=True)
        raise


@transaction.atomic
def process_removing_variable_payslip_deduction(payload):
    """
    Removes a specified variable deduction from a payslip.
    """
    try:
        VariableDeductionModel = apps.get_model("payroll", "VariableDeduction")
        deduction_id = payload.get("deduction")

        VariableDeductionModel.objects.get(id=deduction_id).delete()

        return
    except Exception as error:
        logger.error("Error removing variable payslip deduction", exc_info=True)
        raise


@transaction.atomic
def process_adding_variable_payslip_compensation(payload):
    """
    Adds a variable compensation to a specified payslip with the given compensation name and amount.
    Returns the newly created variable compensation object.
    """
    try:
        VariableCompensationModel = apps.get_model("payroll", "VariableCompensation")
        PayslipModel = apps.get_model("payroll", "Payslip")
        selected_payslip_id = payload.get("payslip")
        selected_payslip = PayslipModel.objects.get(id=selected_payslip_id)

        variable_name = payload.get("compensation_name").strip()
        variable_amount = Decimal(payload.get("compensation_amount", 0))

        new_variable_compensation = VariableCompensationModel.objects.create(
            name=variable_name, payslip=selected_payslip, amount=variable_amount
        )

        return new_variable_compensation
    except Exception as error:
        logger.error("Error adding variable payslip compensation", exc_info=True)
        raise


@transaction.atomic
def process_removing_variable_payslip_compensation(payload):
    """
    Removes a specified variable compensation from a payslip.
    """
    try:
        VariableCompensationModel = apps.get_model("payroll", "VariableCompensation")
        compensation_id = payload.get("compensation")
        VariableCompensationModel.objects.get(id=compensation_id).delete()

        return
    except Exception as error:
        logger.error("Error removing variable payslip compensation", exc_info=True)
        raise


@transaction.atomic
def process_toggle_payslip_release_status(payload):
    """
    Toggles the release status of a payslip. Sets the release date if released, or clears it if unreleased.
    Returns the updated payslip object.
    """
    try:
        PayslipModel = apps.get_model("payroll", "Payslip")
        payslip_id = payload.get("payslip")
        payslip = PayslipModel.objects.get(id=payslip_id)

        payslip.released = not payslip.released

        if payslip.released:
            current_datetime = make_aware(datetime.now())
            payslip.release_date = current_datetime
        else:
            payslip.release_date = None

        payslip.save()

        return payslip
    except Exception as error:
        logger.error("Error toggling payslip release status", exc_info=True)
        raise


@transaction.atomic
def process_creating_thirteenth_month_pay(payload):
    """
    Creates a new thirteenth month pay record for a user, or retrieves an existing one if it already exists for the specified month and year.
    Returns the created or retrieved thirteenth month pay object.
    """
    try:
        ThirteenthMonthPayModel = apps.get_model("payroll", "ThirteenthMonthPay")
        UserModel = apps.get_model("auth", "User")
        user_id = payload.get("user")
        selected_month = payload.get("selected_month")
        selected_year = payload.get("selected_year")
        amount = payload.get("amount")
        user = UserModel.objects.get(id=user_id)
        thirteenth_month_pay, _ = ThirteenthMonthPayModel.objects.get_or_create(
            user=user,
            month=selected_month,
            year=selected_year,
            defaults={"amount": amount},
        )

        return thirteenth_month_pay
    except Exception as error:
        logger.error("Error creating thirteenth month pay", exc_info=True)
        raise


@transaction.atomic
def process_updating_thirteenth_month_pay(payload):
    """
    Updates the amount of an existing thirteenth month pay record.
    Returns the updated thirteenth month pay object.
    """
    try:
        ThirteenthMonthPayModel = apps.get_model("payroll", "ThirteenthMonthPay")
        thirteenth_month_pay_id = payload.get("thirteenth_month_pay")
        thirteenth_month_pay = ThirteenthMonthPayModel.objects.get(
            id=thirteenth_month_pay_id
        )
        amount = Decimal(payload.get("amount", 0))
        thirteenth_month_pay.amount = amount
        thirteenth_month_pay.save()

        return thirteenth_month_pay
    except Exception as error:
        logger.error("Error updating thirteenth month pay", exc_info=True)
        raise


@transaction.atomic
def process_toggling_thirteenth_month_pay_release(payload):
    """
    Toggles the release status of a thirteenth month pay record and updates its release date accordingly.
    Returns the updated thirteenth month pay object.
    """
    try:
        ThirteenthMonthPayModel = apps.get_model("payroll", "ThirteenthMonthPay")
        thirteenth_month_pay_id = payload.get("thirteenth_month_pay")
        thirteenth_month_pay = ThirteenthMonthPayModel.objects.get(
            id=thirteenth_month_pay_id
        )
        thirteenth_month_pay.released = not thirteenth_month_pay.released
        thirteenth_month_pay.release_date = (
            make_aware(datetime.now()) if thirteenth_month_pay.released else None
        )
        thirteenth_month_pay.save()

        return thirteenth_month_pay
    except Exception as error:
        logger.error("Error toggling thirteenth month pay release", exc_info=True)
        raise


@transaction.atomic
def process_delete_thirteenth_month_pay(payload):
    """
    Deletes a specified thirteenth month pay record.
    """
    try:
        ThirteenthMonthPayModel = apps.get_model("payroll", "ThirteenthMonthPay")
        thirteenth_month_pay_id = payload.get("thirteenth_month_pay")
        thirteenth_month_pay = ThirteenthMonthPayModel.objects.get(
            id=thirteenth_month_pay_id
        )

        thirteenth_month_pay.delete()
    except Exception as error:
        logger.error("Error deleting thirteenth month pay", exc_info=True)
        raise


@transaction.atomic
def process_add_thirteenth_month_pay_variable_deduction(payload):
    """
    Adds a variable deduction to a specified thirteenth month pay record.
    Returns the updated thirteenth month pay object.
    """
    try:
        ThirteenthMonthPayVariableDeductionModel = apps.get_model(
            "payroll", "ThirteenthMonthPayVariableDeduction"
        )
        ThirteenthMonthPayModel = apps.get_model("payroll", "ThirteenthMonthPay")
        thirteenth_month_pay_id = payload.get("thirteenth_month_pay")
        deduction_name = payload.get("deduction_name")
        deduction_amount = payload.get("deduction_amount")
        thirteenth_month_pay = ThirteenthMonthPayModel.objects.get(
            id=thirteenth_month_pay_id
        )
        thirteenth_month_pay_variable_deduction = (
            ThirteenthMonthPayVariableDeductionModel.objects.create(
                thirteenth_month_pay=thirteenth_month_pay,
                name=deduction_name,
                amount=deduction_amount,
            )
        )

        return thirteenth_month_pay
    except Exception as error:
        logger.error("Error adding variable deduction", exc_info=True)
        raise


@transaction.atomic
def process_remove_thirteenth_month_pay_variable_deduction(payload):
    """
    Removes a specified variable deduction from a thirteenth month pay record.
    Returns the updated thirteenth month pay object.
    """
    try:
        ThirteenthMonthPayVariableDeductionModel = apps.get_model(
            "payroll", "ThirteenthMonthPayVariableDeduction"
        )
        thirteenth_month_pay_deduction_id = payload.get(
            "thirteenth_month_pay_deduction"
        )
        thirteenth_month_pay_variable_deduction = (
            ThirteenthMonthPayVariableDeductionModel.objects.get(
                id=thirteenth_month_pay_deduction_id
            )
        )
        thirteenth_month_pay = (
            thirteenth_month_pay_variable_deduction.thirteenth_month_pay
        )
        thirteenth_month_pay_variable_deduction.delete()

        return thirteenth_month_pay
    except Exception as error:
        logger.error("Error removing variable deduction", exc_info=True)
        raise
