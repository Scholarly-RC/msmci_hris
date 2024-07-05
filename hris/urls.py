from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("chat/", include("chat.urls", namespace="chat")),
    path("attendance/", include("attendance.urls", namespace="attendance")),
    path("", include("core.urls", namespace="core")),
]
