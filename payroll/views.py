from django.http import HttpResponse
from django.http.request import QueryDict
from django.shortcuts import render
from django_htmx.http import reswap, retarget, trigger_client_event
from render_block import render_block_to_string

from hris.utils import create_global_alert_instance
from payroll.actions import (
    process_adding_job,
    process_deleting_job,
    process_modifying_job,
    process_setting_minimum_wage_amount,
)
from payroll.models import Job
from payroll.utils import (
    get_department_list,
    get_job_list,
    get_minimum_wage_object,
    minimum_wage_update_validation,
)

### Salary and Rank Management Views


def salary_and_rank_management(request):
    context = {}
    departments = get_department_list().exclude(jobs__isnull=True)

    selected_department_id = int(request.POST.get("selected_department", "0"))
    jobs = get_job_list(selected_department_id)
    context.update({"departments": departments, "jobs": jobs})

    if request.POST and request.htmx:
        if selected_department_id:
            context.update({"selected_department": selected_department_id})

        response = HttpResponse()
        response.content = render_block_to_string(
            "payroll/salary_and_rank_management.html",
            "salary_and_rank_management_section",
            context,
        )
        response = retarget(response, "#salary_and_rank_management_section")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "payroll/salary_and_rank_management.html", context)


def add_job(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            departments = get_department_list()
            context.update({"departments": departments})
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "add_job_modal_container",
                context,
            )
            response = trigger_client_event(response, "openAddJobModal", after="swap")
            response = retarget(response, "#add_job_modal_container")
            response = reswap(response, "outerHTML")
            return response

        if request.method == "POST":
            try:
                data = request.POST
                job = process_adding_job(data)
                response = trigger_client_event(response, "updateJobList", after="swap")
                response = trigger_client_event(
                    response, "closeAddJobModal", after="swap"
                )
                response = create_global_alert_instance(
                    response,
                    f"Job '{job.title}' has been successfully added to the job list.",
                    "SUCCESS",
                )
                return response

            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while adding the new job. Details: {error}",
                    "DANGER",
                )
                return response


def update_job_list(request):
    context = {}
    if request.method == "POST" and request.htmx:
        data = request.POST
        selected_department_id = int(data.get("selected_department", "0"))
        jobs = get_job_list(selected_department_id)
        context.update({"jobs": jobs})
        response = HttpResponse()
        response.content = render_block_to_string(
            "payroll/salary_and_rank_management.html",
            "job_list_table",
            context,
        )
        response = retarget(response, "#job_list_table")
        response = reswap(response, "outerHTML")
        return response


def view_job(request):
    context = {}
    if request.method == "POST" and request.htmx:
        data = request.POST
        job_id = data.get("job")
        job = Job.objects.get(id=job_id)
        job.get_salary_data()
        context.update({"job": job})
        response = HttpResponse()
        response.content = render_block_to_string(
            "payroll/salary_and_rank_management.html",
            "view_job_modal_container",
            context,
        )
        response = trigger_client_event(response, "openViewJobModal", after="swap")
        response = retarget(response, "#view_job_modal_container")
        response = reswap(response, "outerHTML")
        return response


def modify_job(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "POST":
            data = request.POST
            job_id = data.get("job")
            job = Job.objects.get(id=job_id)
            departments = get_department_list()
            context.update({"departments": departments, "job": job})
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "modify_job_modal_container",
                context,
            )
            response = trigger_client_event(
                response, "openModifyJobModal", after="swap"
            )
            response = retarget(response, "#modify_job_modal_container")
            response = reswap(response, "outerHTML")
            return response

        if request.method == "PATCH":
            try:
                data = QueryDict(request.body)
                job = process_modifying_job(data)
                response = trigger_client_event(response, "updateJobList", after="swap")
                response = create_global_alert_instance(
                    response,
                    f"Job #{job.id} has been successfully updated.",
                    type="SUCCESS",
                )
                response = reswap(response, "none")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while updating Job #{job.id}. Details: {error}",
                    type="DANGER",
                )
                return response


def delete_job(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "POST":
            data = request.POST
            context.update(
                {
                    "job_to_delete": data.get("job_to_delete", ""),
                    "show_delete_confirmation": not "cancel_delete" in data,
                }
            )
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "delete_button_container",
                context,
            )
            response = retarget(response, "#delete_button_container")
            response = reswap(response, "outerHTML")
            return response
        if request.method == "DELETE":
            try:
                data = QueryDict(request.body)
                job_id = data.get("job_to_delete", "")
                process_deleting_job(job_id)
                response = trigger_client_event(response, "updateJobList", after="swap")
                response = trigger_client_event(
                    response, "closeModifyJobModal", after="swap"
                )
                response = create_global_alert_instance(
                    response, f"Job #{job_id} has been successfully deleted.", "SUCCESS"
                )
                return response

            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while trying to delete Job #{job_id}. Details: {error}",
                    "DANGER",
                )
                return response


def minimum_wage_settings(request):
    context = {}
    if request.htmx:
        minimum_wage = get_minimum_wage_object()
        response = HttpResponse()
        if request.method == "GET":
            context.update({"minimum_wage": minimum_wage})
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "minimum_wage_modal_container",
                context,
            )
            response = trigger_client_event(
                response, "openMinimumWageModal", after="swap"
            )
            response = retarget(response, "#minimum_wage_modal_container")
            response = reswap(response, "outerHTML")
            return response

        if request.method == "POST":
            data = request.POST
            context = minimum_wage_update_validation(data, minimum_wage)
            if "success" in context:
                minimum_wage = process_setting_minimum_wage_amount(
                    data.get("minimum_wage_basic_salary")
                )
                context.update({"minimum_wage": minimum_wage})
                context["minimum_wage_update_success"] = (
                    "Minimum wage has been successfully updated."
                )
            context.update({"minimum_wage": minimum_wage})
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "minimum_wage_modal_container",
                context,
            )
            response = retarget(response, "#minimum_wage_modal_container")
            response = reswap(response, "outerHTML")
            return response


# App Shared View


def payroll_module_close_modals(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        event_name = data.get("event_name")
        response = HttpResponse()
        response = trigger_client_event(response, event_name, after="swap")
        return response
