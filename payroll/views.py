from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.http.request import QueryDict
from django.shortcuts import render
from django.urls import reverse
from django.utils.timezone import make_aware
from django_htmx.http import push_url, reswap, retarget, trigger_client_event
from render_block import render_block_to_string

from attendance.enums import Months
from attendance.utils.date_utils import get_list_of_months
from core.actions import process_add_app_log_entry
from core.decorators import hr_required
from core.notification import create_notification
from core.utils import get_users_sorted_by_department
from hris.utils import create_global_alert_instance
from payroll.actions import (
    process_add_or_create_fixed_compensation,
    process_add_thirteenth_month_pay_variable_deduction,
    process_adding_job,
    process_adding_variable_payslip_compensation,
    process_adding_variable_payslip_deduction,
    process_creating_thirteenth_month_pay,
    process_delete_thirteenth_month_pay,
    process_deleting_job,
    process_get_or_create_user_payslip,
    process_modifying_fixed_compensation,
    process_modifying_fixed_compensation_users,
    process_modifying_job,
    process_remove_thirteenth_month_pay_variable_deduction,
    process_removing_fixed_compensation,
    process_removing_variable_payslip_compensation,
    process_removing_variable_payslip_deduction,
    process_setting_deduction_config,
    process_setting_minimum_wage_amount,
    process_setting_mp2_amount,
    process_toggle_payslip_release_status,
    process_toggle_user_mp2_status,
    process_toggling_thirteenth_month_pay_release,
    process_updating_thirteenth_month_pay,
)
from payroll.models import Job, Payslip, ThirteenthMonthPay
from payroll.utils import (
    get_13th_month_pay_year_list,
    get_compensation_year_list,
    get_current_month_and_year,
    get_deduction_configuration_object,
    get_department_list,
    get_existing_compensation,
    get_fix_compensation_and_users,
    get_job_list,
    get_minimum_wage_object,
    get_mp2_object,
    get_payslip_year_list,
    get_user_13th_month_pay_list,
    get_user_payslips,
    get_users_with_payslip_data,
    get_variable_deduction_choices,
)
from payroll.validations import (
    creating_thirteenth_month_pay_validation,
    minimum_wage_update_validation,
    payslip_data_validation,
    thirteenth_month_pay_variable_deduction_validation,
    variable_payslip_compensation_validation,
    variable_payslip_deduction_validation,
)
from performance.utils import get_user_with_hr_role


### Salary and Rank Management Views
@login_required(login_url="/login")
@hr_required("/")
def salary_and_rank_management(request):
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


