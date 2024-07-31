from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("attendance/", include("attendance.urls", namespace="attendance")),
    path("chat/", include("chat.urls", namespace="chat")),
    path("performance/", include("performance.urls", namespace="performance")),
    path("", include("core.urls", namespace="core")),
]
