from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from chat import views as chat_views

app_name = "chat"

urlpatterns = [
    path(
        "toggle/<str:open>",
        chat_views.toggle_chat_window,
        name="toggle_chat_window",
    ),
    path(
        "users",
        chat_views.search_chat_users,
        name="search_chat_users",
    ),
    path(
        "users/select",
        chat_views.select_chat_users,
        name="select_chat_users",
    ),
    path(
        "users/send-chat-message",
        chat_views.send_chat_message,
        name="send_chat_message",
    ),
]
