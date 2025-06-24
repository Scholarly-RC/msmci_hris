from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django_htmx.http import reswap, retarget, trigger_client_event
from render_block import render_block_to_string

from reports_and_analytics.utils import (
    get_age_demographics_report_data,
    get_all_employees_report_data,
    get_daily_staffing_report_data,
    get_education_level_report_data,
    get_employee_leave_summary_report_data,
    get_employee_performance_evaluation_summary_data,
    get_employee_yearly_salary_salary_report_data,
    get_employees_per_department_report_data,
    get_filter_contexts_for_specific_report,
    get_gender_demographics_report_data,
    get_list_of_modules,
    get_religion_report_data,
    get_reports_for_specific_module,
    get_resignation_report_data,
    get_yearly_salary_expense_report_data,
    get_years_of_experience_report_data,
)


@login_required(login_url="/login")
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
@login_required(login_url="/login")
def view_daily_staffing_report(request, selected_date="", option="all"):
    context = {}
    user = request.user
    is_user_hr = user.userdetails.is_hr()
    if not is_user_hr:
        context["hide_print_download_button"] = True

    selected_date = request.POST.get("selected_date") or selected_date

    context["option"] = option
    context.update(get_daily_staffing_report_data(selected_date_str=selected_date))
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "reports_and_analytics/components/daily_staffing_report.html",
            "content",
            context,
        )
        response = retarget(response, "#report_content_display")
        response = reswap(response, "innerHTML")
        return response

    if not is_user_hr:
        return redirect(reverse("core:main"))

    context["for_print_download"] = True

    return render(
        request,
        "reports_and_analytics/components/daily_staffing_report.html",
        context,
    )


@login_required(login_url="/login")
def popup_daily_staffing_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_date = data.get("selected_date")
        option = data.get("option")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_daily_staffing_report_with_data",
                    kwargs={
                        "selected_date": selected_date,
                        "option": option,
                    },
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


### Performance and Learning Reports Views ###
@login_required(login_url="/login")
def view_employee_performance_evaluation_summary(
    request, selected_user="", selected_year="", option="all"
):
    context = {}
    user = request.user
    is_user_hr = user.userdetails.is_hr()
    if not is_user_hr:
        selected_user = user.id
        context["hide_print_download_button"] = True

    selected_user = request.POST.get("selected_user") or selected_user
    selected_year = request.POST.get("selected_year") or selected_year
    context["option"] = option
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

    if not is_user_hr:
        return redirect(reverse("core:main"))

    context["for_print_download"] = True

    return render(
        request,
        "reports_and_analytics/components/employee_performance_evaluation_summary_report.html",
        context,
    )


@login_required(login_url="/login")
def popup_employee_performance_evaluation_summary(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_year = data.get("selected_year")
        selected_user = data.get("selected_user")
        option = data.get("option")
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
                        "option": option,
                    },
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


### Payroll Reports Views ###
@login_required(login_url="/login")
def view_yearly_salary_expense_report(request, selected_year="", option="all"):
    context = {}
    selected_year = request.POST.get("selected_year") or selected_year
    context["option"] = option
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


@login_required(login_url="/login")
def popup_yearly_salary_expense_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_year = data.get("selected_year")
        option = data.get("option")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_yearly_salary_expense_report_with_data",
                    kwargs={"selected_year": selected_year, "option": option},
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


@login_required(login_url="/login")
def view_employee_yearly_salary_summary_report(
    request, selected_user="", selected_year="", option="all"
):
    context = {}
    user = request.user
    is_user_hr = user.userdetails.is_hr()
    if not is_user_hr:
        selected_user = user.id
        context["hide_print_download_button"] = True

    selected_user = request.POST.get("selected_user") or selected_user
    selected_year = request.POST.get("selected_year") or selected_year
    context["option"] = option
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

    if not is_user_hr:
        return redirect(reverse("core:main"))

    context["for_print_download"] = True

    return render(
        request,
        "reports_and_analytics/components/employee_yearly_salary_summary_report.html",
        context,
    )


@login_required(login_url="/login")
def popup_employee_yearly_salary_summary_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_year = data.get("selected_year")
        selected_user = data.get("selected_user")
        option = data.get("option")
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
                        "option": option,
                    },
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


### Leave Reports Views ###
@login_required(login_url="/login")
def view_employee_leave_summary_report(
    request, selected_user="", from_date="", to_date="", option="all"
):
    context = {}
    user = request.user
    is_user_hr = user.userdetails.is_hr()
    if not is_user_hr:
        selected_user = user.id
        context["hide_print_download_button"] = True

    selected_user = request.POST.get("selected_user") or selected_user
    from_date = request.POST.get("from_date") or from_date
    to_date = request.POST.get("to_date") or to_date
    context["option"] = option
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

    if not is_user_hr:
        return redirect(reverse("core:main"))

    context["for_print_download"] = True

    return render(
        request,
        "reports_and_analytics/components/employee_leave_summary_report.html",
        context,
    )


@login_required(login_url="/login")
def popup_employee_leave_summary_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        selected_user = data.get("selected_user")
        from_date = data.get("from_date")
        to_date = data.get("to_date")
        option = data.get("option")
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
                        "option": option,
                    },
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


### Users Reports Views ###
@login_required(login_url="/login")
def view_all_employees_report(request, as_of_date="", option="all"):
    context = {}
    as_of_date = (
        request.POST.get("selected_as_of_date")
        or as_of_date
        or str(datetime.now().date())
    )
    context["option"] = option
    context.update(get_all_employees_report_data(as_of_date))
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "reports_and_analytics/components/all_employees_report.html",
            "content",
            context,
        )
        response = retarget(response, "#report_content_display")
        response = reswap(response, "innerHTML")
        return response

    context["for_print_download"] = True
    return render(
        request,
        "reports_and_analytics/components/all_employees_report.html",
        context,
    )


