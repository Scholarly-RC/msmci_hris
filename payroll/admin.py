from django.contrib import admin

from payroll.models import Job, MinimumWage

# Register your models here.
admin.site.register(Job)
admin.site.register(MinimumWage)
