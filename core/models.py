import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.utils import date_to_string, get_user_profile_picture_directory_path


class UserDetails(models.Model):
    class EducationalAttainment(models.TextChoices):
        KINDERGARTEN = "KG", _("Kindergarten")
        ELEMENTARY = "EL", _("Elementary")
        HIGH_SCHOOL = "HS", _("High School")
        BACHELOR = "BA", _("Bachelor")
        MASTER = "MA", _("Master")
        DOCTORATE = "DR", _("Doctorate")

    class CivilStatus(models.TextChoices):
        SINGLE = "SI", _("Single")
        MARRIED = "MA", _("Married")
        DIVORCED = "DI", _("Divorced")
        WIDOWED = "WI", _("Widowed")
        SEPARATED = "SE", _("Separated")

    class Role(models.TextChoices):
        HR = "HR", _("Human Resource")
        DEPARTMENT_HEAD = "DH", _("Department Head")
        EMPLOYEE = "EMP", _("Employee")

    user = models.OneToOneField(User, on_delete=models.RESTRICT, primary_key=True)
    profile_picture = models.FileField(
        _("User Profile Picture"),
        null=True,
        blank=True,
        upload_to=get_user_profile_picture_directory_path,
    )
    date_of_birth = models.DateField(_("User Date of Birth"), null=True, blank=True)
    phone_number = models.CharField(
        _("User Phone Number"), max_length=500, null=True, blank=True
    )
    address = models.CharField(_("User Address"), max_length=500, null=True, blank=True)
    education = models.CharField(
        _("User Educational Attainment"),
        max_length=2,
        choices=EducationalAttainment.choices,
        default=None,
        null=True,
        blank=True,
    )
    civil_status = models.CharField(
        _("User Civil Status"),
        max_length=2,
        choices=CivilStatus.choices,
        default=None,
        null=True,
        blank=True,
    )
    date_of_hiring = models.DateField(_("User Date of Hiring"), null=True, blank=True)
    employee_number = models.CharField(
        _("User Employee Number"), max_length=500, null=True, blank=True
    )
    rank = models.CharField(_("User Rank"), max_length=500, null=True, blank=True)

    department = models.ForeignKey(
        "Department", on_delete=models.RESTRICT, null=True, blank=True
    )

    user_role = models.CharField(
        _("User Role"),
        max_length=3,
        choices=Role.choices,
        default=None,
        null=True,
        blank=True,
    )

    updated = models.DateField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "User Details"

    def __str__(self):
        return self.user.get_full_name()

    def get_age(self):
        if self.date_of_birth:
            today = datetime.date.today()
            age = (
                today.year
                - self.date_of_birth.year
                - (
                    (today.month, today.day)
                    < (self.date_of_birth.month, self.date_of_birth.day)
                )
            )
            return age
        return None

    def get_years_in_service(self):
        if self.date_of_hiring:
            today = datetime.date.today()
            years_in_service = (
                today.year
                - self.date_of_hiring.year
                - (
                    (today.month, today.day)
                    < (self.date_of_hiring.month, self.date_of_hiring.day)
                )
            )
            return years_in_service
        return None

    def str_date_of_birth(self):
        return date_to_string(self.date_of_birth)

    def str_date_of_hiring(self):
        return date_to_string(self.date_of_hiring)

    def is_hr(self):
        return self.user_role == self.Role.HR

    def is_department_head(self):
        return self.user_role == self.Role.DEPARTMENT_HEAD

    def is_employee(self):
        return self.user_role == self.Role.EMPLOYEE | self.user_role is None


class BiometricDetail(models.Model):
    user = models.OneToOneField(User, on_delete=models.RESTRICT, null=True, blank=True)
    uid_in_device = models.IntegerField(_("Biometric UID"), null=True, blank=True)

    class Meta:
        verbose_name_plural = "Biometric Details"

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.uid_in_device}"


class Department(models.Model):
    name = models.CharField(_("Department Name"), max_length=500, null=True, blank=True)
    code = models.CharField(_("Department Code"), max_length=500, null=True, blank=True)
    is_active = models.BooleanField(_("Is Department Active"), default=True)
    created = models.DateField(auto_now_add=True, null=True, blank=True)
    updated = models.DateField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Departments"

    def __str__(self):
        return self.name
