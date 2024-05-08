from django.contrib import admin
from django.urls import path, include

from core import views as core_views

app_name = "core"

urlpatterns = [
    path("", core_views.user_login, name="main"),
    path("login", core_views.user_login, name="login"),
    path("logout", core_views.user_logout, name="logout"),
    path("register", core_views.user_register, name="register"),
    path("profile", core_views.user_profile, name="profile"),
    path("user-management/add-new-user", core_views.add_new_user, name="add_new_user"),
    path("user-management/<str:pk>/toggle-status", core_views.toggle_user_status, name="toggle_user_status"),
    path("user-management", core_views.user_management, name="user_management"),
]
