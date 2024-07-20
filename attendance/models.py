from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from attendance.utils.date_utils import get_readable_date_from_date_oject
from core.models import BiometricDetail, Department


# Create your models here.
class AttendanceRecord(models.Model):
    class Punch(models.TextChoices):
        TIME_IN = "IN", _("Time In")
        TIME_OUT = "OUT", _("Time Out")
        OVERTIME_IN = "OT_IN", _("Overtime In")
        OVERTIME_OUT = "OT_OUT", _("Overtime Out")

    user = models.ForeignKey(
        BiometricDetail, on_delete=models.RESTRICT, null=True, blank=True
    )
    user_id_from_device = models.IntegerField(
        _("Attendance Record User ID From Device"), null=True, blank=True
    )
    timestamp = models.DateTimeField(_("Attendance Timestamp"), null=True, blank=True)
    punch = models.CharField(
        _("Attendance Record Punch"),
        choices=Punch.choices,
        max_length=6,
        default=None,
        null=True,
        blank=True,
    )
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Attendance Records"

    def __str__(self):
        return f"User ID: {self.user_id_from_device} - {self.punch} - {self.timestamp}"


class Shift(models.Model):
    description = models.TextField(_("Shift Description"), null=True, blank=True)
    start_time = models.TimeField(_("Shift Start Time"), null=True, blank=True)
    end_time = models.TimeField(_("Shift End Time"), null=True, blank=True)
    is_active = models.BooleanField(_("Shift Is Active"), default=True)

    class Meta:
        verbose_name_plural = "Shifts"

    def __str__(self):
        return f"{self.description} - {self.start_time} to {self.end_time}"


class DailyShiftSchedule(models.Model):
    shift = models.ForeignKey(
        Shift, on_delete=models.RESTRICT, related_name="daily_shift_schedules"
    )
    user = models.ForeignKey(User, on_delete=models.RESTRICT)

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Daily Shift Schedules"

    def __str__(self):
        return f"{self.shift} - {self.user.userdetails.get_user_fullname()}"


class DailyShiftRecord(models.Model):
    date = models.DateField(_("Daily Shift Record Date"), null=True, blank=True)
    shifts = models.ManyToManyField(
        DailyShiftSchedule, related_name="daily_shift_records", blank=True
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.RESTRICT,
        related_name="daily_shift_records",
        null=True,
        blank=True,
    )

    is_approved = models.BooleanField(
        _("Daily Shift Record Is Approved"), default=False
    )

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Daily Shift Records"

    def __str__(self):
        str_details = [
            get_readable_date_from_date_oject(self.date) if self.date else "",
            self.department.name if self.department else "",
            "Approved" if self.is_approved else "",
        ]
        return " ".join(str_details)
