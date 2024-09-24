from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from hris import views as hris_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("attendance/", include("attendance.urls", namespace="attendance")),
    path("chat/", include("chat.urls", namespace="chat")),
    path(
        "payroll/",
        include("payroll.urls", namespace="payroll"),
    ),
    path(
        "performance-and-learning/",
        include("performance.urls", namespace="performance"),
    ),
    path(
        "alert/",
        hris_views.show_alert,
        name="show_alert",
    ),
    path("", include("core.urls", namespace="core")),
    path("prose/", include("prose.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
