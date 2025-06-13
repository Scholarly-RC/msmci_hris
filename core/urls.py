from django.urls import path

from core import views as core_views

app_name = "core"

urlpatterns = [
    path("login", core_views.user_login, name="login"),
    path("logout", core_views.user_logout, name="logout"),
    path("register", core_views.user_register, name="register"),
    path(
        "set-user-password", core_views.set_new_user_password, name="set_user_password"
    ),
    # Settings #
    path("settings/add-department", core_views.add_department, name="add_department"),
    path(
        "settings/edit-department",
        core_views.edit_department,
        name="edit_department",
    ),
    path(
        "settings/delete-department",
        core_views.delete_department,
        name="delete_department",
    ),
    path("settings", core_views.settings, name="settings"),
    # APP LOGS #
    path("app-logs", core_views.app_logs, name="app_logs"),
    # USER PROFILE #
    path(
        "profile/preview-personal-file",
        core_views.preview_personal_file,
        name="preview_personal_file",
    ),
    path(
        "profile/reload-personal-files-section",
        core_views.reload_personal_files_section,
        name="reload_personal_files_section",
    ),
    path(
        "profile/delete-selected-personal-file",
        core_views.delete_selected_personal_file,
        name="delete_selected_personal_file",
    ),
    path(
        "profile/change-selected-category",
        core_views.change_selected_category,
        name="change_selected_category",
    ),
    path(
        "profile/add-personal-files",
        core_views.add_personal_files,
        name="add_personal_files",
    ),
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
        "user-management/modify-shift-modification-permission/<str:pk>",
        core_views.shift_modification_permission,
        name="shift_modification_permission",
    ),
    path(
        "user-management/user_resignation/<str:pk>",
        core_views.user_resignation,
        name="user_resignation",
    ),
    path(
        "user-management/modify-user-biometric-details/<str:pk>",
        core_views.modify_user_biometric_details,
        name="modify_user_biometric_details",
    ),
    path(
        "user-management/modify-user-details/update-rank-selection",
        core_views.update_rank_selection,
        name="update_rank_selection",
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
    path(
        "close-modals",
        core_views.core_module_close_modals,
        name="core_module_close_modals",
    ),
    path("", core_views.main, name="main"),
]
