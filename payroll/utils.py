import copy
import json
import re
from datetime import datetime
from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.db.models import Q, Sum
from django.utils.timezone import make_aware

from hris.exceptions import InitializationError


def get_department_list():
    """
    Retrieves a list of active departments from the database, ordered by their name.
    """
    DepartmentModel = apps.get_model("core", "Department")
    return (
        DepartmentModel.objects.prefetch_related("shifts")
        .filter(is_active=True)
        .order_by("name")
    )


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
    """
    Retrieve rank choices for jobs in a specified department.
    This function collects and organizes job rank information,
    including any specific steps within those ranks,
    for all jobs associated with a given department ID.
    """
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
    """
    Retrieve updated deduction configuration data based on submitted changes.
    This function processes various deduction configurations (SSS, PhilHealth, Tax, and PagIBIG)
    by applying updates from a provided payload. It generates a list of updated configuration
    dictionaries, ensuring that each deduction category reflects the most recent values based on
    the input data.
    """

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
    """
    This function takes each number in the list,
    converts it to a string, and joins them together
    with commas, making it easy to format numeric data
    for display.
    """
    return ", ".join(map(str, list))


def convert_string_to_decimal_list(str: str) -> list:
    """
    This function splits the input string by commas,
    converts each resulting substring into a Decimal,
    and returns a list of these Decimal numbers,
    allowing for precise numerical calculations.
    """
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
    """
    Retrieves the current month and year as a tuple,
    ensuring the datetime is timezone-aware for accurate
    results in applications that handle multiple time zones.
    """
    now = make_aware(datetime.now())
    current_month = now.month
    current_year = now.year

    return current_month, current_year


def get_payslip_year_list() -> list:
    """
    Fetches a list of distinct years from the Payslip model,
    ordering them chronologically. This is useful for generating
    yearly reports or summaries related to payroll data.
    """
    PayslipModel = apps.get_model("payroll", "Payslip")

    payslip_years = (
        PayslipModel.objects.values_list("year", flat=True).order_by("year").distinct()
    )

    return list(payslip_years)


def get_users_with_payslip():
    """
    Retrieves a list of users who have payslips, excluding those
    with an HR role. The result is ordered by the user's first name
    and ensures that each user appears only once in the list.
    """
    UserModel = apps.get_model("auth", "User")
    UserDetails = apps.get_model("core", "UserDetails")
    hr_role = UserDetails.Role.HR.value

    return (
        UserModel.objects.exclude(
            Q(userdetails__role=hr_role) | Q(payslips__isnull=True)
        )
        .order_by("first_name")
        .distinct()
    )


def get_compensation_year_list() -> list:
    """
    Fetches a list of distinct years for fixed compensation records
    from the database, ordering the results by year. This provides
    a chronological overview of the years for which fixed compensation
    data exists.
    """
    FixedCompensationModel = apps.get_model("payroll", "FixedCompensation")

    compensation_years = (
        FixedCompensationModel.objects.values_list("year", flat=True)
        .order_by("year")
        .distinct()
    )

    return list(compensation_years)


def get_13th_month_pay_year_list() -> list:
    """
    Retrieves a list of distinct years for thirteenth month pay records
    from the database, ordering the results in descending order.
    This provides insight into the available years for which thirteenth
    month pay data exists.
    """
    FixedCompensationModel = apps.get_model("payroll", "ThirteenthMonthPay")

    compensation_years = (
        FixedCompensationModel.objects.values_list("year", flat=True)
        .order_by("-year")
        .distinct()
    )

    return list(compensation_years)


def get_existing_compensation(month: int, year: int) -> list:
    """
    Retrieves a list of existing fixed compensation records for a specified
    month and year from the database. This function filters the compensation
    data to return only those records that match the given month and year,
    providing relevant information for payroll processing.
    """
    FixedCompensationModel = apps.get_model("payroll", "FixedCompensation")
    existing_compensations = FixedCompensationModel.objects.filter(
        month=month, year=year
    )

    return existing_compensations


def get_fix_compensation_and_users(compensation_id: int):
    """
    Fetches a specific fixed compensation record along with its associated
    users from the database using the given compensation ID. This function
    retrieves the fixed compensation details and the list of users linked
    to that compensation, facilitating the management of payroll information.
    """
    FixedCompensationModel = apps.get_model("payroll", "FixedCompensation")
    compensation = FixedCompensationModel.objects.get(id=compensation_id)
    return compensation, compensation.users.all()


