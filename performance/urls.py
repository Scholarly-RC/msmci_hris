from django.urls import include, path

app_name = "performance"

from performance import views as performance_views

urlpatterns = [
    path(
        "polls-management/<str:poll_id>/delete",
        performance_views.delete_selected_poll,
        name="delete_selected_poll",
    ),
    path(
        "polls-management/<str:poll_id>/add-choice",
        performance_views.modify_poll_choices,
        name="modify_poll_choices",
    ),
    path(
        "polls-management/<str:poll_id>",
        performance_views.polls_management,
        name="polls_management_with_selected_poll",
    ),
    path(
        "polls-management",
        performance_views.polls_management,
        name="polls_management",
    ),
    # path(
    #     "polls",
    #     performance_views.polls_management,
    #     name="polls_management",
    # ),
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
        "user-evaluation-management/modify/reset",
        performance_views.reset_evaluation,
        name="reset_evaluation",
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
        "evaluation/submit-user-evaluation/peer",
        performance_views.submit_peer_evaluation,
        name="submit_peer_evaluation",
    ),
    path(
        "evaluation/submit-user-evaluation",
        performance_views.submit_self_evaluation,
        name="submit_self_evaluation",
    ),
    path(
        "evaluation/submit-evaluation-rating/<str:for_peer>",
        performance_views.submit_evaluation_rating,
        name="submit_peer_evaluation_rating",
    ),
    path(
        "evaluation/submit-evaluation-rating",
        performance_views.submit_evaluation_rating,
        name="submit_evaluation_rating",
    ),
    path(
        "evaluation/swtich",
        performance_views.switch_performance_evalution,
        name="switch_performance_evalution",
    ),
    path(
        "peer-evaluation/<str:evaluation_id>",
        performance_views.performance_peer_evaluation,
        name="selected_performance_peer_evaluation",
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
