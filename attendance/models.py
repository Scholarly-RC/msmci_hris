from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BiometricDetail


# Create your models here.
class Attendance(models.Model):

    class Punch(models.TextChoices):
        TIME_IN = "IN", _("Time In")
        TIME_OUT = "OUT", _("Time Out")
        OVERTIME_IN = "OT_IN", _("Overtime In")
        OVERTIME_OUT = "OT_OUT", _("Overtime Out")

    user = models.ForeignKey(
        BiometricDetail, on_delete=models.RESTRICT, null=True, blank=True
    )

    user_id_from_device = models.IntegerField(
        _("Attendance UID From Device"), null=True, blank=True
    )

    timestamp = models.DateTimeField(_("Attendance Timestamp"), null=True, blank=True)
    punch = models.CharField(
        _("Attendance Punch"),
        choices=Punch.choices,
        max_length=6,
        default=None,
        null=True,
        blank=True,
    )

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"{self.user_id_from_device} - {self.punch} - {self.timestamp}"
