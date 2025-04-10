from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import Department
from leave.enums import LeaveRequestAction


# Create your models here.
class LeaveApprover(models.Model):
    department = models.ForeignKey(
        Department, on_delete=models.RESTRICT, related_name="leave_approvers"
    )
    department_approver = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="department_approvals",
        blank=True,
        null=True,
    )
    director_approver = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="director_approvals",
        blank=True,
        null=True,
    )
    president_approver = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="president_approvals",
        blank=True,
        null=True,
    )
    hr_approver = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="hr_approvals",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name_plural = "Leave Approvers"

    def __str__(self):
        return f"Leave Approvers for {self.department.name} - Dept: {self.department_approver.userdetails.get_user_fullname()}, Director: {self.director_approver.userdetails.get_user_fullname()}, President: {self.president_approver.userdetails.get_user_fullname()}, HR: {self.hr_approver.userdetails.get_user_fullname()}"


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
    info = models.TextField(_("Leave Info"), blank=True, null=True)

    first_approver_data = models.JSONField(
        _("First Leave Approver Data"), null=True, blank=True, default=dict
    )

    second_approver_data = models.JSONField(
        _("Second Leave Approver Data"), null=True, blank=True, default=dict
    )

    class Meta:
        verbose_name_plural = "Leaves"

    def __str__(self):
        return f"{self.user.userdetails.get_user_fullname()} - {self.date} ({self.get_type_display()})"

    def get_type_display(self):
        if self.type:
            return self.LeaveType(self.type).label
        return None

    def get_status(self):
        if (
            self.first_approver_data["status"] == LeaveRequestAction.REJECTED.value
            or self.second_approver_data["status"] == LeaveRequestAction.REJECTED.value
        ):
            return LeaveRequestAction.REJECTED.value

        if (
            self.first_approver_data["status"] == LeaveRequestAction.APPROVED.value
            and self.second_approver_data["status"] == LeaveRequestAction.APPROVED.value
        ):
            return LeaveRequestAction.APPROVED.value

        return LeaveRequestAction.PENDING.value

    def get_user_status(self, user):
        if user.id == self.first_approver_data["approver"]:
            return self.first_approver_data["status"]

        if user.id == self.second_approver_data["approver"]:
            return self.second_approver_data["status"]

        return None

    def get_first_approver(self):
        return User.objects.get(id=self.first_approver_data["approver"])

    def get_second_approver(self):
        return User.objects.get(id=self.second_approver_data["approver"])

    def ready_for_second_approver(self):
        return self.first_approver_data["status"] != LeaveRequestAction.PENDING.value


class LeaveCredit(models.Model):
    user = models.OneToOneField(User, on_delete=models.RESTRICT, primary_key=True)
    credits = models.IntegerField(_("User Leave Credits"), null=True, blank=True)
    used_credits = models.IntegerField(_("User Leave Credits"), null=True, blank=True)

    class Meta:
        verbose_name_plural = "Leave Credits"

    def __str__(self):
        return f"{self.user.userdetails.get_user_fullname()}'s Leave Credits: {self.credits}"

    def get_remaining_leave_credits(self):
        if not self.credits:
            return None
        if not self.used_credits:
            return self.credits
        return self.credits - self.used_credits

    def reset_used_credits(self):
        self.used_credits = 0
        self.save()
