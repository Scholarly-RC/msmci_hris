from django.contrib import admin

from core.models import BiometricDetail, Department, UserDetails

admin.site.register(BiometricDetail)
admin.site.register(UserDetails)
admin.site.register(Department)
