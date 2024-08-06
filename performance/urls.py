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
        "user-evaluation-management/modify/<str:pk>/<str:quarter>/<str:year>",
        performance_views.modify_user_evaluation,
        name="modify_user_evaluation",
    ),
    path(
        "user-evaluation-management/<str:year>",
        performance_views.user_evaluation_management,
        name="user_evaluation_management_filtered",
    ),
    path(
        "user-evaluation-management",
        performance_views.user_evaluation_management,
        name="user_evaluation_management",
    ),
    path(
        "evaluation/submit-evaluation-rating",
        performance_views.submit_evaluation_rating,
        name="submit_evaluation_rating",
    ),
    path(
        "peer-evaluation",
        performance_views.performance_peer_evaluation,
        name="performance_peer_evaluation",
    ),
    path(
        "evaluation",
        performance_views.performance_evaluation,
        name="performance_evaluation",
    ),
    path(
        "section-switch",
        performance_views.switch_performance_management_section,
        name="switch_performance_management_section",
    ),
    path(
        "",
        performance_views.performance_management,
        name="performance_management",
    ),
]
