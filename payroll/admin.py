from django.contrib import admin

from payroll.models import BasicSalary, Job

# Register your models here.
admin.site.register(BasicSalary)
admin.site.register(Job)
