from django.urls import include, path

app_name = "performance"

from performance import views as performance_views

urlpatterns = [
    path(
        "user-evaluation-management/<str:user_evaluation_id>/modify-evaluator",
        performance_views.modify_user_evaluation_evaluators,
        name="modify_user_evaluation_evaluators",
    ),
    path(
        "user-evaluation-management/<str:user_evaluation_id>/finalize/toggle",
        performance_views.finalize_user_evaluation_toggle,
        name="finalize_user_evaluation_toggle",
    ),
    path(
        "user-evaluation-management/modify/<str:pk>/<str:quarter>",
        performance_views.modify_user_evaluation,
        name="modify_user_evaluation",
    ),
    path(
        "user-evaluation-management",
        performance_views.user_evaluation_management,
        name="user_evaluation_management",
    ),
    path(
        "",
        performance_views.performance_management,
        name="performance_management",
    ),
]
