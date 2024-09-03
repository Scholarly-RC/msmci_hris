import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.utils import date_to_string, get_user_profile_picture_directory_path


class UserDetails(models.Model):
    class EducationalAttainment(models.TextChoices):
        HIGH_SCHOOL = "HS", _("High School")
        VOCATIONAL = "VC", _("Vocational")
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
        BOARD_OF_DIRECTOR = "BOD", _("Board of Director")
        HR = "HR", _("Human Resource")
        MANAGER = "MGR", _("Manager")
        DEPARTMENT_HEAD = "DH", _("Department Head")
        EMPLOYEE = "EMP", _("Employee")

    class Religion(models.TextChoices):
        ROMAN_CATHOLIC = "RC", _("Roman Catholic")
        ISLAM = "IS", _("Islam")
        EVANGELICAL = "EV", _("Evangelical")
        IGLESIA_NI_CRISTO = "INC", _("Iglesia ni Cristo")
        AGLIPAYAN = "AG", _("Aglipayan")
        JEHOVAH_WITNESSES = "JW", _("Jehovah's Witnesses")
        BORN_AGAIN_CHRISTIAN = "BAC", _("Born Again Christian")
        SEVENTH_DAY_ADVENTIST = "SDA", _("Seventh-day Adventist")
        UNITED_PENTECOSTAL = "UPC", _("United Pentecostal Church")
        BAPTIST = "BAP", _("Baptist")
        METHODIST = "MET", _("Methodist")
        CHURCH_OF_CHRIST = "COC", _("Church of Christ")

    user = models.OneToOneField(User, on_delete=models.RESTRICT, primary_key=True)
    middle_name = models.CharField(
        _("User Middle Name"), max_length=100, null=True, blank=True
    )
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
    degrees_earned = models.CharField(
        _("User Degrees Earned"), max_length=1000, null=True, blank=True
    )
    civil_status = models.CharField(
        _("User Civil Status"),
        max_length=2,
        choices=CivilStatus.choices,
        default=None,
        null=True,
        blank=True,
    )
    religion = models.CharField(
        _("User Religious Affiliation"),
        max_length=3,
        choices=Religion.choices,
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
        return f"User Details of USER {self.get_user_fullname() if self.get_user_fullname().strip() != '' else self.user.id}"

    def get_user_fullname(self):
        user_name_values = [
            self.user.first_name,
            f"{self.middle_name[0]}." if self.middle_name else "",
            self.user.last_name,
        ]
        return " ".join(user_name_values)

    def get_user_complete_fullname(self):
        user_name_values = [
            self.user.first_name,
            self.middle_name if self.middle_name else "",
            self.user.last_name,
        ]
        return " ".join(user_name_values)

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

    def get_years_and_months_in_service(self):
        if self.date_of_hiring:
            today = datetime.date.today()
            years_in_service = today.year - self.date_of_hiring.year
            months_in_service = today.month - self.date_of_hiring.month

            # Adjust for the case where the day of the month hasn't been reached yet
            if today.day < self.date_of_hiring.day:
                months_in_service -= 1

            # Adjust the years and months if necessary
            if months_in_service < 0:
                years_in_service -= 1
                months_in_service += 12

            return years_in_service, months_in_service

        return None

    def str_date_of_birth(self):
        return date_to_string(self.date_of_birth)

    def str_date_of_hiring(self):
        return date_to_string(self.date_of_hiring)

    def is_board_of_director(self):
        return self.user_role == self.Role.BOARD_OF_DIRECTOR

    def is_hr(self):
        return self.user_role == self.Role.HR

    def is_manager(self):
        return self.user_role == self.Role.MANAGER

    def is_department_head(self):
        return self.user_role == self.Role.DEPARTMENT_HEAD

    def is_employee(self):
        return self.user_role == self.Role.EMPLOYEE or self.user_role is None

    def get_user_full_user_role(self):
        user_role = (
            self.Role.EMPLOYEE.name
            if self.is_employee()
            else self.Role(self.user_role).name
        )
        user_role = user_role.replace("_", " ")
        return user_role


class BiometricDetail(models.Model):
    user = models.OneToOneField(User, on_delete=models.RESTRICT, null=True, blank=True)
    user_id_in_device = models.IntegerField(_("Biometric UID"), null=True, blank=True)

    class Meta:
        verbose_name_plural = "Biometric Details"

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.user_id_in_device}"


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
