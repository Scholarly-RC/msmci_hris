from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from leave.models import LeaveCredit


class Command(BaseCommand):
    help = "Initializes leave credits for users that have not yet been set."

    def handle(self, *args, **options):
        try:
            for user in User.objects.all():
                LeaveCredit.objects.get_or_create(
                    user=user, defaults={"credits": 0, "used_credits": 0}
                )
        except Exception as error:
            self.stdout.write(f"An error occurred: {error}")
        else:
            self.stdout.write("Leave credits have been successfully initialized.")
