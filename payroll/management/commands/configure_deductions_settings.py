import json
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from payroll.models import DeductionConfiguration


class Command(BaseCommand):
    help = "Initializes the minimum wage settings if they are not already set."

    def handle(self, *args, **options):
        if DeductionConfiguration.objects.exists():
            self.stdout.write(
                "A deduction setting already exists. To update it, please go to Salary and Rank Management -> Deduction Settings."
            )
        else:
            try:
                with open("fixtures/initial_deductions_config.json", "r") as file:
                    data = json.load(file)
                current_date = make_aware(datetime.now()).date().strftime("%Y-%m-%d")
                DeductionConfiguration.objects.create(
                    config=data, history=[{"date_set": current_date, "config": data}]
                )

            except Exception as error:
                self.stdout.write(f"An error occurred: {error}")
            else:
                self.stdout.write(
                    "Deduction settings have been successfully initialized."
                )
