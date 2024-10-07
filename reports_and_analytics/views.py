from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django_htmx.http import reswap, retarget, trigger_client_event
from render_block import render_block_to_string

from reports_and_analytics.enums import PayrollReports
from reports_and_analytics.utils import (
    get_age_demographics_report_data,
    get_education_level_report_data,
    get_employee_leave_summary_report_data,
    get_employee_performance_evaluation_summary_data,
    get_employee_punctuality_report_data,
    get_employee_yearly_salary_salary_report_data,
    get_filter_contexts_for_specific_report,
    get_gender_demographics_report_data,
    get_list_of_modules,
    get_reports_for_specific_module,
    get_yearly_salary_expense_report_data,
    get_years_of_experience_report_data,
)


# Create your views here.
def reports_and_analytics(request):
    context = {}
    user = request.user
    is_user_hr = user.userdetails.is_hr()
    selected_module = request.GET.get("selected_module", "")
    selected_report = request.GET.get("selected_report", "")
    modules = get_list_of_modules(for_hr=is_user_hr)
    reports = get_reports_for_specific_module(module=selected_module, for_hr=is_user_hr)
    context.update(
        get_filter_contexts_for_specific_report(
            report=selected_report, for_hr=is_user_hr
        )
    )
    context.update(
        {
            "modules": modules,
            "reports": reports,
            "selected_module": selected_module,
            "selected_report": selected_report,
            "is_user_hr": is_user_hr,
        }
    )
    if request.htmx:
        response = HttpResponse()
        response.content = render_block_to_string(
            "reports_and_analytics/reports_and_analytics.html",
            "reports_and_analytics_filter_section",
            context,
        )
        response = retarget(response, "#reports_and_analytics_filter_section")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "reports_and_analytics/reports_and_analytics.html", context)


### Attendance Reports Views ###
def view_employee_punctuality_report(
    request, selected_user="", from_date="", to_date=""
):
    context = {}
    user = request.user
    is_user_hr = user.userdetails.is_hr()
    if not is_user_hr:
        selected_user = user.id

    selected_user = request.POST.get("selected_user") or selected_user
    from_date = request.POST.get("from_date") or from_date
    to_date = request.POST.get("to_date") or to_date

    context.update(
        get_employee_punctuality_report_data(selected_user, from_date, to_date)
    )
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "reports_and_analytics/components/employee_punctuality_report.html",
            "content",
            context,
        )
        response = retarget(response, "#report_content_display")
        response = reswap(response, "innerHTML")
        return response
    context["for_print_download"] = True
    return render(
        request,
        "reports_and_analytics/components/employee_punctuality_report.html",
        context,
    )


def popup_employee_punctuality_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_user = data.get("selected_user")
        from_date = data.get("from_date")
        to_date = data.get("to_date")

        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_employee_punctuality_report_with_data",
                    kwargs={
                        "selected_user": selected_user,
                        "from_date": from_date,
                        "to_date": to_date,
                    },
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


### Performance and Learning Reports Views ###
def view_employee_performance_evaluation_summary(
    request, selected_user="", selected_year=""
):
    context = {}
    user = request.user
    is_user_hr = user.userdetails.is_hr()
    if not is_user_hr:
        selected_user = user.id

    selected_user = request.POST.get("selected_user") or selected_user
    selected_year = request.POST.get("selected_year") or selected_year

    context.update(
        get_employee_performance_evaluation_summary_data(selected_year, selected_user)
    )
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "reports_and_analytics/components/employee_performance_evaluation_summary_report.html",
            "content",
            context,
        )
        response = retarget(response, "#report_content_display")
        response = reswap(response, "innerHTML")
        return response
    context["for_print_download"] = True
    return render(
        request,
        "reports_and_analytics/components/employee_performance_evaluation_summary_report.html",
        context,
    )


def popup_employee_performance_evaluation_summary(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_year = data.get("selected_year")
        selected_user = data.get("selected_user")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_employee_performance_evaluation_summary_with_data",
                    kwargs={
                        "selected_year": selected_year,
                        "selected_user": selected_user,
                    },
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


### Payroll Reports Views ###
def view_yearly_salary_expense_report(request, selected_year=""):
    context = {}
    selected_year = request.POST.get("selected_year") or selected_year
    context.update(get_yearly_salary_expense_report_data(selected_year))
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "reports_and_analytics/components/yearly_salary_expense_report.html",
            "content",
            context,
        )
        response = retarget(response, "#report_content_display")
        response = reswap(response, "innerHTML")
        return response
    context["for_print_download"] = True
    return render(
        request,
        "reports_and_analytics/components/yearly_salary_expense_report.html",
        context,
    )


def popup_yearly_salary_expense_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_year = data.get("selected_year")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_yearly_salary_expense_report_with_data",
                    kwargs={"selected_year": selected_year},
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


