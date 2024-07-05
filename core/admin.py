from django.contrib import admin

from core.models import Department, UserDetails

admin.site.register(UserDetails)
admin.site.register(Department)
