from decimal import Decimal

from django.apps import apps
from django.conf import settings


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


def calculate_basic_salary_for_grade(salary_grade: int) -> float:
    """
    Calculates the basic salary for a given salary grade based on a base salary and a multiplier.
    The salary increases by applying the multiplier for each grade above the base grade.
    Raises ValueError if the provided salary grade is less than 1.
    """
    SalaryModel = apps.get_model("payroll", "BasicSalary")

    base_salary = SalaryModel.objects.first().amount
    salary_multiplier = Decimal(settings.BASIC_SALARY_MULTIPLIER)

    if salary_grade < 1:
        raise ValueError("Invalid Salary Grade")

    def _compute_salary(current_salary, remaining_grades):
        if remaining_grades == 0:
            return current_salary
        updated_salary = current_salary * salary_multiplier
        return _compute_salary(updated_salary, remaining_grades - 1)

    basic_salary = _compute_salary(base_salary, salary_grade - 2)
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
