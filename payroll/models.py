from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from attendance.enums import Months
from core.models import Department
from payroll.deductions import PagIbig, Philhealth, Sss, Tax
from payroll.utils import (
    calculate_basic_salary_for_grade,
    calculate_basic_salary_steps,
    get_mp2_object,
    get_payslip_compensations,
    get_payslip_variable_deductions,
    get_salary_from_rank,
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


class MandatoryDeductionConfiguration(models.Model):
    config = models.JSONField(
        _("Deduction Configuration"), null=True, blank=True, default=list
    )

    history = models.JSONField(
        _("Deduction Configuration History"), null=True, blank=True, default=list
    )

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "Mandatory Deduction Configuration"
        verbose_name_plural = "Mandatory Deduction Configurations"

    def __str__(self):
        return "Mandatory Deduction Configuration"

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


class VariableDeductionConfiguration(models.Model):
    name = models.CharField(_("Deduction Name"), max_length=500)
    payslip = models.ForeignKey(
        "Payslip", on_delete=models.RESTRICT, related_name="variable_deductions"
    )

    amount = models.DecimalField(
        _("Deduction Amount"), blank=True, null=True, max_digits=9, decimal_places=2
    )

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Variable Deduction Configurations"

    def __str__(self):
        return "Variable Deduction Configuration"


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

    def get_semi_monthly_amount(self):
        return self.amount / 2


class Payslip(models.Model):
    class Period(models.TextChoices):
        FIRST = "1ST", _("1st Period")
        SECOND = "2ND", _("2nd Period")

    user = models.ForeignKey(User, on_delete=models.RESTRICT)
    rank = models.CharField(
        _("Current User Rank"), max_length=500, null=True, blank=True
    )
    salary = models.DecimalField(
        _("Current User Salary"), blank=True, null=True, max_digits=9, decimal_places=2
    )

    period = models.CharField(
        _("Salary Period"),
        max_length=3,
        choices=Period.choices,
        default=None,
        null=True,
        blank=True,
    )

    finalized = models.BooleanField(_("Is Payslip Finalized"), default=False)

    month = models.IntegerField(_("Payslip Month"), null=True, blank=True)
    year = models.IntegerField(_("Payslip Year"), null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Payslips"

    def __str__(self):
        return f"{self.Period(self.period).name.title()} Period - {Months(self.month).name} - {self.year} payslip of user: {self.user.userdetails.get_user_fullname()}"

    def get_month_and_year(self):
        return f"{Months(self.month).name} - {self.year}"

    def update_salary(self):
        self.salary = get_salary_from_rank(self.rank)
        self.save()

    def get_data(self):
        salary_details = {}

        if not self.rank:
            return salary_details

        base_salary = self.salary

        payslip_compensations, total_compensation = get_payslip_compensations(self)

        payslip_variable_deductions, total_variable_deductions = (
            get_payslip_variable_deductions(self)
        )

        adjusted_salary_with_compensations = base_salary + total_compensation

        adjusted_salary_with_compensations_and_total_variable_deductions = (
            adjusted_salary_with_compensations / 2
        ) - total_variable_deductions

        # TODO: ASK FOR LOGIC

        # adjusted_salary_with_compensations -= (
        #     adjusted_salary_with_compensations
        #     - adjusted_salary_with_compensations_and_total_variable_deductions
        # )

        sss_employee_deduction = Sss(
            adjusted_salary_with_compensations
        ).get_employee_deduction()
        philhealth_employee_deduction = Philhealth(
            adjusted_salary_with_compensations
        ).get_employee_deduction()
        pag_ibig_employee_deduction = PagIbig().get_employee_deduction()
        mp2_employee_deduction = (
            get_mp2_object().amount if self.user.mp2.all() else Decimal(0.00)
        )

        salary_after_contributions = adjusted_salary_with_compensations - (
            sss_employee_deduction
            + philhealth_employee_deduction
            + mp2_employee_deduction
        )

        tax_employee_deduction = Tax(
            salary_after_contributions / 2
        ).get_employee_deduction()

        mandatory_deductions = (
            sss_employee_deduction
            + philhealth_employee_deduction
            + pag_ibig_employee_deduction
            + mp2_employee_deduction
            + tax_employee_deduction
        )

        total_deductions = mandatory_deductions + total_variable_deductions

        final_net_salary = adjusted_salary_with_compensations - mandatory_deductions

        salary_details.update(
            {
                "salary": base_salary / 2,
                "compensations": payslip_compensations,
                "variable_deductions": payslip_variable_deductions,
                "adjusted_salary_with_compensations": adjusted_salary_with_compensations
                / 2,
                "sss_deduction": sss_employee_deduction / 2,
                "philhealth_deduction": philhealth_employee_deduction / 2,
                "pag_ibig_deduction": pag_ibig_employee_deduction / 2,
                "mp2_deduction": mp2_employee_deduction / 2,
                "tax_deduction": tax_employee_deduction,
                "total_deductions": total_deductions / 2,
                "net_salary": final_net_salary / 2,
            }
        )
        return salary_details

    def get_data_for_template(self):
        def _combine_lists(list1, list2):
            combined_list = []

            len_first = len(list1)
            len_second = len(list2)
            max_len = max(len_first, len_second)

            for i in range(max_len):
                current_entry = []

                # First list entries
                if i < len_first:
                    for key, value in list1[i].items():
                        current_entry.append(key)
                        current_entry.append(value)
                else:
                    current_entry.extend(["", ""])

                # Second list entries
                if i < len_second:
                    for key, value in list2[i].items():
                        current_entry.append(key)
                        current_entry.append(value)
                else:
                    current_entry.extend(["", ""])

                combined_list.append(current_entry)

            return combined_list

        data = self.get_data()

        earnings = [{"Base Pay": data.get("salary")}] + [
            {compensation.get_type_display(): compensation.get_semi_monthly_amount()}
            for compensation in data.get("compensations")
        ]

        deductions = [
            {"SSS": data.get("sss_deduction")},
            {"PhilHealth": data.get("philhealth_deduction")},
            {"Pag-Ibig": data.get("pag_ibig_deduction")},
            {"MP2": data.get("mp2_deduction")},
            {"Tax": data.get("tax_deduction")},
        ]

        data_for_payslip_table = _combine_lists(earnings, deductions)

        return {
            "row_data": data_for_payslip_table,
            "total_earnings": data.get("adjusted_salary_with_compensations"),
            "total_deductions": data.get("total_deductions"),
            "net_salary": data.get("net_salary"),
        }
