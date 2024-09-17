from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from attendance.enums import Months
from core.models import Department
from payroll.utils import calculate_basic_salary_for_grade, calculate_basic_salary_steps


# Create your models here.
class MinimumWage(models.Model):
    amount = models.DecimalField(
        _("Minimum Wage Amount"),
        max_digits=10,
        decimal_places=2,
    )

    history = models.JSONField(
        _("Minimum Wage History"), null=True, blank=True, default=list
    )

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Minimum Wage"

    def __str__(self):
        return f"Basic Salary: {self.amount}"


class Job(models.Model):
    title = models.CharField(_("Job Title"), max_length=500)
    code = models.CharField(_("Job Code"), max_length=10)

    department = models.ManyToManyField(Department, related_name="jobs", blank=True)

    salary_grade = models.IntegerField(_("Job Salary Grade"), null=True, blank=True)

    is_active = models.BooleanField(_("Is Job Active"), default=True)

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Jobs"

    def __str__(self):
        return f"{self.code} - {self.title}"

    def get_salary_data(self):
        data = []

        salary_grade = self.salary_grade

        for rank in range(1, settings.MAX_JOB_RANK + 1):
            basic_salary = calculate_basic_salary_for_grade(salary_grade)
            steps = calculate_basic_salary_steps(basic_salary)
            data.append(
                {
                    f"{self.code}-{rank}": {
                        "salary_grade": salary_grade,
                        "basic_salary": round(basic_salary, 2),
                        "steps": steps,
                    }
                }
            )
            salary_grade += 1
        return data

    def get_number_of_steps_for_header(self):
        return [f"STEP {step}" for step in range(1, settings.BASIC_SALARY_STEPS + 1)]


class DeductionConfiguration(models.Model):
    config = models.JSONField(
        _("Deduction Configuration"), null=True, blank=True, default=list
    )

    history = models.JSONField(
        _("Deduction Configuration History"), null=True, blank=True, default=list
    )

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "Deduction Configuration"
        verbose_name_plural = "Deduction Configurations"

    def __str__(self):
        return "Deduction Configuration"

    def get_config(self, name):
        for item in self.config:
            if item.get("name") == name:
                return item
        return None

    def sss_config(self):
        return self.get_config("SSS")

    def philhealth_config(self):
        return self.get_config("PHILHEALTH")

    def pagibig_config(self):
        return self.get_config("PAG-IBIG")

    def tax_config(self):
        return self.get_config("TAX")


class Mp2(models.Model):
    users = models.ManyToManyField(User, blank=True, related_name="mp2")

    amount = models.DecimalField(
        _("Contribution Amount"), blank=True, null=True, max_digits=7, decimal_places=2
    )

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "MP2"

    def __str__(self):
        return "MP2 - Users"


class Compensation(models.Model):
    class CompensationType(models.TextChoices):
        ALLOWANCE = "AL", _("Allowance")
        HONORARIUM = "HO", _("Honorarium")
        GOVERNMENT_GRANT = "GG", _("Government Grant")
        THIRTEENTH_MONTH = "13", _("13th Month")
        OTHERS = "OT", _("Others")

    type = models.CharField(
        _("Compensation Type"),
        max_length=2,
        choices=CompensationType.choices,
        default=None,
        null=True,
        blank=True,
    )

    specific_type = models.CharField(
        _("Specific Type"), max_length=500, null=True, blank=True
    )

    amount = models.DecimalField(
        _("Compensation Amount"), blank=True, null=True, max_digits=9, decimal_places=2
    )

    users = models.ManyToManyField(User, blank=True, related_name="compensations")

    month = models.IntegerField(_("Compensation Month"), null=True, blank=True)
    year = models.IntegerField(_("Compensation Month"), null=True, blank=True)

    class Meta:
        verbose_name_plural = "Compensations"

    def __str__(self):
        return f"{self.CompensationType(self.type).name} - {Months(self.month).name} - {self.year}"

    def get_type_display(self):
        if self.type == self.CompensationType.OTHERS.value:
            return self.specific_type.title()
        return self.CompensationType(self.type).name.title()


class Payslip(models.Model):
    user = models.ForeignKey(User, on_delete=models.RESTRICT)
    rank = models.CharField(
        _("Current User Rank"), max_length=500, null=True, blank=True
    )
    salary = models.DecimalField(
        _("Current User Salary"), blank=True, null=True, max_digits=9, decimal_places=2
    )
    deductions = models.DecimalField(
        _("Current Total Deductions"),
        blank=True,
        null=True,
        max_digits=9,
        decimal_places=2,
    )
    compensations = models.DecimalField(
        _("Current Total Compensation"),
        blank=True,
        null=True,
        max_digits=9,
        decimal_places=2,
    )

    status = models.JSONField(_("Payslip Status"), null=True, blank=True, default=dict)

    month = models.IntegerField(_("Payslip Month"), null=True, blank=True)
    year = models.IntegerField(_("Payslip Year"), null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Payslips"

    def __str__(self):
        return f"{Months(self.month).name} - {self.year} payslip of User: {self.user.userdetails.get_user_fullname()}"