def get_user_payslips(user, month: int, year: int, released: bool = False):
    """
    Retrieves the payslips for a specified user for a given month and year.
    This function allows the option to filter the results based on the
    released status of the payslips. If 'released' is set to False,
    all payslips are returned; otherwise, only the released payslips
    are returned.
    """
    PayslipModel = apps.get_model("payroll", "Payslip")
    payslips = PayslipModel.objects.filter(user=user, month=month, year=year)

    if not released:
        return payslips

    return payslips.filter(released=True)


def get_users_with_payslip_data(users, month: int, year: int):
    """
    Retrieves payslip data for a list of users for a specific month and year.
    For each user, it gets their payslip for the first and second periods if available.
    """

    PayslipModel = apps.get_model("payroll", "Payslip")
    payslips = PayslipModel.objects.filter(month=month, year=year)

    payslips_by_user = {}

    for payslip in payslips:
        user_id = payslip.user.id
        if user_id not in payslips_by_user:
            payslips_by_user[user_id] = {
                "1st_period_payslip": None,
                "2nd_period_payslip": None,
            }

        if payslip.period == "1ST":
            payslips_by_user[user_id]["1st_period_payslip"] = payslip
        elif payslip.period == "2ND":
            payslips_by_user[user_id]["2nd_period_payslip"] = payslip

    data = [
        {
            "user": user,
            "1st_period_payslip": (
                payslips_by_user[user.id]["1st_period_payslip"]
                if user.id in payslips_by_user
                else None
            ),
            "2nd_period_payslip": (
                payslips_by_user[user.id]["2nd_period_payslip"]
                if user.id in payslips_by_user
                else None
            ),
        }
        for user in users
    ]

    return data


def get_payslip_fixed_compensations(payslip, semi_monthly=False):
    """
    Retrieves fixed compensation records associated with a specific
    payslip for a user in a given month and year. It calculates the
    total amount of these compensations, and if specified, divides
    the total by two for semi-monthly compensation structures. The
    function returns both the list of compensations and the total
    amount calculated.
    """
    FixedCompensationModel = apps.get_model("payroll", "FixedCompensation")
    month = payslip.month
    year = payslip.year
    user = payslip.user

    compensations = FixedCompensationModel.objects.filter(
        users=user, month=month, year=year
    )

    total_amount = compensations.aggregate(total=Sum("amount"))["total"] or 0

    if semi_monthly and total_amount:
        total_amount = total_amount / 2

    return compensations, total_amount


def get_payslip_variable_deductions(payslip):
    """
    Fetches all variable deductions associated with a given payslip
    and calculates the total amount of these deductions. The function
    returns both the list of variable deductions and the total amount
    calculated.
    """
    deductions = payslip.variable_deductions.all()

    total_amount = deductions.aggregate(total=Sum("amount"))["total"] or 0

    return deductions, total_amount


def get_variable_deduction_choices():
    with open("payroll/data/variable_deductions.json", "r") as file:
        data = json.load(file)
        return data


def get_payslip_variable_compensations(payslip):
    """
    Retrieves all variable compensations linked to a specific payslip
    and computes the total amount of these compensations. The function
    returns both the list of variable compensations and the total amount
    calculated.
    """
    compensation = payslip.variable_compensation.all()

    total_amount = compensation.aggregate(total=Sum("amount"))["total"] or 0

    return compensation, total_amount


def get_salary_from_rank(rank_code):
    """
    Retrieves the salary associated with a given rank code, which
    includes the job code, rank, and optional step. The function first
    extracts the relevant details from the rank code using a regex pattern,
    then fetches the job object from the database. It iterates through the
    job's salary data to return the basic salary for the specified rank
    and step, if applicable.
    """

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


def get_user_13th_month_pay_list(user_id, year="", released=""):
    """
    Retrieves a user's list of thirteenth month pay records for a specified year.
    The function fetches the user by their ID and orders their thirteenth month
    pay entries by year and month in descending order. If a specific year is provided,
    it filters the results accordingly. Additionally, if the 'released' parameter
    is set to true, it further filters the list to include only released entries.
    """
    UserModel = apps.get_model("auth", "User")
    user = UserModel.objects.get(id=user_id)
    thirteenth_month_pay_list = user.thirteenth_month_pays.order_by("-year", "-month")
    if year and year != "0":
        thirteenth_month_pay_list = thirteenth_month_pay_list.filter(year=year)
    if released:
        thirteenth_month_pay_list = thirteenth_month_pay_list.filter(released=True)
    return user, thirteenth_month_pay_list
