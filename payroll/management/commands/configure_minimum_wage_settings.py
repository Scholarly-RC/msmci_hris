from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from payroll.models import MinimumWage


class Command(BaseCommand):
    help = "Initializes the minimum wage settings if they are not already set."

    def add_arguments(self, parser):
        parser.add_argument(
            "--amount",
            type=float,
            help="The minimum wage amount to be set. This argument is required.",
        )

    def handle(self, *args, **options):
        if MinimumWage.objects.exists():
            self.stdout.write(
                "A minimum wage setting already exists. To update it, please go to Salary and Rank Management -> Minimum Wage Settings."
            )
        else:
            try:
                current_date = make_aware(datetime.now()).date().strftime("%Y-%m-%d")
                amount = options.get("amount")
                if amount is None:
                    self.stdout.write(
                        "Error: You must specify the minimum wage amount using the --amount option."
                    )
                    return

                MinimumWage.objects.create(
                    amount=amount,
                    history=[{"amount": amount, "date_set": current_date}],
                )
            except Exception as error:
                self.stdout.write(f"An error occurred: {error}")
            else:
                self.stdout.write(
                    "Minimum wage settings have been successfully initialized."
                )
