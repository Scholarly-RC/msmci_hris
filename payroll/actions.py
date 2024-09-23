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


@transaction.atomic
def process_adding_job(payload):
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
        raise error


@transaction.atomic
def process_modifying_job(payload):
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
        raise error


@transaction.atomic
def process_deleting_job(job_id):
    try:
        JobModel = apps.get_model("payroll", "Job")
        job = JobModel.objects.get(id=job_id)
        job.delete()

    except Exception as error:
        raise error


@transaction.atomic
def process_setting_minimum_wage_amount(amount):
    try:
        minimum_wage = get_minimum_wage_object()
        minimum_wage.amount = amount
        current_date = make_aware(datetime.now()).date().strftime("%Y-%m-%d")
        minimum_wage.history.append({"amount": amount, "date_set": current_date})
        minimum_wage.save()

        return minimum_wage

    except Exception as error:
        raise error


@transaction.atomic
def process_setting_deduction_config(payload):
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
        raise error


@transaction.atomic
def process_toggle_user_mp2_status(payload):
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
        raise error


@transaction.atomic
def process_setting_mp2_amount(payload):
    try:
        amount = payload.get("mp2_amount", 0)
        mp2 = get_mp2_object()

        mp2.amount = Decimal(amount)
        mp2.save()

        return mp2
    except Exception as error:
        raise error


@transaction.atomic
def process_get_or_create_user_payslip(
    user_id: int, month: int, year: int, period: str
):
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
        raise error


@transaction.atomic
def process_add_or_create_fixed_compensation(name: str, month: int, year: int):
    try:
        FixedCompensationModel = apps.get_model("payroll", "FixedCompensation")
        name = name.strip().title()
        return FixedCompensationModel.objects.get_or_create(
            name=name, month=month, year=year
        )

    except Exception as error:
        raise error


@transaction.atomic
def process_modifying_fixed_compensation(payload):
    try:
        FixedCompensationModel = apps.get_model("payroll", "FixedCompensation")
        compensation = FixedCompensationModel.objects.get(
            id=payload.get("selected_compensation")
        )
        compensation.amount = Decimal(payload.get("amount"))
        compensation.save()
        return compensation
    except Exception as error:
        raise error


@transaction.atomic
def process_removing_fixed_compensation(payload):
    try:
        FixedCompensationModel = apps.get_model("payroll", "FixedCompensation")
        compensation = FixedCompensationModel.objects.get(
            id=payload.get("selected_compensation")
        )
        compensation.delete()
    except Exception as error:
        raise error


@transaction.atomic
def process_modifying_fixed_compensation_users(
    user_id: int, compensation_id: int, remove: bool = False
):
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
        raise error


@transaction.atomic
def process_adding_variable_payslip_deduction(payload):
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
        raise error


@transaction.atomic
def process_removing_variable_payslip_deduction(payload):
    try:
        VariableDeductionModel = apps.get_model("payroll", "VariableDeduction")
        deduction_id = payload.get("deduction")

        VariableDeductionModel.objects.get(id=deduction_id).delete()

        return
    except Exception as error:
        raise error


@transaction.atomic
def process_adding_variable_payslip_compensation(payload):
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

        breakpoint()

        return new_variable_compensation
    except Exception as error:
        raise error


@transaction.atomic
def process_removing_variable_payslip_compensation(payload):
    try:
        VariableCompensationModel = apps.get_model("payroll", "VariableCompensation")
        compensation_id = payload.get("compensation")
        VariableCompensationModel.objects.get(id=compensation_id).delete()

        return
    except Exception as error:
        raise error


@transaction.atomic
def process_toggle_payslip_release_status(payload):
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
        raise error
