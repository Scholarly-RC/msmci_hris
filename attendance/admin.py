from django.contrib import admin

from attendance.models import (
    Attendance,
    DailyAttendanceRecord,
    DailyShiftRecords,
    DailyShiftSchedule,
    Shift,
)

admin.site.register(Attendance)
admin.site.register(DailyAttendanceRecord)
admin.site.register(DailyShiftRecords)
admin.site.register(DailyShiftSchedule)
admin.site.register(Shift)