def view_employee_yearly_salary_summary_report(
    request, selected_user="", selected_year=""
):
    context = {}
    user = request.user
    is_user_hr = user.userdetails.is_hr()
    if not is_user_hr:
        selected_user = user.id

    selected_user = request.POST.get("selected_user") or selected_user
    selected_year = request.POST.get("selected_year") or selected_year

    context.update(
        get_employee_yearly_salary_salary_report_data(selected_year, selected_user)
    )
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "reports_and_analytics/components/employee_yearly_salary_summary_report.html",
            "content",
            context,
        )
        response = retarget(response, "#report_content_display")
        response = reswap(response, "innerHTML")
        return response
    context["for_print_download"] = True
    return render(
        request,
        "reports_and_analytics/components/employee_yearly_salary_summary_report.html",
        context,
    )


def popup_employee_yearly_salary_summary_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_year = data.get("selected_year")
        selected_user = data.get("selected_user")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_employee_yearly_salary_summary_report_with_data",
                    kwargs={
                        "selected_year": selected_year,
                        "selected_user": selected_user,
                    },
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


### Leave Reports Views ###
def view_employee_leave_summary_report(
    request, selected_user="", from_date="", to_date=""
):
    context = {}
    user = request.user
    is_user_hr = user.userdetails.is_hr()
    if not is_user_hr:
        selected_user = user.id

    selected_user = request.POST.get("selected_user") or selected_user
    from_date = request.POST.get("from_date") or from_date
    to_date = request.POST.get("to_date") or to_date

    context.update(
        get_employee_leave_summary_report_data(selected_user, from_date, to_date)
    )
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "reports_and_analytics/components/employee_leave_summary_report.html",
            "content",
            context,
        )
        response = retarget(response, "#report_content_display")
        response = reswap(response, "innerHTML")
        return response

    context["for_print_download"] = True
    return render(
        request,
        "reports_and_analytics/components/employee_leave_summary_report.html",
        context,
    )


def popup_employee_leave_summary_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_user = data.get("selected_user")
        from_date = data.get("from_date")
        to_date = data.get("to_date")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_employee_leave_summary_report_with_data",
                    kwargs={
                        "selected_user": selected_user,
                        "from_date": from_date,
                        "to_date": to_date,
                    },
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


### Users Reports Views ###
def view_age_demographics_report(request, as_of_date=""):
    context = {}
    as_of_date = (
        request.POST.get("selected_as_of_date")
        or as_of_date
        or str(datetime.now().date())
    )
    context.update(get_age_demographics_report_data(as_of_date))
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "reports_and_analytics/components/age_demographics_report.html",
            "content",
            context,
        )
        response = retarget(response, "#report_content_display")
        response = reswap(response, "innerHTML")
        return response

    context["for_print_download"] = True
    return render(
        request,
        "reports_and_analytics/components/age_demographics_report.html",
        context,
    )


def popup_age_demographics_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        as_of_date = data.get("as_of_date")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_age_demographics_report_with_data",
                    kwargs={"as_of_date": as_of_date},
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


def view_gender_demographics_report(request, as_of_date=""):
    context = {}
    as_of_date = (
        request.POST.get("selected_as_of_date")
        or as_of_date
        or str(datetime.now().date())
    )
    context.update(get_gender_demographics_report_data(as_of_date))
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "reports_and_analytics/components/gender_demographics_report.html",
            "content",
            context,
        )
        response = retarget(response, "#report_content_display")
        response = reswap(response, "innerHTML")
        return response

    context["for_print_download"] = True
    return render(
        request,
        "reports_and_analytics/components/gender_demographics_report.html",
        context,
    )


def popup_gender_demographics_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        as_of_date = data.get("as_of_date")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_gender_demographics_report_with_data",
                    kwargs={"as_of_date": as_of_date},
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


def view_years_of_experience_report(request, as_of_date=""):
    context = {}
    as_of_date = (
        request.POST.get("selected_as_of_date")
        or as_of_date
        or str(datetime.now().date())
    )
    context.update(get_years_of_experience_report_data(as_of_date))
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "reports_and_analytics/components/years_of_experience_report.html",
            "content",
            context,
        )
        response = retarget(response, "#report_content_display")
        response = reswap(response, "innerHTML")
        return response

    context["for_print_download"] = True
    return render(
        request,
        "reports_and_analytics/components/years_of_experience_report.html",
        context,
    )


def popup_years_of_experience_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        as_of_date = data.get("as_of_date")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_years_of_experience_report_with_data",
                    kwargs={"as_of_date": as_of_date},
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


def view_education_level_report(request, as_of_date=""):
    context = {}
    as_of_date = (
        request.POST.get("selected_as_of_date")
        or as_of_date
        or str(datetime.now().date())
    )
    context.update(get_education_level_report_data(as_of_date))
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "reports_and_analytics/components/education_level_report.html",
            "content",
            context,
        )
        response = retarget(response, "#report_content_display")
        response = reswap(response, "innerHTML")
        return response

    context["for_print_download"] = True
    return render(
        request,
        "reports_and_analytics/components/education_level_report.html",
        context,
    )


def popup_education_level_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        as_of_date = data.get("as_of_date")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_education_level_report_with_data",
                    kwargs={"as_of_date": as_of_date},
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response
