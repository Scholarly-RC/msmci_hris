from django.urls import path

app_name = "payroll"

from payroll import views as payroll_views

urlpatterns = [
    path(
        "salary-and-rank-management/mp2-amount-settings",
        payroll_views.mp2_amount_settings,
        name="mp2_amount_settings",
    ),
    path(
        "salary-and-rank-management/mp2-settings/toggle-status",
        payroll_views.toggle_user_mp2_status,
        name="toggle_user_mp2_status",
    ),
    path(
        "salary-and-rank-management/mp2-settings",
        payroll_views.mp2_settings,
        name="mp2_settings",
    ),
    path(
        "salary-and-rank-management/deductions-settings",
        payroll_views.deductions_settings,
        name="deductions_settings",
    ),
    path(
        "salary-and-rank-management/minimum-wage-settings",
        payroll_views.minimum_wage_settings,
        name="minimum_wage_settings",
    ),
    path(
        "salary-and-rank-management/delete-job",
        payroll_views.delete_job,
        name="delete_job",
    ),
    path(
        "salary-and-rank-management/modify-job",
        payroll_views.modify_job,
        name="modify_job",
    ),
    path(
        "salary-and-rank-management/view-job",
        payroll_views.view_job,
        name="view_job",
    ),
    path(
        "salary-and-rank-management/update-job-list",
        payroll_views.update_job_list,
        name="update_job_list",
    ),
    path(
        "salary-and-rank-management/add-job",
        payroll_views.add_job,
        name="add_job",
    ),
    path(
        "salary-and-rank-management/close-modals",
        payroll_views.payroll_module_close_modals,
        name="payroll_module_close_modals",
    ),
    path(
        "salary-and-rank-management",
        payroll_views.salary_and_rank_management,
        name="salary_and_rank_management",
    ),
]
