import copy
import re
from datetime import datetime
from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.db.models import Sum
from django.utils.timezone import make_aware

from hris.exceptions import InitializationError


def get_department_list():
    """
    Retrieves a list of active departments from the database, ordered by their name.
    """
    DepartmentModel = apps.get_model("core", "Department")
    return DepartmentModel.objects.filter(is_active=True).order_by("name")


def get_job_list(department: int):
    """
    Retrieves a list of active jobs from the database, ordered by job title.
    Optionally filters the list to include only jobs in the specified department.
    """
    JobModel = apps.get_model("payroll", "Job")
    jobs = JobModel.objects.filter(is_active=True).order_by("title")
    if not department:
        return jobs
    return jobs.filter(department=department)


def get_rank_choices(department_id: int) -> list:
    rank_choices = []
    jobs = get_job_list(department_id)

    for job in jobs:
        salary_data = job.get_salary_data()

        job_rank_choices = {}
        rank_names_list = []

        for salary_rank in salary_data:
            for rank_name, rank_details in salary_rank.items():
                rank_names_list.append(rank_name)
                for step in rank_details.get("steps", []):
                    for step_name, _ in step.items():
                        rank_names_list.append(f"{rank_name} - {step_name}")

        job_rank_choices[job.title] = rank_names_list
        rank_choices.append(job_rank_choices)

    return rank_choices


def get_minimum_wage_object():
    """
    Retrieves the first MinimumWage record from the database.
    If no records are found, an InitializationError is raised.
    """
    MinimumWageModel = apps.get_model("payroll", "MinimumWage")
    if not MinimumWageModel.objects.exists():
        raise InitializationError(
            "Minimum Wage configuration settings have not been initialized."
        )
    return MinimumWageModel.objects.first()


def calculate_basic_salary_for_grade(salary_grade: int) -> float:
    """
    Calculates the basic salary for a given salary grade based on a base salary and a multiplier.
    The salary increases by applying the multiplier for each grade above the base grade.
    Raises ValueError if the provided salary grade is less than 1.
    """

    base_salary = get_minimum_wage_object().amount
    salary_multiplier = Decimal(settings.BASIC_SALARY_MULTIPLIER)

    if salary_grade < 1:
        raise ValueError("Invalid Salary Grade")

    def _compute_salary(current_salary, remaining_grades):
        if remaining_grades == 0:
            return current_salary
        updated_salary = current_salary * salary_multiplier
        return _compute_salary(updated_salary, remaining_grades - 1)

    basic_salary = _compute_salary(base_salary, salary_grade - 1)
    return Decimal(basic_salary)


def calculate_basic_salary_steps(basic_salary: int) -> list:
    """
    Calculates the salary at each step based on an initial basic salary and a step multiplier.
    Returns a list of dictionaries where each dictionary represents the salary at a specific step.
    The calculation continues for a number of steps defined in the settings.
    """
    basic_salary_steps = []

    def _compute_step(current_salary, remaining_step):
        update_salary = current_salary * Decimal(settings.BASIC_SALARY_STEP_MULTIPLIER)
        basic_salary_steps.append(
            {f"STEP {remaining_step}": Decimal(round(update_salary, 2))}
        )
        if remaining_step == settings.BASIC_SALARY_STEPS:
            return
        return _compute_step(update_salary, remaining_step + 1)

    _compute_step(basic_salary, 1)

    return basic_salary_steps


def get_deduction_configuration_object():
    """
    Retrieves the first MandatoryDeductionConfiguration record from the database.
    If no records are found, an InitializationError is raised.
    """
    MandatoryDeductionConfigurationModel = apps.get_model(
        "payroll", "MandatoryDeductionConfiguration"
    )

    if not MandatoryDeductionConfigurationModel.objects.exists():
        raise InitializationError(
            "Deduction configuration settings have not been initialized."
        )

    return MandatoryDeductionConfigurationModel.objects.first()


def get_deduction_configuration_with_submitted_changes(
    payload, deduction_configuration
):
    def _update_config_data(config_copy, payload, config_keys):
        config_data = config_copy.get("data")
        for config_key, payload_key in config_keys.items():
            config_data[config_key] = payload.get(payload_key)

    data = []

    # SSS Configuration
    sss_config = deduction_configuration.sss_config()
    sss_config_copy = copy.deepcopy(sss_config)
    sss_keys = {
        "min_compensation": "sss_minimum_compensation",
        "max_compensation": "sss_maximum_compensation",
        "min_contribution": "sss_minimum_contribution",
        "max_contribution": "sss_maximum_contribution",
        "contribution_difference": "sss_contribution_difference",
    }
    _update_config_data(sss_config_copy, payload, sss_keys)
    data.append(sss_config_copy)

    # PhilHealth Configuration
    philhealth_config = deduction_configuration.philhealth_config()
    philhealth_config_copy = copy.deepcopy(philhealth_config)
    philhealth_keys = {
        "min_compensation": "philhealth_minimum_compensation",
        "max_compensation": "philhealth_maximum_compensation",
        "min_contribution": "philhealth_minimum_contribution",
        "max_contribution": "philhealth_maximum_contribution",
        "rate": "philhealth_contribution_rate",
    }
    _update_config_data(philhealth_config_copy, payload, philhealth_keys)
    data.append(philhealth_config_copy)

    # Tax Configuration
    tax_config = deduction_configuration.tax_config()
    tax_config_copy = copy.deepcopy(tax_config)
    tax_keys = {
        "compensation_range": "tax_compensation_range",
        "percentage": "tax_parcentage",
        "base_tax": "tax_base_tax",
    }
    _update_config_data(tax_config_copy, payload, tax_keys)
    data.append(tax_config_copy)

    # PagIBIG Configuration
    pagibig_config = deduction_configuration.pagibig_config()
    pagibig_config_copy = copy.deepcopy(pagibig_config)
    pagibig_keys = {"amount": "pagibig_contribution_amount"}
    _update_config_data(pagibig_config_copy, payload, pagibig_keys)
    data.append(pagibig_config_copy)

    return data


