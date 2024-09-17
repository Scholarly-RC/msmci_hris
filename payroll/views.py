from django.db.models import Q
from django.http import HttpResponse
from django.http.request import QueryDict
from django.shortcuts import render
from django_htmx.http import push_url, reswap, retarget, trigger_client_event
from render_block import render_block_to_string

from attendance.enums import Months
from attendance.utils.date_utils import get_list_of_months, get_months_dict
from core.utils import get_users_sorted_by_department
from hris.utils import create_global_alert_instance
from payroll.actions import (
    process_add_or_create_compensation,
    process_adding_job,
    process_deleting_job,
    process_get_or_create_user_payslip,
    process_modifying_compensation,
    process_modifying_compensation_user,
    process_modifying_job,
    process_removing_compensation,
    process_setting_deduction_config,
    process_setting_minimum_wage_amount,
    process_setting_mp2_amount,
    process_toggle_user_mp2_status,
)
from payroll.models import Compensation, Job
from payroll.utils import (
    get_compensation_types,
    get_compensation_year_list,
    get_current_month_and_year,
    get_deduction_configuration_object,
    get_department_list,
    get_job_list,
    get_minimum_wage_object,
    get_mp2_object,
    get_payslip_year_list,
    get_specific_compensation_and_users,
    get_users_with_payslip_data,
)
from payroll.validations import minimum_wage_update_validation, payslip_data_validation

### Salary and Rank Management Views


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
                response = reswap(response, "none")
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
                response = reswap(response, "none")
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
                response = reswap(response, "none")
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
                response = reswap(response, "none")
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
                response = reswap(response, "none")
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
            response = reswap(response, "none")
            return response


def compensations_settings(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        try:
            current_month, current_year = get_current_month_and_year()
            selected_month = request.POST.get("selected_month") or current_month
            selected_year = request.POST.get("selected_year") or current_year
            months = get_list_of_months()
            years = get_compensation_year_list()
            (
                _,
                existent_compensation_types,
                non_existent_compensation_type_choices,
            ) = get_compensation_types(selected_month, selected_year)
            context.update(
                {
                    "months": months,
                    "years": years if years else [current_year],
                    "selected_month": int(selected_month),
                    "selected_year": int(selected_year),
                    "existent_compensation_types": existent_compensation_types,
                    "non_existent_compensation_type_choices": non_existent_compensation_type_choices,
                }
            )
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "compensations_settings_modal_container",
                context,
            )
            response = retarget(response, "#compensations_settings_modal_container")
            response = reswap(response, "outerHTML")
            if request.method == "GET":
                response = trigger_client_event(
                    response, "openCompensationsSettingsModal", after="swap"
                )
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while accessing compensation settings. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


def modify_specific_compensation(request):
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
            process_modifying_compensation(data)
            response = create_global_alert_instance(
                response,
                "Compensation details have been successfully updated.",
                "SUCCESS",
            )
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while updating the compensation details. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


def add_specific_compensation(request):
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
            type = data.get("selected_non_existent_type", "OT")
            specific_type = data.get("other_types")
            if type == "OT" and (not specific_type or specific_type.strip() == ""):
                response = create_global_alert_instance(
                    response,
                    "The specific compensation name is required.",
                    "WARNING",
                )
                response = reswap(response, "none")
                return response
            compensation = process_add_or_create_compensation(
                type, specific_type, int(selected_month), int(selected_year)
            )
            (
                _,
                existent_compensation_types,
                non_existent_compensation_type_choices,
            ) = get_compensation_types(selected_month, selected_year)
            context.update(
                {
                    "months": months,
                    "years": years if years else [current_year],
                    "selected_month": int(selected_month),
                    "selected_year": int(selected_year),
                    "existent_compensation_types": existent_compensation_types,
                    "non_existent_compensation_type_choices": non_existent_compensation_type_choices,
                }
            )
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "compensations_settings_modal_container",
                context,
            )
            type_name = Compensation.CompensationType(compensation.type).name
            month_name = Months(compensation.month).name
            response = create_global_alert_instance(
                response,
                f"{compensation.get_type_display()} compensation has been successfully added for {month_name} {compensation.year}.",
                "SUCCESS",
            )
            response = retarget(response, "#compensations_settings_modal_container")
            response = reswap(response, "outerHTML")
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while adding the compensation. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


def remove_specific_compensation(request):
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
            process_removing_compensation(data)
            (
                _,
                existent_compensation_types,
                non_existent_compensation_type_choices,
            ) = get_compensation_types(selected_month, selected_year)
            context.update(
                {
                    "months": months,
                    "years": years if years else [current_year],
                    "selected_month": int(selected_month),
                    "selected_year": int(selected_year),
                    "existent_compensation_types": existent_compensation_types,
                    "non_existent_compensation_type_choices": non_existent_compensation_type_choices,
                }
            )
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "compensations_settings_modal_container",
                context,
            )
            response = create_global_alert_instance(
                response, "Compensation successfully removed.", "SUCCESS"
            )
            response = retarget(response, "#compensations_settings_modal_container")
            response = reswap(response, "outerHTML")
            return response
        except Exception as error:
            response = create_global_alert_instance(
                response,
                f"An error occurred while removing the compensation. Details: {error}",
                "DANGER",
            )
            response = reswap(response, "none")
            return response


def toggle_specific_compensation_users_view(request):
    context = {}
    if request.htmx and request.method == "POST":
        data = request.POST
        response = HttpResponse()
        selected_compensation_id = data.get("selected_compensation")
        compensation, compensation_users = get_specific_compensation_and_users(
            int(selected_compensation_id)
        )
        context["compensation"] = compensation
        if "hide" not in data:
            users = get_users_sorted_by_department()
            context.update(
                {
                    "users": users,
                    "compensation_users": compensation_users,
                }
            )
        response.content = render_block_to_string(
            "payroll/salary_and_rank_management.html",
            "specific_compensation_section",
            context,
        )
        response = retarget(response, "closest form")
        response = reswap(response, "outerHTML")
        return response


def modify_specific_compensation_users(request):
    context = {}
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        try:
            data = request.POST
            selected_compensation_id = data.get("selected_compensation")
            if "for_search" in data:
                compensation, compensation_users = get_specific_compensation_and_users(
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

            selected_user_id = data.get("selected_user") or data.get("user_to_remove")
            to_remove = "user_to_remove" in data and "selected_user" not in data
            compensation, user = process_modifying_compensation_user(
                int(selected_user_id), int(selected_compensation_id), to_remove
            )
            context.update({"user": user, "compensation": compensation})
            response.content = render_block_to_string(
                "payroll/salary_and_rank_management.html",
                "specific_user_section",
                context,
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


def modify_payslip(request):
    context = {}
    if request.htmx:
        response = HttpResponse()
        if request.method == "GET":
            data = request.GET
            errors = payslip_data_validation(data)
            if errors:
                response = create_global_alert_instance(
                    response, errors["empty_rank_error"], "WARNING"
                )
                response = reswap(response, "none")
                return response

            selected_month = data.get("selected_month")
            selected_year = data.get("selected_year")
            selected_user_id = data.get("selected_user")
            user, payslip = process_get_or_create_user_payslip(
                int(selected_user_id), int(selected_month), int(selected_year)
            )

            context.update({"selected_user": user, "payslip": payslip})
            response.content = render_block_to_string(
                "payroll/payslip_management.html",
                "modify_payslip_modal_container",
                context,
            )
            response = trigger_client_event(
                response, "openModifyPayslipModal", after="swap"
            )
            response = retarget(response, "#modify_payslip_modal_container")
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
