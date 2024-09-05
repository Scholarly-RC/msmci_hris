from django.apps import apps
from django.db import transaction


@transaction.atomic
def process_adding_job(payload):
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