@login_required(login_url="/login")
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
                process_add_app_log_entry(
                    request.user.id, f"Added a job ({job.title})."
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
                response = reswap(response, "none")
                return response


@login_required(login_url="/login")
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


@login_required(login_url="/login")
def view_job(request):
    context = {}
    if request.method == "POST" and request.htmx:
        data = request.POST
        job_id = data.get("job")
        job = Job.objects.get(id=job_id)
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


@login_required(login_url="/login")
def modify_job(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "POST":
            data = request.POST
            job_id = data.get("job")
            job = Job.objects.prefetch_related("department").get(id=job_id)
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
                process_add_app_log_entry(
                    request.user.id,
                    f"Updated a job position. Details: {{'title': {job.title}, 'code': {job.code}, 'salary_grade: {job.salary_grade}, departments: {job.department.all()}}}",
                )
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
                    "DANGER",
                )
                response = reswap(response, "none")
                return response


@login_required(login_url="/login")
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
                job_details = process_deleting_job(job_id)
                response = trigger_client_event(response, "updateJobList", after="swap")
                response = trigger_client_event(
                    response, "closeModifyJobModal", after="swap"
                )
                process_add_app_log_entry(
                    request.user.id, f"Deleted a job ({job_details})."
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
                response = reswap(response, "none")
                return response


@login_required(login_url="/login")
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
                process_add_app_log_entry(
                    request.user.id,
                    f"Updated minimum wage. Details: {minimum_wage.amount}.",
                )
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


@login_required(login_url="/login")
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
                deduction_config = process_setting_deduction_config(data)
                process_add_app_log_entry(
                    request.user.id,
                    f"Updated the mandatory deduction config. Details: ({deduction_config.config}).",
                )
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
                response = reswap(response, "none")
                return response


@login_required(login_url="/login")
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


@login_required(login_url="/login")
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
                response = reswap(response, "none")
                return response


@login_required(login_url="/login")
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
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def fixed_compensations_settings(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        try:
            current_month, current_year = get_current_month_and_year()
            selected_month = request.POST.get("selected_month") or current_month
            selected_year = request.POST.get("selected_year") or current_year
            months = get_list_of_months()
            years = get_compensation_year_list()
            existent_compensation_types = get_existing_compensation(
                selected_month, selected_year
            )
            context.update(
                {
                    "months": months,
                    "years": years if years else [current_year],
                    "selected_month": int(selected_month),
                    "selected_year": int(selected_year),
                    "existent_compensation_types": existent_compensation_types,
                }
            )
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "fixed_compensations_settings_modal_container",
                context,
            )
            response = retarget(
                response, "#fixed_compensations_settings_modal_container"
            )
            response = reswap(response, "outerHTML")
            if request.method == "GET":
                response = trigger_client_event(
                    response, "openFixedCompensationsSettingsModal", after="swap"
                )
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while accessing fixed compensation settings. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def modify_fixed_compensation(request):
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response = reswap(response, "none")
        try:
            data = request.POST
            if not data.get("amount", ""):
                response = create_global_alert_instance(
                    response, "Please enter a valid amount.", "WARNING"
                )
                return response
            fixed_compensation = process_modifying_fixed_compensation(data)
            process_add_app_log_entry(
                request.user.id,
                f"Modified fixed compensation. Details: {{'Amount': {fixed_compensation.amount}}}.",
            )
            response = create_global_alert_instance(
                response,
                "Fixed compensation details have been successfully updated.",
                "SUCCESS",
            )
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while updating the fixed compensation details. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def add_fixed_compensation(request):
    context = {}
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        try:
            data = request.POST
            current_month, current_year = get_current_month_and_year()
            selected_month = request.POST.get("selected_month") or current_month
            selected_year = request.POST.get("selected_year") or current_year
            months = get_list_of_months()
            years = get_compensation_year_list()
            fixed_compensation = data.get("fixed_compensation")
            if not fixed_compensation or fixed_compensation.strip() == "":
                response = create_global_alert_instance(
                    response,
                    "The fixed compensation name is required.",
                    "WARNING",
                )
                response = reswap(response, "none")
                return response
            compensation, compensation_created = (
                process_add_or_create_fixed_compensation(
                    fixed_compensation, int(selected_month), int(selected_year)
                )
            )
            month_name = Months(compensation.month).name

            if not compensation_created:
                response = create_global_alert_instance(
                    response,
                    f"{compensation.name} fixed compensation already exists for {month_name} {compensation.year}.",
                    "INFO",
                )
                response = reswap(response, "none")
                return response

            existent_compensation_types = get_existing_compensation(
                selected_month, selected_year
            )
            context.update(
                {
                    "months": months,
                    "years": years if years else [current_year],
                    "selected_month": int(selected_month),
                    "selected_year": int(selected_year),
                    "existent_compensation_types": existent_compensation_types,
                }
            )
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "fixed_compensations_settings_modal_container",
                context,
            )
            process_add_app_log_entry(
                request.user.id,
                f"Added fixed compensation ({compensation}).",
            )
            response = create_global_alert_instance(
                response,
                f"{compensation.name} fixed compensation has been successfully added for {month_name} {compensation.year}.",
                "SUCCESS",
            )
            response = retarget(
                response, "#fixed_compensations_settings_modal_container"
            )
            response = reswap(response, "outerHTML")
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while adding the fixed compensation. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def remove_fixed_compensation(request):
    context = {}
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        try:
            current_month, current_year = get_current_month_and_year()
            selected_month = request.POST.get("selected_month") or current_month
            selected_year = request.POST.get("selected_year") or current_year
            months = get_list_of_months()
            years = get_compensation_year_list()
            data = request.POST
            fixed_compensation_details = process_removing_fixed_compensation(data)
            existent_compensation_types = get_existing_compensation(
                selected_month, selected_year
            )
            context.update(
                {
                    "months": months,
                    "years": years if years else [current_year],
                    "selected_month": int(selected_month),
                    "selected_year": int(selected_year),
                    "existent_compensation_types": existent_compensation_types,
                }
            )
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "fixed_compensations_settings_modal_container",
                context,
            )
            process_add_app_log_entry(
                request.user.id,
                f"Removed fixed compensation ({fixed_compensation_details}).",
            )
            response = create_global_alert_instance(
                response, "Fixed compensation successfully removed.", "SUCCESS"
            )
            response = retarget(
                response, "#fixed_compensations_settings_modal_container"
            )
            response = reswap(response, "outerHTML")
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while removing the fixed compensation. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def toggle_fixed_compensation_users_view(request):
    context = {}
    if request.htmx and request.method == "POST":
        data = request.POST
        response = HttpResponse()
        selected_compensation_id = data.get("selected_compensation")
        fixed_compensation, fixed_compensation_users = get_fix_compensation_and_users(
            int(selected_compensation_id)
        )
        context["compensation"] = fixed_compensation
        if "hide" not in data:
            users = get_users_sorted_by_department()
            context["users"] = users
        response.content = render_block_to_string(
            "payroll/salary_and_rank_management.html",
            "specific_fixed_compensation_section",
            context,
        )
        response = retarget(response, "closest form")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def modify_fixed_compensation_users(request):
    context = {}
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        try:
            data = request.POST
            selected_compensation_id = data.get("selected_compensation")
            if "for_search" in data:
                compensation, compensation_users = get_fix_compensation_and_users(
                    int(selected_compensation_id)
                )
                context["compensation"] = compensation
                user_search = data.get("user_search", "")
                users = get_users_sorted_by_department(user_search)
                context.update(
                    {
                        "users": users,
                        "compensation_users": compensation_users,
                        "user_search": user_search,
                    }
                )
                response.content = render_block_to_string(
                    "payroll/salary_and_rank_management.html",
                    "user_list_section",
                    context,
                )
                response = retarget(response, ".user-list-section")
                response = reswap(response, "outerHTML")
                return response

            to_remove = "user_to_remove" in data
            selected_user_id = data.get("user_to_add") or data.get("user_to_remove")
            compensation, user = process_modifying_fixed_compensation_users(
                int(selected_user_id), int(selected_compensation_id), to_remove
            )
            context.update({"user": user, "compensation": compensation})
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "specific_user_section",
                context,
            )
            process_add_app_log_entry(
                request.user.id,
                f"{'Removed' if to_remove else 'Added'} {user.userdetails.get_user_fullname()} to fixed compensation {compensation}.",
            )
            response = create_global_alert_instance(
                response,
                f"User has been successfully {'removed' if to_remove else 'added'}.",
                "SUCCESS",
            )
            response = retarget(response, "closest li")
            response = reswap(response, "outerHTML")
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while modifying the compensation users. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
@hr_required("/")
def payslip_management(request):
    context = {}
    current_month, current_year = get_current_month_and_year()
    selected_month = request.POST.get("selected_month") or current_month
    selected_year = request.POST.get("selected_year") or current_year
    selected_department = request.POST.get("selected_department", 0)
    months = get_list_of_months()
    years = get_payslip_year_list()
    departments = get_department_list()
    user_search = request.POST.get("user_search", "")
    users = get_users_sorted_by_department(user_search, int(selected_department))
    users_with_payslip_data = get_users_with_payslip_data(
        users, current_month, current_year
    )
    context.update(
        {
            "months": months,
            "years": years if years else [current_year],
            "departments": departments,
            "selected_month": int(selected_month),
            "selected_year": int(selected_year),
            "selected_department": int(selected_department),
            "user_search": user_search,
            "users_with_payslip_data": users_with_payslip_data,
        }
    )
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "payroll/payslip_management.html",
            "payslip_management_section",
            context,
        )
        response = retarget(response, "#payslip_management_section")
        response = reswap(response, "outerHTML")
        return response
    return render(request, "payroll/payslip_management.html", context)


