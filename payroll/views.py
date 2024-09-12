from django.db.models import Q
from django.http import HttpResponse
from django.http.request import QueryDict
from django.shortcuts import render
from django_htmx.http import reswap, retarget, trigger_client_event
from render_block import render_block_to_string

from core.utils import get_users_sorted_by_department
from hris.utils import create_global_alert_instance
from payroll.actions import (
    process_adding_job,
    process_deleting_job,
    process_modifying_job,
    process_setting_deduction_config,
    process_setting_minimum_wage_amount,
    process_setting_mp2_amount,
    process_toggle_user_mp2_status,
)
from payroll.models import Job
from payroll.utils import (
    get_deduction_configuration_object,
    get_department_list,
    get_job_list,
    get_minimum_wage_object,
    get_mp2_object,
)
from payroll.validations import minimum_wage_update_validation

### Salary and Rank Management Views


def salary_and_rank_management(request, section=""):
    context = {}

    departments = get_department_list().exclude(jobs__isnull=True)
    selected_department_id = int(request.POST.get("selected_department", "0"))
    jobs = get_job_list(selected_department_id)
    context.update({"departments": departments, "jobs": jobs})

    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "salary_and_rank_management_section",
                context,
            )
            response = retarget(response, "#salary_and_rank_management_section")
            response = reswap(response, "outerHTML")
            return response

        if request.POST:
            if selected_department_id:
                context.update({"selected_department": selected_department_id})

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


def deductions_settings(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            deduction_configuration = get_deduction_configuration_object()
            context["deduction_configuration"] = deduction_configuration
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "deductions_settings_modal_container",
                context,
            )
            response = trigger_client_event(
                response, "openDeductionsSettingsModal", after="swap"
            )
            response = retarget(response, "#deductions_settings_modal_container")
            response = reswap(response, "outerHTML")
            return response

        if request.method == "POST":
            try:
                data = request.POST
                process_setting_deduction_config(data)
                response = create_global_alert_instance(
                    response,
                    "Deduction settings have been successfully saved.",
                    "SUCCESS",
                )
                response = trigger_client_event(
                    response, "closeDeductionsSettingsModal", after="swap"
                )
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while saving the deduction settings. Please try again later. Error details: {error}",
                    "DANGER",
                )
                return response


def mp2_settings(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            if "back" in request.GET:
                response = trigger_client_event(
                    response, "openDeductionsSettingsModal", after="swap"
                )
                response = trigger_client_event(
                    response, "closeMp2SettingsModal", after="swap"
                )
                response = reswap(response, "none")
            else:
                users = get_users_sorted_by_department()
                context["users"] = users
                response.content = render_block_to_string(
                    "payroll/salary_and_rank_management.html",
                    "mp2_settings_modal_container",
                    context,
                )
                response = retarget(response, "#mp2_settings_modal_container")
                response = reswap(response, "outerHTML")
                response = trigger_client_event(
                    response, "openMp2SettingsModal", after="swap"
                )
                response = trigger_client_event(
                    response, "closeDeductionsSettingsModal", after="swap"
                )
                response = reswap(response, "outerHTML")
            return response

        if request.method == "POST":
            data = request.POST
            users = get_users_sorted_by_department()
            user_search = data.get("user_search", "")
            if user_search:
                user_filter = (
                    Q(first_name__icontains=user_search)
                    | Q(last_name__icontains=user_search)
                    | Q(email__icontains=user_search)
                )
                users = users.filter(user_filter)
            context["users"] = users
            context.update({"users": users, "user_search": user_search})
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "mp2_settings_modal_container",
                context,
            )
            response = retarget(response, "#mp2_settings_modal_container")
            response = reswap(response, "outerHTML")
            return response


def mp2_amount_settings(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            if "back" in request.GET:
                response = trigger_client_event(
                    response, "closeMp2AmountSettingsModal", after="swap"
                )
                response = trigger_client_event(
                    response, "openMp2SettingsModal", after="swap"
                )
                response = reswap(response, "none")
            else:
                mp2 = get_mp2_object()
                context["mp2"] = mp2
                response = trigger_client_event(
                    response, "openMp2AmountSettingsModal", after="swap"
                )
                response = trigger_client_event(
                    response, "closeMp2SettingsModal", after="swap"
                )
                response.content = render_block_to_string(
                    "payroll/salary_and_rank_management.html",
                    "mp2_amount_settings_modal_container",
                    context,
                )
                response = retarget(response, "#mp2_amount_settings_modal_container")
                response = reswap(response, "outerHTML")

            return response

        if request.method == "POST":
            try:
                data = request.POST
                mp2 = process_setting_mp2_amount(data)
                context["mp2"] = mp2
                response.content = render_block_to_string(
                    "payroll/salary_and_rank_management.html",
                    "mp2_amount_settings_modal_container",
                    context,
                )
                response = create_global_alert_instance(
                    response, "MP2 Amount has been successfully updated.", "SUCCESS"
                )
                response = retarget(response, "#mp2_amount_settings_modal_container")
                response = reswap(response, "outerHTML")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while updating the MP2 Amount. Details: {error}",
                    "DANGER",
                )
                return response


def toggle_user_mp2_status(request):
    context = {}
    if request.htmx and request.method == "POST":
        try:
            response = HttpResponse()
            data = request.POST
            _, user, added = process_toggle_user_mp2_status(data)
            context["user"] = user
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "mp2_user_block",
                context,
            )
            response = reswap(response, "outerHTML")
            response = create_global_alert_instance(
                response,
                f"User #{user.id} has been successfully {'added to' if added else 'removed from'} MP2.",
                "SUCCESS",
            )
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while updating the user's MP2 status. Details: {error}",
                "DANGER",
            )
            return response


# App Shared View


def payroll_module_close_modals(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        event_name = data.get("event_name")
        response = HttpResponse()
        response = trigger_client_event(response, event_name, after="swap")
        return response
