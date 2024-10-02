from django.contrib import admin

from attendance.models import (
    AttendanceRecord,
    DailyShiftRecord,
    DailyShiftSchedule,
    Holiday,
    OverTime,
    Shift,
)

admin.site.register(AttendanceRecord)
admin.site.register(DailyShiftRecord)
admin.site.register(DailyShiftSchedule)
admin.site.register(Holiday)
admin.site.register(OverTime)
admin.site.register(Shift)
