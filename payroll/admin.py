from django.contrib import admin

from payroll.models import DeductionConfiguration, Job, MinimumWage, Mp2

# Register your models here.
admin.site.register(DeductionConfiguration)
admin.site.register(Job)
admin.site.register(MinimumWage)
admin.site.register(Mp2)