@login_required(login_url="/login")
def access_payslip(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            data = request.GET
            errors = payslip_data_validation(data)
            if errors:
                for error in errors:
                    response = create_global_alert_instance(
                        response, errors[error], "WARNING"
                    )
                    response = reswap(response, "none")
                    return response

            selected_month = data.get("selected_month")
            selected_year = data.get("selected_year")
            selected_user_id = data.get("selected_user")
            selected_period = data.get("period")

            user, payslip = process_get_or_create_user_payslip(
                int(selected_user_id),
                int(selected_month),
                int(selected_year),
                selected_period,
            )

            payslip_data = payslip.get_data()

            context.update(
                {
                    "selected_user": user,
                    "payslip": payslip,
                    "payslip_data": payslip_data,
                }
            )

            response.content = render_block_to_string(
                "payroll/payslip_management.html",
                "access_payslip_modal_container",
                context,
            )
            response = trigger_client_event(
                response, "openAccessPayslipModal", after="swap"
            )
            response = retarget(response, "#access_payslip_modal_container")
            response = reswap(response, "outerHTML")
            return response


@login_required(login_url="/login")
def add_variable_payslip_deduction(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        try:
            if request.method == "GET":
                data = request.GET
                if "back" in data:
                    response = trigger_client_event(
                        response, "closeAddVariablePayslipDeductionModal", after="swap"
                    )
                    response = trigger_client_event(
                        response, "openAccessPayslipModal", after="swap"
                    )
                    response = reswap(response, "none")
                    return response
                choices = get_variable_deduction_choices()
                context.update({"payslip": data.get("payslip"), "choices": choices})
                response.content = render_block_to_string(
                    "payroll/payslip_management.html",
                    "add_variable_payslip_deduction_modal_container",
                    context,
                )
                response = trigger_client_event(
                    response, "openAddVariablePayslipDeductionModal", after="swap"
                )
                response = trigger_client_event(
                    response, "closeAccessPayslipModal", after="swap"
                )
                response = retarget(
                    response, "#add_variable_payslip_deduction_modal_container"
                )
                response = reswap(response, "outerHTML")
                return response

            if request.method == "POST":
                data = request.POST
                errors = variable_payslip_deduction_validation(data)
                if errors:
                    for error in errors:
                        response = create_global_alert_instance(
                            response, errors[error], "WARNING"
                        )
                        response = reswap(response, "none")
                        return response

                process_adding_variable_payslip_deduction(data)
                response = create_global_alert_instance(
                    response,
                    "A new variable deduction has been successfully added.",
                    "SUCCESS",
                )
                response = trigger_client_event(
                    response, "openAccessPayslipModal", after="swap"
                )
                response = trigger_client_event(
                    response, "closeAddVariablePayslipDeductionModal", after="swap"
                )
                response = trigger_client_event(
                    response, "updatePayslipData", after="swap"
                )
                return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error has occured while adding a variable deduction. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def remove_variable_payslip_deduction(request):
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        try:
            data = request.POST
            process_removing_variable_payslip_deduction(data)
            response = create_global_alert_instance(
                response, "Selected variable deduction successfully removed.", "SUCCESS"
            )
            response = trigger_client_event(response, "updatePayslipData", after="swap")
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error has occured while removing the selected variable deduction. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def add_variable_payslip_compensation(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        try:
            if request.method == "GET":
                data = request.GET
                if "back" in data:
                    response = trigger_client_event(
                        response,
                        "closeAddVariablePayslipCompensationModal",
                        after="swap",
                    )
                    response = trigger_client_event(
                        response, "openAccessPayslipModal", after="swap"
                    )
                    response = reswap(response, "none")
                    return response

                context.update({"payslip": data.get("payslip")})
                response.content = render_block_to_string(
                    "payroll/payslip_management.html",
                    "add_variable_payslip_compensation_modal_container",
                    context,
                )
                response = trigger_client_event(
                    response, "openAddVariablePayslipCompensationModal", after="swap"
                )
                response = trigger_client_event(
                    response, "closeAccessPayslipModal", after="swap"
                )
                response = retarget(
                    response, "#add_variable_payslip_compensation_modal_container"
                )
                response = reswap(response, "outerHTML")
                return response

            if request.method == "POST":
                data = request.POST
                errors = variable_payslip_compensation_validation(data)
                if errors:
                    for error in errors:
                        response = create_global_alert_instance(
                            response, errors[error], "WARNING"
                        )
                        response = reswap(response, "none")
                        return response

                process_adding_variable_payslip_compensation(data)
                response = create_global_alert_instance(
                    response,
                    "A new variable compensation has been successfully added.",
                    "SUCCESS",
                )
                response = trigger_client_event(
                    response, "openAccessPayslipModal", after="swap"
                )
                response = trigger_client_event(
                    response, "closeAddVariablePayslipCompensationModal", after="swap"
                )
                response = trigger_client_event(
                    response, "updatePayslipData", after="swap"
                )
                return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error has occured while adding a variable compensation. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def remove_variable_payslip_compensation(request):
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        try:
            data = request.POST
            process_removing_variable_payslip_compensation(data)
            response = create_global_alert_instance(
                response,
                "Selected variable compensation successfully removed.",
                "SUCCESS",
            )
            response = trigger_client_event(response, "updatePayslipData", after="swap")
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error has occured while removing the selected variable compensation. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def toggle_payslip_release_status(request):
    context = {}
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        user = request.user
        try:
            data = request.POST
            payslip = process_toggle_payslip_release_status(data)
            if payslip.released:
                create_notification(
                    content=f"Your payslip for <b>{payslip.get_month_year_and_period_display()}</b> is now available.",
                    date=make_aware(datetime.now()),
                    sender_id=user.id,
                    recipient_id=payslip.user.id,
                    url=reverse("payroll:payroll_management"),
                )

            context["payslip"] = payslip
            response.content = render_block_to_string(
                "payroll/payslip_management.html",
                "modify_payslip_section",
                context,
            )
            process_add_app_log_entry(
                request.user.id,
                (
                    f"Marked payslip ({payslip}) as RELEASED. Data: {payslip.get_data()}."
                    if payslip.released
                    else f"Marked payslip ({payslip}) as DRAFT."
                ),
            )
            response = create_global_alert_instance(
                response,
                f"The status of the selected payslip has been successfully set to {'RELEASED' if payslip.released else 'DRAFT'}.",
                "SUCCESS",
            )
            response = retarget(response, "#modify_payslip_section")
            response = reswap(response, "outerHTML")
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while updating the payslip status. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def update_payslip_data(request):
    context = {}
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        data = request.POST
        payslip = Payslip.objects.get(id=data.get("selected_payslip"))
        payslip_data = payslip.get_data()
        context.update(
            {
                "selected_user": payslip.user,
                "payslip": payslip,
                "payslip_data": payslip_data,
            }
        )
        response.content = render_block_to_string(
            "payroll/payslip_management.html",
            "access_payslip_modal_container",
            context,
        )
        response = retarget(response, "#access_payslip_modal_container")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def thirteenth_month_pay(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        user_search = request.POST.get("user_search", "")
        users = get_users_sorted_by_department(user_search)
        context["users"] = users
        if request.method == "GET":
            response.content = render_block_to_string(
                "payroll/payslip_management.html",
                "thirteenth_month_pay_container",
                context,
            )
            response = trigger_client_event(
                response, "openThirteenthMonthPayModal", after="swap"
            )
            response = retarget(response, "#thirteenth_month_pay_container")
            response = reswap(response, "outerHTML")
            return response

        if request.method == "POST":
            response.content = render_block_to_string(
                "payroll/payslip_management.html",
                "user_list_table_container",
                context,
            )
            response = trigger_client_event(
                response, "openThirteenthMonthPayModal", after="swap"
            )
            response = retarget(response, "#user_list_table_container")
            response = reswap(response, "outerHTML")
            return response


@login_required(login_url="/login")
def user_thirteenth_month_pay(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if "back" in request.GET:
            response = trigger_client_event(
                response, "openThirteenthMonthPayModal", after="swap"
            )
            response = trigger_client_event(
                response, "closeUserThirteenthMonthPayModal", after="swap"
            )
            response = reswap(response, "none")
            return response

        current_month, current_year = get_current_month_and_year()
        selected_month = current_month
        selected_year = request.POST.get("selected_year")
        months = get_list_of_months()
        years = get_13th_month_pay_year_list()
        user_id = request.POST.get("user") or request.GET.get("user")
        user, thirteenth_month_pay_list = get_user_13th_month_pay_list(
            user_id, selected_year
        )
        context.update(
            {
                "user": user,
                "thirteenth_month_pay_list": thirteenth_month_pay_list,
                "months": months,
                "years": years,
                "current_year": current_year,
                "selected_month": selected_month,
                "selected_year": selected_year,
            }
        )
        if request.method == "GET":
            response.content = render_block_to_string(
                "payroll/payslip_management.html",
                "user_thirteenth_month_pay_container",
                context,
            )
            response = trigger_client_event(
                response, "openUserThirteenthMonthPayModal", after="swap"
            )
            response = trigger_client_event(
                response, "closeThirteenthMonthPayModal", after="swap"
            )
            response = retarget(response, "#user_thirteenth_month_pay_container")
            response = reswap(response, "outerHTML")
            return response

        if request.method == "POST":
            data = request.POST
            if "filter_list_by_year" in data:
                response.content = render_block_to_string(
                    "payroll/payslip_management.html",
                    "user_thirteenth_month_pay_list",
                    context,
                )
                response = retarget(response, "#user_thirteenth_month_pay_list")
                response = reswap(response, "outerHTML")
                return response


@login_required(login_url="/login")
def create_thirteenth_month_pay(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "POST":
            try:
                data = request.POST
                errors = creating_thirteenth_month_pay_validation(data)
                if errors:
                    for error in errors:
                        response = create_global_alert_instance(
                            response, errors[error], "WARNING"
                        )
                        response = reswap(response, "none")
                        return response

                current_month, current_year = get_current_month_and_year()
                selected_month = current_month
                months = get_list_of_months()
                thirteenth_month_pay = process_creating_thirteenth_month_pay(data)
                years = get_13th_month_pay_year_list()
                user, thirteenth_month_pay_list = get_user_13th_month_pay_list(
                    request.POST.get("user")
                )
                context.update(
                    {
                        "user": user,
                        "thirteenth_month_pay_list": thirteenth_month_pay_list,
                        "months": months,
                        "years": years,
                        "current_year": current_year,
                        "selected_month": selected_month,
                    }
                )

                response.content = render_block_to_string(
                    "payroll/payslip_management.html",
                    "user_thirteenth_month_pay_container",
                    context,
                )
                process_add_app_log_entry(
                    request.user.id,
                    f"Added a thirteenth month pay for user ({thirteenth_month_pay.get_app_log_details()} - Amount: {thirteenth_month_pay.amount}).",
                )
                response = create_global_alert_instance(
                    response,
                    f"Thirteenth Month Pay for {thirteenth_month_pay.user.userdetails.get_user_fullname()} has been successfully added.",
                    "SUCCESS",
                )
                response = retarget(response, "#user_thirteenth_month_pay_container")
                response = reswap(response, "outerHTML")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while processing the Thirteenth Month Pay for the selected user. Please try again or contact support if the issue persists. Error details: {error}.",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response


@login_required(login_url="/login")
def update_user_thirteenth_month_pay_list(request):
    context = {}
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        data = request.POST
        selected_thirteenth_month_pay_user_id = data.get(
            "selected_thirteenth_month_pay_user"
        )
        user, thirteenth_month_pay_list = get_user_13th_month_pay_list(
            selected_thirteenth_month_pay_user_id
        )
        context["thirteenth_month_pay_list"] = thirteenth_month_pay_list
        response.content = render_block_to_string(
            "payroll/payslip_management.html",
            "user_thirteenth_month_pay_list",
            context,
        )
        response = retarget(response, "#user_thirteenth_month_pay_list")
        response = reswap(response, "outerHTML")
        return response


@login_required(login_url="/login")
def view_specific_thirteenth_month_pay(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            data = request.GET
            if "back" in data:
                response = trigger_client_event(
                    response, "openUserThirteenthMonthPayModal", after="swap"
                )
                response = trigger_client_event(
                    response, "closeSpecificThirteenthMonthPayModal", after="swap"
                )
                response = reswap(response, "none")
                return response

            thirteenth_month_pay_id = data.get("thirteenth_month_pay")
            thirteenth_month_pay = ThirteenthMonthPay.objects.get(
                id=thirteenth_month_pay_id
            )

            thirteenth_month_pay_deductions = (
                thirteenth_month_pay.variable_deductions.all()
            )
            context.update(
                {
                    "thirteenth_month_pay": thirteenth_month_pay,
                    "thirteenth_month_pay_deductions": thirteenth_month_pay_deductions,
                }
            )
            response.content = render_block_to_string(
                "payroll/payslip_management.html",
                "specific_thirteenth_month_pay_container",
                context,
            )
            response = trigger_client_event(
                response, "openSpecificThirteenthMonthPayModal", after="swap"
            )
            response = trigger_client_event(
                response, "closeUserThirteenthMonthPayModal", after="swap"
            )
            response = retarget(response, "#specific_thirteenth_month_pay_container")
            response = reswap(response, "outerHTML")
            return response


@login_required(login_url="/login")
def update_specific_thirteenth_month_pay(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "POST":
            try:
                data = request.POST
                thirteenth_month_pay = process_updating_thirteenth_month_pay(data)
                process_add_app_log_entry(
                    request.user.id,
                    f"Updated selected thirteenth month pay record ({thirteenth_month_pay.get_app_log_details()} - Amount: {thirteenth_month_pay.amount}).",
                )
                response = create_global_alert_instance(
                    response,
                    f"The Thirteenth Month Pay for user {thirteenth_month_pay.user} has been successfully updated.",
                    "SUCCESS",
                )
                response = reswap(response, "none")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while updating the Thirteenth Month Pay amount. Details: {error}.",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response


@login_required(login_url="/login")
def toggle_specific_thirteenth_month_pay_release(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        user = request.user
        if request.method == "POST":
            try:
                data = request.POST
                thirteenth_month_pay = process_toggling_thirteenth_month_pay_release(
                    data
                )
                if thirteenth_month_pay.released:
                    create_notification(
                        content=f"Your 13th Month Pay payslip for <b>{thirteenth_month_pay.get_month_year_display()}</b> is now available.",
                        date=make_aware(datetime.now()),
                        sender_id=user.id,
                        recipient_id=thirteenth_month_pay.user.id,
                        url=reverse("payroll:payroll_management"),
                    )
                thirteenth_month_pay_deductions = (
                    thirteenth_month_pay.variable_deductions.all()
                )
                context.update(
                    {
                        "thirteenth_month_pay": thirteenth_month_pay,
                        "thirteenth_month_pay_deductions": thirteenth_month_pay_deductions,
                    }
                )
                response.content = render_block_to_string(
                    "payroll/payslip_management.html",
                    "specific_thirteenth_month_pay_container",
                    context,
                )
                process_add_app_log_entry(
                    request.user.id,
                    f"Set thirteenth month pay ({thirteenth_month_pay.get_app_log_details()}) to {'RELEASED' if thirteenth_month_pay.released else 'DRAFT'}.",
                )
                response = create_global_alert_instance(
                    response,
                    f"The Thirteenth Month Pay status has been successfully updated to {'RELEASED' if thirteenth_month_pay.released else 'DRAFT'}.",
                    "SUCCESS",
                )
                response = retarget(
                    response, "#specific_thirteenth_month_pay_container"
                )
                response = reswap(response, "outerHTML")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while updating the Thirteenth Month Pay status. Details: {error}.",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response


@login_required(login_url="/login")
def delete_specific_thirteenth_month_pay_release(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "DELETE":
            try:
                data = QueryDict(request.body)
                thirteenth_month_pay_details = process_delete_thirteenth_month_pay(data)
                process_add_app_log_entry(
                    request.user.id,
                    f"Deleted a thirteen month pay record ({thirteenth_month_pay_details}).",
                )
                response = create_global_alert_instance(
                    response,
                    f"The selected Thirteenth Month Pay record has been successfully deleted.",
                    "SUCCESS",
                )
                response = trigger_client_event(
                    response, "openUserThirteenthMonthPayModal", after="swap"
                )
                response = trigger_client_event(
                    response, "closeSpecificThirteenthMonthPayModal", after="swap"
                )
                response = trigger_client_event(
                    response, "updateUserThirteenthMonthPayList", after="swap"
                )
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while deleting the selected Thirteenth Month Pay record. Details: {error}.",
                    "DANGER",
                )
                response = reswap(response, "none")
                return response

        if request.method == "POST":
            data = request.POST
            if "cancel" not in data:
                context["confirm_delete"] = True
            thirteenth_month_pay = data.get("thirteenth_month_pay")
            context["thirteenth_month_pay"] = thirteenth_month_pay
            response.content = render_block_to_string(
                "payroll/payslip_management.html",
                "specific_thirteenth_month_pay_delete_button_section",
                context,
            )
            response = retarget(
                response, "#specific_thirteenth_month_pay_delete_button_section"
            )
            response = reswap(response, "outerHTML")
            return response


@login_required(login_url="/login")
def add_thirteenth_month_pay_variable_deduction(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            data = request.GET
            if "back" in data:
                response = trigger_client_event(
                    response, "openSpecificThirteenthMonthPayModal", after="swap"
                )
                response = trigger_client_event(
                    response,
                    "closeThirteenthMonthPayVariableDeductionModal",
                    after="swap",
                )
                response = reswap(response, "none")
            else:
                thirteenth_month_pay_id = data.get("thirteenth_month_pay")
                context["thirteenth_month_pay"] = thirteenth_month_pay_id
                response.content = render_block_to_string(
                    "payroll/payslip_management.html",
                    "add_thirteenth_month_pay_variable_deduction_container",
                    context,
                )
                response = trigger_client_event(
                    response,
                    "openThirteenthMonthPayVariableDeductionModal",
                    after="swap",
                )
                response = trigger_client_event(
                    response, "closeSpecificThirteenthMonthPayModal", after="swap"
                )
                response = retarget(
                    response, "#add_thirteenth_month_pay_variable_deduction_container"
                )
                response = reswap(response, "outerHTML")
            return response

        if request.method == "POST":
            try:
                data = request.POST
                errors = thirteenth_month_pay_variable_deduction_validation(data)
                if errors:
                    for error in errors:
                        response = create_global_alert_instance(
                            response, errors[error], "WARNING"
                        )
                        response = reswap(response, "none")
                        return response

                thirteenth_month_pay = (
                    process_add_thirteenth_month_pay_variable_deduction(data)
                )
                thirteenth_month_pay_deductions = (
                    thirteenth_month_pay.variable_deductions.all()
                )
                process_add_app_log_entry(
                    request.user.id,
                    f"Added a variable deductions to thirteenth month pay ({thirteenth_month_pay.get_app_log_details()}). Deductions: {thirteenth_month_pay.get_variable_deductions_list()}.",
                )
                context.update(
                    {
                        "thirteenth_month_pay": thirteenth_month_pay,
                        "thirteenth_month_pay_deductions": thirteenth_month_pay_deductions,
                    }
                )
                response.content = render_block_to_string(
                    "payroll/payslip_management.html",
                    "specific_thirteenth_month_pay_container",
                    context,
                )
                response = create_global_alert_instance(
                    response,
                    "Deduction for the selected 13th Month Pay has been successfully added.",
                    "SUCCESS",
                )

                response = trigger_client_event(
                    response, "openSpecificThirteenthMonthPayModal", after="swap"
                )
                response = trigger_client_event(
                    response,
                    "closeThirteenthMonthPayVariableDeductionModal",
                    after="swap",
                )
                response = retarget(
                    response, "#specific_thirteenth_month_pay_container"
                )
                response = reswap(response, "outerHTML")
                return response
            except Exception as error:
                response = create_global_alert_instance(
                    response,
                    f"An error occurred while adding a variable deduction to the selected Thirteenth Month Pay. Details: {error}.",
                    "DANGER",
                )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def remove_thirteenth_month_pay_variable_deduction(request):
    context = {}
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        try:
            data = request.POST
            thirteenth_month_pay = (
                process_remove_thirteenth_month_pay_variable_deduction(data)
            )
            thirteenth_month_pay_deductions = (
                thirteenth_month_pay.variable_deductions.all()
            )
            process_add_app_log_entry(
                request.user.id,
                f"Updated variable deductions of thirteenth month pay ({thirteenth_month_pay.get_app_log_details()}). Deductions: {thirteenth_month_pay.get_variable_deductions_list()}.",
            )
            context.update(
                {
                    "thirteenth_month_pay": thirteenth_month_pay,
                    "thirteenth_month_pay_deductions": thirteenth_month_pay_deductions,
                }
            )
            response.content = render_block_to_string(
                "payroll/payslip_management.html",
                "specific_thirteenth_month_pay_container",
                context,
            )
            response = create_global_alert_instance(
                response,
                "Deduction for the selected 13th Month Pay has been successfully removed.",
                "SUCCESS",
            )
            response = retarget(response, "#specific_thirteenth_month_pay_container")
            response = reswap(response, "outerHTML")
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while removing the variable deduction from the selected Thirteenth Month Pay. Details: {error}.",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def payroll_management(request):
    context = {}
    user = request.user
    current_month, current_year = get_current_month_and_year()
    selected_month = request.POST.get("selected_month") or current_month
    selected_year = request.POST.get("selected_year") or current_year
    months = get_list_of_months()
    years = get_payslip_year_list()
    payslips = get_user_payslips(user, selected_month, selected_year, released=True)
    _, thirteenth_month_pay_list = get_user_13th_month_pay_list(user.id, released=True)
    context.update(
        {
            "months": months,
            "years": years if years else [current_year],
            "selected_month": int(selected_month),
            "selected_year": int(selected_year),
            "payslips": payslips,
            "thirteenth_month_pay_list": thirteenth_month_pay_list,
        }
    )
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "payroll/payroll_management.html",
            "payroll_management_section",
            context,
        )
        response = retarget(response, "#payroll_management_section")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "payroll/payroll_management.html", context)


@login_required(login_url="/login")
def view_user_payslip(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            data = request.GET
            selected_payslip_id = data.get("payslip")
            response = trigger_client_event(
                response,
                "viewUserPayslip",
                {
                    "payslip_url_view": reverse(
                        "payroll:access_user_payslip",
                        kwargs={"payslip_id": selected_payslip_id},
                    )
                },
                after="swap",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def access_user_payslip(request, payslip_id):
    context = {}
    payslip = Payslip.objects.get(id=payslip_id)
    hr = get_user_with_hr_role().first()
    context.update({"payslip": payslip, "hr": hr})
    return render(request, "payroll/components/payslip_view.html", context)


@login_required(login_url="/login")
def view_user_thirteenth_month_pay_payslip(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            data = request.GET
            selected_payslip_id = data.get("thirteenth_month_pay")
            response = trigger_client_event(
                response,
                "viewUserPayslip",
                {
                    "payslip_url_view": reverse(
                        "payroll:access_user_thirteenth_month_pay_payslip",
                        kwargs={"thirteenth_month_pay_id": selected_payslip_id},
                    )
                },
                after="swap",
            )
            response = reswap(response, "none")
            return response


@login_required(login_url="/login")
def access_user_thirteenth_month_pay_payslip(request, thirteenth_month_pay_id):
    context = {}
    payslip = ThirteenthMonthPay.objects.get(id=thirteenth_month_pay_id)
    hr = get_user_with_hr_role().first()
    context.update({"payslip": payslip, "hr": hr})
    return render(
        request, "payroll/components/thirteenth_month_pay_payslip_view.html", context
    )


# App Shared View


def payroll_module_close_modals(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        event_name = data.get("event_name")
        response = HttpResponse()
        response = trigger_client_event(response, event_name, after="swap")
        response = reswap(response, "none")
        return response
