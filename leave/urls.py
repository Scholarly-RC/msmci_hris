from django.urls import path

from leave import views as leave_views

app_name = "leave"

urlpatterns = [
    path(
        "user-leave/review",
        leave_views.user_review_leave_request,
        name="user_review_leave_request",
    ),
    path(
        "user-leave/request", leave_views.user_leave_request, name="user_leave_request"
    ),
    path("user-leave", leave_views.user_leave, name="user_leave"),
    path(
        "management/leave/<str:leave_id>/delete",
        leave_views.delete_leave_request,
        name="delete_leave_request",
    ),
    path(
        "management/leave/review",
        leave_views.review_leave_request,
        name="review_leave_request",
    ),
    path(
        "management/leave-credit-settings/edit",
        leave_views.edit_leave_credit_settings,
        name="edit_leave_credit_settings",
    ),
    path(
        "management/leave-credit-settings",
        leave_views.leave_credit_settings,
        name="leave_credit_settings",
    ),
    path(
        "management/approver-settings",
        leave_views.approver_settings,
        name="approver_settings",
    ),
    path(
        "close-modals",
        leave_views.leave_module_close_modals,
        name="leave_module_close_modals",
    ),
    path("management", leave_views.leave_management, name="leave_management"),
]
