from django.contrib import admin

from core.models import BiometricDetail, Department, Notification, UserDetails

admin.site.register(BiometricDetail)
admin.site.register(Department)
admin.site.register(UserDetails)
admin.site.register(Notification)
