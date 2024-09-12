from django.core.management.base import BaseCommand

from payroll.models import Mp2


class Command(BaseCommand):
    help = "Initializes MP2 settings if they are not already set."

    def handle(self, *args, **options):
        if Mp2.objects.exists():
            self.stdout.write(
                "MP2 settings already exist. To update them, navigate to Salary and Rank Management -> Deduction Settings -> Pag-Ibig -> MP2."
            )
        else:
            try:
                Mp2.objects.create()
            except Exception as error:
                self.stdout.write(
                    f"An error occurred while initializing MP2 settings: {error}"
                )
            else:
                self.stdout.write("MP2 settings have been successfully initialized.")
