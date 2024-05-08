from django.db import models
from django.contrib.auth.models import User


class UserDetails(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    phone_number = models.CharField(max_length=500, null=True, blank=True)
    address = models.CharField(max_length=500, null=True, blank=True)
    

    class Meta:
        verbose_name_plural = "User Details"

    def __str__(self):
        return self.user.get_full_name()
