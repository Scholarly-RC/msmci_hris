from decimal import Decimal
import json
from django.apps import apps
from reports_and_analytics.enums import Modules, PayrollReports

from payroll.utils import get_payslip_year_list

from attendance.enums import Months


def get_list_of_modules():
    return [(module.name, module.value) for module in Modules]


def get_reports_for_specific_module(module: str = ""):
    if module == Modules.PAYROLL.value:
        return get_payroll_reports()
    return []


def get_filter_contexts_for_specific_report(report: str = "") -> dict:
    if report == PayrollReports.YEARLY_SALARY_EXPENSE.value:
        return {"years": get_payslip_year_list()}
    return {}


def get_yearly_salary_expense_report_context():
    return {"years": get_payslip_year_list()}


def get_payroll_reports():
    return [
        (payroll_report.value, payroll_report.get_display_name())
        for payroll_report in PayrollReports
    ]


def get_yearly_salary_expense_report_data(selected_year):
    def _get_total_net_income(months, payslips):
        total_amount = 0
        total_list = []
        for month in months:
            total = 0
            for payslip in payslips.filter(month=month):
                net_salary = payslip.get_data().get("net_salary")
                total += net_salary
            total_amount += total
            total_list.append(str(round(total, 2)))
        return total_list, round(total_amount, 2)

    PayslipModel = apps.get_model("payroll", "Payslip")
    payslips = PayslipModel.objects.filter(released=True, year=selected_year).order_by(
        "month"
    )
    months_value = payslips.values_list("month", flat=True).distinct()
    months_name = [Months(month).name[:3].title() for month in months_value]

    total_per_month_list, total_expenses = _get_total_net_income(months_value, payslips)

    return {
        "chart_option_data": json.dumps(
            {"months": months_name, "total_amounts": total_per_month_list}
        ),
        "total_expenses": total_expenses,
        "selected_year": selected_year,
    }
