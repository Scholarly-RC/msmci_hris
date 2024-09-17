from django.contrib import admin

from payroll.models import (
    Compensation,
    DeductionConfiguration,
    Job,
    MinimumWage,
    Mp2,
    Payslip,
)

# Register your models here.
admin.site.register(Compensation)
admin.site.register(DeductionConfiguration)
admin.site.register(Job)
admin.site.register(MinimumWage)
admin.site.register(Mp2)
admin.site.register(Payslip)