def convert_decimal_list_to_string(list: list) -> str:
    return ", ".join(map(str, list))


def convert_string_to_decimal_list(str: str) -> list:
    return [Decimal(x) for x in str.split(", ")]


def get_mp2_object():
    """
    Retrieves the first Mp2 record from the database.
    This function returns the first record of the 'Mp2' model. If no records are found, it raises an
    InitializationError indicating that the 'Mp2' settings have not been initialized.
    """
    Mp2Model = apps.get_model("payroll", "Mp2")

    if not Mp2Model.objects.exists():
        raise InitializationError("Mp2 settings have not been initialized.")

    return Mp2Model.objects.first()


def get_current_month_and_year():
    now = make_aware(datetime.now())
    current_month = now.month
    current_year = now.year

    return current_month, current_year


def get_payslip_year_list() -> list:
    PayslipModel = apps.get_model("payroll", "Payslip")

    payslip_years = (
        PayslipModel.objects.values_list("year", flat=True).order_by("year").distinct()
    )

    return list(payslip_years)


def get_compensation_year_list() -> list:
    FixedCompensationModel = apps.get_model("payroll", "FixedCompensation")

    compensation_years = (
        FixedCompensationModel.objects.values_list("year", flat=True)
        .order_by("year")
        .distinct()
    )

    return list(compensation_years)


def get_existing_compensation(month: int, year: int) -> list:
    FixedCompensationModel = apps.get_model("payroll", "FixedCompensation")
    existing_compensations = FixedCompensationModel.objects.filter(
        month=month, year=year
    )

    return existing_compensations


def get_fix_compensation_and_users(compensation_id: int):
    FixedCompensationModel = apps.get_model("payroll", "FixedCompensation")
    compensation = FixedCompensationModel.objects.get(id=compensation_id)
    return compensation, compensation.users.all()


def get_user_payslips(user, month: int, year: int, finalized: bool = False):
    PayslipModel = apps.get_model("payroll", "Payslip")
    payslips = PayslipModel.objects.filter(user=user, month=month, year=year)

    if not finalized:
        return payslips

    return payslips.filter(finalized=True)


def get_users_with_payslip_data(users, month: int, year: int):

    data = []
    for user in users:
        payslip_data = get_user_payslips(user=user, month=month, year=year)
        data.append(
            {
                "user": user,
                "1st_period_payslip": payslip_data.filter(period="1ST").first(),
                "2nd_period_payslip": payslip_data.filter(period="2ND").first(),
            }
        )
    return data


def get_payslip_fixed_compensations(payslip):
    FixedCompensationModel = apps.get_model("payroll", "FixedCompensation")
    month = payslip.month
    year = payslip.year
    user = payslip.user

    compensations = FixedCompensationModel.objects.filter(
        users=user, month=month, year=year
    )

    total_amount = compensations.aggregate(total=Sum("amount"))["total"] or 0

    return compensations, total_amount


def get_payslip_variable_deductions(payslip):
    deductions = payslip.variable_deductions.all()

    total_amount = deductions.aggregate(total=Sum("amount"))["total"] or 0

    return deductions, total_amount


def get_payslip_variable_compensations(payslip):
    deductions = payslip.variable_deductions.all()

    total_amount = deductions.aggregate(total=Sum("amount"))["total"] or 0

    return deductions, total_amount


def get_salary_from_rank(rank_code):
    def _extract_details(rank_code):
        pattern = re.compile(
            r"^(?P<job_code>[A-Z]+)-(?P<rank>\d+)(?: - STEP (?P<step>\d+))?$"
        )

        match = pattern.match(rank_code)

        if match:
            job_code = match.group("job_code")
            job_rank = f"{job_code}-{match.group('rank')}"
            step_code = match.group("step")
            if step_code:
                step_code = f"STEP {step_code}"
            return job_code, job_rank, step_code

        return None, None, None

    JobModel = apps.get_model("payroll", "Job")
    job_code, job_rank, step_code = _extract_details(rank_code)
    job = JobModel.objects.get(code=job_code)

    for data in job.get_salary_data():
        if job_rank in data:
            if not step_code:
                return data[job_rank].get("basic_salary")
            else:
                for step_data in data[job_rank].get("steps"):
                    if step_code in step_data:
                        return step_data[step_code]
