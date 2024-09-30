from django.urls import path

from core import views as core_views

app_name = "core"

urlpatterns = [
    path("", core_views.user_login, name="main"),
    path("login", core_views.user_login, name="login"),
    path("logout", core_views.user_logout, name="logout"),
    path("register", core_views.user_register, name="register"),
    path(
        "set-user-password", core_views.set_new_user_password, name="set_user_password"
    ),
    # USER PROFILE #
    path(
        "profile/change-user-password",
        core_views.change_user_password,
        name="change_user_password",
    ),
    path(
        "profile/upload-user-profile-picture",
        core_views.upload_user_profile_picture,
        name="upload_user_profile_picture",
    ),
    path("profile", core_views.user_profile, name="profile"),
    # USER MANAGEMENT #
    path(
        "user-management/modify-user-biometric-details/<str:pk>",
        core_views.modify_user_biometric_details,
        name="modify_user_biometric_details",
    ),
    path(
        "user-management/modify-user-details/<str:pk>",
        core_views.modify_user_details,
        name="modify_user_details",
    ),
    path("user-management/add-new-user", core_views.add_new_user, name="add_new_user"),
    path(
        "user-management/<str:pk>/toggle-status",
        core_views.toggle_user_status,
        name="toggle_user_status",
    ),
    path(
        "user-management/bulk-add-new-users",
        core_views.bulk_add_new_users,
        name="bulk_add_new_users",
    ),
    path("user-management", core_views.user_management, name="user_management"),
    path(
        "notifications/retrieve",
        core_views.retrieve_notifications,
        name="retrieve_notifications",
    ),
    path(
        "notifications/open",
        core_views.open_notification,
        name="open_notification",
    ),
    path(
        "notifications/button-indicator",
        core_views.notification_button_indicator,
        name="notification_button_indicator",
    ),
]
