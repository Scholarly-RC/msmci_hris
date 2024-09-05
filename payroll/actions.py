from datetime import datetime

from django.apps import apps
from django.db import transaction
from django.utils.timezone import make_aware

from payroll.utils import get_minimum_wage_object


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
