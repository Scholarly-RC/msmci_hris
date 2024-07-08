from django.contrib import admin

from attendance.models import Attendance, DailyAttendanceRecord, Shift

admin.site.register(Attendance)
admin.site.register(DailyAttendanceRecord)
admin.site.register(Shift)
