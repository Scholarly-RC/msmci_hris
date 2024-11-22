import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _

from attendance.utils.date_utils import (
    get_date_object,
    get_months_dict,
    get_readable_date_from_date_object,
)


# Create your models here.
class AttendanceRecord(models.Model):
    class Punch(models.TextChoices):
        TIME_IN = "IN", _("Time In")
        TIME_OUT = "OUT", _("Time Out")

    user_biometric_detail = models.ForeignKey(
        "core.BiometricDetail",
        on_delete=models.RESTRICT,
        related_name="attendance_records",
        null=True,
        blank=True,
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
        return f"User ID: {self.user_id_from_device} - {self.punch} - {self.get_localtime_timestamp()}"

    def get_localtime_timestamp(self):
        return localtime(self.timestamp)

    def get_localtime_time(self):
        return self.get_localtime_timestamp().time()

    def get_localtime_time_str(self):
        return self.get_localtime_time().strftime("%H:%M")


class Shift(models.Model):
    description = models.TextField(_("Shift Description"), null=True, blank=True)
    start_time = models.TimeField(_("Shift Start Time"), null=True, blank=True)
    end_time = models.TimeField(_("Shift End Time"), null=True, blank=True)
    start_time_2 = models.TimeField(_("Shift Second Start Time"), null=True, blank=True)
    end_time_2 = models.TimeField(_("Shift Second End Time"), null=True, blank=True)

    is_active = models.BooleanField(_("Shift Is Active"), default=True)

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Shifts"

    def __str__(self):
        shift_str = f"{self.description} - {self.start_time} to {self.end_time}"
        if self.start_time_2 and self.end_time_2:
            shift_str + f" - {self.start_time} to {self.end_time}"
        return shift_str

    def get_twelve_hour_format_start_time(self):
        if self.start_time:
            return self.start_time.strftime("%I:%M %p")
        return None

    def get_twelve_hour_format_end_time(self):
        if self.end_time:
            return self.end_time.strftime("%I:%M %p")
        return None

    def get_twelve_hour_format_shift_range(self):
        start_time = self.get_twelve_hour_format_start_time()
        end_time = self.get_twelve_hour_format_end_time()
        if start_time and end_time:
            return f"{start_time} to {end_time}"
        return None


class DailyShiftSchedule(models.Model):
    date = models.DateField(_("Daily Shift Schedule Date"), null=True, blank=True)
    shift = models.ForeignKey(
        Shift, on_delete=models.RESTRICT, related_name="daily_shift_schedules"
    )
    user = models.ForeignKey(
        User, on_delete=models.RESTRICT, related_name="daily_shift_schedules"
    )

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Daily Shift Schedules"

    def __str__(self):
        return f"{get_readable_date_from_date_object(self.date) if self.date else ''} {self.shift} - {self.user.userdetails.get_user_fullname()}"


class DailyShiftRecord(models.Model):
    date = models.DateField(_("Daily Shift Record Date"), null=True, blank=True)
    shifts = models.ManyToManyField(
        DailyShiftSchedule, related_name="daily_shift_records", blank=True
    )
    department = models.ForeignKey(
        "core.Department",
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
            get_readable_date_from_date_object(self.date) if self.date else "",
            self.department.name if self.department else "",
            "Approved" if self.is_approved else "",
        ]
        return " ".join(str_details)


class Holiday(models.Model):
    name = models.CharField(_("Holiday Name"), max_length=500, null=True, blank=True)

    day = models.IntegerField(_("Holiday Day"), null=True, blank=True)
    month = models.IntegerField(_("Holiday Month"), null=True, blank=True)
    year = models.IntegerField(_("Holiday Year"), null=True, blank=True)

    is_regular = models.BooleanField(_("Is Holiday Regular"), default=False)

    class Meta:
        verbose_name_plural = "Holidays"

    def __str__(self):
        holiday_str = f"{self.name} - " + self.get_display_date()
        return holiday_str

    def get_name_display(self):
        return f"{self.name} ({'Regular' if self.is_regular else 'Special'})"

    def get_holiday_date(self):
        return get_date_object(
            self.year or datetime.datetime.now().year, self.month, self.day
        )

    def get_display_date(self):
        display_date = f"{get_months_dict().get(self.month)} {self.day}"
        if not self.is_regular:
            display_date += f", {self.year}"
        return display_date


class OverTime(models.Model):
    class Status(models.TextChoices):
        PENDING = "PEND", _("Pending")
        APPROVED = "APP", _("Approved")
        REJECTED = "REK", _("Rejected")

    user = models.ForeignKey(
        User, on_delete=models.RESTRICT, related_name="overtime_requests"
    )
    approver = models.ForeignKey(
        User, on_delete=models.RESTRICT, related_name="approved_overtimes"
    )
    date = models.DateField(_("Overtime Date"), null=True, blank=True)

    status = models.CharField(
        _("Overtime Request Status"),
        choices=Status.choices,
        max_length=4,
        default=Status.PENDING.value,
        null=True,
        blank=True,
    )

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Overtime Requests"

    def __str__(self):
        return f"Overtime request by {self.user.userdetails.get_user_fullname()} on {self.date} - Status: {self.get_status_display()}"

    def get_display_date(self):
        return get_readable_date_from_date_object(self.date)

    def get_status_display(self):
        return self.Status(self.status).name

    def get_requestor_display(self):
        return self.user.userdetails.get_user_fullname().title()

    def get_approver_display(self):
        return self.approver.userdetails.get_user_fullname().title()
