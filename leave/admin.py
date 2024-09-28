from django.contrib import admin

from leave.models import Leave, LeaveApprover, LeaveCredit

# Register your models here.
admin.site.register(Leave)
admin.site.register(LeaveApprover)
admin.site.register(LeaveCredit)