@login_required(login_url="/login")
def popup_all_employees_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        as_of_date = data.get("as_of_date")
        option = data.get("option")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_all_employees_report_with_data",
                    kwargs={"as_of_date": as_of_date, "option": option},
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


@login_required(login_url="/login")
def view_employees_per_department_report(request, as_of_date="", option="all"):
    context = {}
    as_of_date = (
        request.POST.get("selected_as_of_date")
        or as_of_date
        or str(datetime.now().date())
    )
    context["option"] = option
    context.update(get_employees_per_department_report_data(as_of_date))
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "reports_and_analytics/components/employees_per_department_report.html",
            "content",
            context,
        )
        response = retarget(response, "#report_content_display")
        response = reswap(response, "innerHTML")
        return response

    context["for_print_download"] = True
    return render(
        request,
        "reports_and_analytics/components/employees_per_department_report.html",
        context,
    )


@login_required(login_url="/login")
def popup_employees_per_department_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        as_of_date = data.get("as_of_date")
        option = data.get("option")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_employees_per_department_report_with_data",
                    kwargs={"as_of_date": as_of_date, "option": option},
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


@login_required(login_url="/login")
def view_age_demographics_report(request, as_of_date="", option="all"):
    context = {}
    as_of_date = (
        request.POST.get("selected_as_of_date")
        or as_of_date
        or str(datetime.now().date())
    )
    context["option"] = option
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


@login_required(login_url="/login")
def popup_age_demographics_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        as_of_date = data.get("as_of_date")
        option = data.get("option")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_age_demographics_report_with_data",
                    kwargs={"as_of_date": as_of_date, "option": option},
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


@login_required(login_url="/login")
def view_gender_demographics_report(request, as_of_date="", option="all"):
    context = {}
    as_of_date = (
        request.POST.get("selected_as_of_date")
        or as_of_date
        or str(datetime.now().date())
    )
    context["option"] = option
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


@login_required(login_url="/login")
def popup_gender_demographics_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        as_of_date = data.get("as_of_date")
        option = data.get("option")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_gender_demographics_report_with_data",
                    kwargs={"as_of_date": as_of_date, "option": option},
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


@login_required(login_url="/login")
def view_years_of_experience_report(request, as_of_date="", option="all"):
    context = {}
    as_of_date = (
        request.POST.get("selected_as_of_date")
        or as_of_date
        or str(datetime.now().date())
    )
    context["option"] = option
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


@login_required(login_url="/login")
def popup_years_of_experience_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        as_of_date = data.get("as_of_date")
        option = data.get("option")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_years_of_experience_report_with_data",
                    kwargs={"as_of_date": as_of_date, "option": option},
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


@login_required(login_url="/login")
def view_education_level_report(request, as_of_date="", option="all"):
    context = {}
    as_of_date = (
        request.POST.get("selected_as_of_date")
        or as_of_date
        or str(datetime.now().date())
    )
    context["option"] = option
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


@login_required(login_url="/login")
def popup_education_level_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        as_of_date = data.get("as_of_date")
        option = data.get("option")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_education_level_report_with_data",
                    kwargs={"as_of_date": as_of_date, "option": option},
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


@login_required(login_url="/login")
def view_religion_report(request, as_of_date="", option="all"):
    context = {}
    as_of_date = (
        request.POST.get("selected_as_of_date")
        or as_of_date
        or str(datetime.now().date())
    )
    context["option"] = option
    context.update(get_religion_report_data(as_of_date))
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "reports_and_analytics/components/religion_report.html",
            "content",
            context,
        )
        response = retarget(response, "#report_content_display")
        response = reswap(response, "innerHTML")
        return response

    context["for_print_download"] = True
    return render(
        request,
        "reports_and_analytics/components/religion_report.html",
        context,
    )


@login_required(login_url="/login")
def popup_religion_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        as_of_date = data.get("as_of_date")
        option = data.get("option")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_religion_report_with_data",
                    kwargs={"as_of_date": as_of_date, "option": option},
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response


@login_required(login_url="/login")
def view_resignation_report(request, from_date="", to_date="", option="all"):
    context = {}

    from_date = request.POST.get("from_date") or from_date
    to_date = request.POST.get("to_date") or to_date
    context["option"] = option
    context.update(get_resignation_report_data(from_date, to_date))
    if request.htmx and request.method == "POST":
        response = HttpResponse()
        response.content = render_block_to_string(
            "reports_and_analytics/components/resignation_report.html",
            "content",
            context,
        )
        response = retarget(response, "#report_content_display")
        response = reswap(response, "innerHTML")
        return response

    context["for_print_download"] = True

    return render(
        request,
        "reports_and_analytics/components/resignation_report.html",
        context,
    )


@login_required(login_url="/login")
def popup_resignation_report(request):
    if request.htmx and request.method == "POST":
        data = request.POST
        from_date = data.get("from_date")
        to_date = data.get("to_date")
        option = data.get("option")
        response = HttpResponse()
        response = trigger_client_event(
            response,
            "openSelectedReport",
            {
                "report_url_view": reverse(
                    "reports_and_analytics:view_resignation_report_with_data",
                    kwargs={
                        "from_date": from_date,
                        "to_date": to_date,
                        "option": option,
                    },
                )
            },
            after="swap",
        )
        response = reswap(response, "none")
        return response
