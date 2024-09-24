from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from core.models import Department


# Create your models here.
class LeaveApprover(models.Model):
    department = models.ForeignKey(
        Department, on_delete=models.RESTRICT, related_name="leave_approvers"
    )
    department_approver = models.ForeignKey(
        User, on_delete=models.RESTRICT, related_name="department_approvals"
    )
    hr_approver = models.ForeignKey(
        User, on_delete=models.RESTRICT, related_name="hr_approvals"
    )

    class Meta:
        verbose_name_plural = "Leave Approvers"

    def __str__(self):
        return f"{self.department.name} - Dept: {self.department_approver.userdetails.get_user_fullname()}, HR: {self.hr_approver.userdetails.get_user_fullname()}"


class Leave(models.Model):
    class LeaveType(models.TextChoices):
        PAID = "PA", _("Paid Leave")
        UNPAID = "UN", _("Unpaid Leave")
        WORK_RELATED_TRIP = "WR", _("Work-Related Trip")

    user = models.ForeignKey(
        User, on_delete=models.RESTRICT, related_name="user_leaves"
    )
    date = models.DateField(_("Leave Date"), null=True, blank=True)
    type = models.CharField(
        _("Leave Type"),
        max_length=2,
        choices=LeaveType.choices,
        default=None,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name_plural = "Leaves"

    def __str__(self):
        return f"{self.user.userdetails.get_user_fullname()} - {self.date} ({self.get_type_display()})"

    def get_type_display(self):
        if self.type:
            return self.LeaveType(self.type).title()
        return None


class LeaveCredit(models.Model):
    user = models.OneToOneField(User, on_delete=models.RESTRICT, primary_key=True)
    credits = models.IntegerField(_("User Leave Credits"), null=True, blank=True)

    class Meta:
        verbose_name_plural = "Leave Credits"

    def __str__(self):
        return f"{self.user.userdetails.get_user_fullname()}'s Leave Credits: {self.credits}"
