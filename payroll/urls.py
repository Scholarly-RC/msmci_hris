from django.urls import path

app_name = "payroll"

from payroll import views as payroll_views

urlpatterns = [
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
