from django.contrib import admin

from attendance.models import (
    AttendanceRecord,
    DailyShiftRecord,
    DailyShiftSchedule,
    Shift,
)

admin.site.register(AttendanceRecord)
admin.site.register(DailyShiftRecord)
admin.site.register(DailyShiftSchedule)
admin.site.register(Shift)
