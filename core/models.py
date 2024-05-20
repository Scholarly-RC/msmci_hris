import datetime
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.db import models

from core.utils import date_to_string

class UserDetails(models.Model):

    class EducationalAttainment(models.TextChoices):
        KINDERGARTEN = 'KG', _('Kindergarten')
        ELEMENTARY = 'EL', _('Elementary')
        HIGH_SCHOOL = 'HS', _('High School')
        BACHELOR = 'BA', _('Bachelor')
        MASTER = 'MA', _('Master')
        DOCTORATE = 'DR', _('Doctorate')


    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=500, null=True, blank=True)
    address = models.CharField(max_length=500, null=True, blank=True)
    education = models.CharField(max_length=2, choices=EducationalAttainment.choices, default=EducationalAttainment.BACHELOR)
    date_of_hiring = models.DateField(null=True, blank=True)
    employee_number = models.CharField(max_length=500, null=True, blank=True)
    rank = models.CharField(max_length=500, null=True, blank=True)

    department = models.ForeignKey("Department", on_delete=models.SET_NULL, null=True, blank=True)

    updated = models.DateField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "User Details"

    def __str__(self):
        return self.user.get_full_name()
    
    def str_date_of_birth(self):
        return date_to_string(self.date_of_birth)
    
    def str_date_of_hiring(self):
        return date_to_string(self.date_of_hiring)


class Department(models.Model):
    name = models.CharField(max_length=500, null=True, blank=True)
    created = models.DateField(auto_now_add=True, null=True, blank=True)
    updated = models.DateField(auto_now_add=True, null=True, blank=True)
