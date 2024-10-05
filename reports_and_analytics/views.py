from django.http import HttpResponse
from django.urls import reverse
from django.shortcuts import render
from reports_and_analytics.utils import (
    get_list_of_modules,
    get_reports_for_specific_module,
    get_filter_contexts_for_specific_report,
    get_yearly_salary_expense_report_data,
)
from django_htmx.http import reswap, retarget, trigger_client_event
from render_block import render_block_to_string

from reports_and_analytics.enums import PayrollReports


# Create your views here.
def menu(request):
    context = {}
    selected_module = request.GET.get("selected_module", "")
    selected_report = request.GET.get("selected_report", "")
    modules = get_list_of_modules()
    reports = get_reports_for_specific_module(selected_module)
    context.update(get_filter_contexts_for_specific_report(selected_report))
    context.update(
        {
            "modules": modules,
            "reports": reports,
            "selected_module": selected_module,
            "selected_report": selected_report,
        }
    )
    if request.htmx:
        response = HttpResponse()
        response.content = render_block_to_string(
            "reports_and_analytics/menu.html",
            "reports_and_analytics_filter_section",
            context,
        )
        response = retarget(response, "#reports_and_analytics_filter_section")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "reports_and_analytics/menu.html", context)


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
