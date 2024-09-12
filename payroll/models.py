from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import Department
from payroll.utils import (
    calculate_basic_salary_for_grade,
    calculate_basic_salary_steps,
)


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
