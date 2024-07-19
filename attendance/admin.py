from django.contrib import admin

from attendance.models import (
    Attendance,
    DailyAttendanceRecord,
    DailyShiftRecord,
    DailyShiftSchedule,
    Shift,
)

admin.site.register(Attendance)
admin.site.register(DailyAttendanceRecord)
admin.site.register(DailyShiftRecord)
admin.site.register(DailyShiftSchedule)
admin.site.register(Shift)
