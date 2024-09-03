from django.core.management.base import BaseCommand

from core.models import UserDetails


class Command(BaseCommand):
    help = "Resets all of the attendance records."

    def handle(self, *args, **options):
        try:
            employee_role = UserDetails.Role.EMPLOYEE.value
            UserDetails.objects.filter(role__isnull=True).update(role=employee_role)
        except Exception as error:
            self.stdout.write(f"{error}")
        else:
            self.stdout.write(
                "Users without roles have been successfully assigned the Employee role."
            )
