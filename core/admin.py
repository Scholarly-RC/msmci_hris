from django.contrib import admin

from core.models import (
    AppLog,
    BiometricDetail,
    Department,
    Notification,
    PersonalFile,
    UserDetails,
)

admin.site.register(AppLog)
admin.site.register(BiometricDetail)
admin.site.register(Department)
admin.site.register(UserDetails)
admin.site.register(Notification)
admin.site.register(PersonalFile)
