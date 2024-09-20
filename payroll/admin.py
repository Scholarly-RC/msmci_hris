from django.contrib import admin

from payroll.models import (
    FixedCompensation,
    Job,
    MandatoryDeductionConfiguration,
    MinimumWage,
    Mp2,
    Payslip,
    VariableDeductionConfiguration,
)

# Register your models here.
admin.site.register(FixedCompensation)
admin.site.register(Job)
admin.site.register(MandatoryDeductionConfiguration)
admin.site.register(MinimumWage)
admin.site.register(Mp2)
admin.site.register(Payslip)
admin.site.register(VariableDeductionConfiguration)
