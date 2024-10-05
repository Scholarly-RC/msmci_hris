from django.urls import path

from reports_and_analytics import views as raa_views

app_name = "reports_and_analytics"

urlpatterns = [
    path(
        "report/yearly-salary-expense-report/view/<str:selected_year>",
        raa_views.view_yearly_salary_expense_report,
        name="view_yearly_salary_expense_report_with_data",
    ),
    path(
        "report/yearly-salary-expense-report/popup",
        raa_views.popup_yearly_salary_expense_report,
        name="popup_yearly_salary_expense_report",
    ),
    path(
        "report/yearly-salary-expense-report/view",
        raa_views.view_yearly_salary_expense_report,
        name="view_yearly_salary_expense_report",
    ),
    path("", raa_views.menu, name="reports_and_analytics_menu"),
]
