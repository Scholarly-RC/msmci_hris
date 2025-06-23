from django.core.management.base import BaseCommand
from django_q.models import Schedule
from django_q.tasks import schedule


class Command(BaseCommand):
    help = "Control the biometric capture service (start/stop)"

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            choices=["start", "stop"],
            help="Start or stop the biometric capture service",
        )

    def handle(self, *args, **options):
        action = options["action"]
        task_name = "attendance.tasks.run_biometric_capture"

        if action == "start":
            if Schedule.objects.filter(func=task_name).exists():
                self.stdout.write(self.style.WARNING("Service is already running"))
                return

            schedule(
                task_name, schedule_type=Schedule.ONCE, repeats=-1  # Run indefinitely
            )
            self.stdout.write(self.style.SUCCESS("Started biometric capture service"))

        elif action == "stop":
            deleted, _ = Schedule.objects.filter(func=task_name).delete()
            if deleted:
                self.stdout.write(
                    self.style.SUCCESS("Stopped biometric capture service")
                )
            else:
                self.stdout.write(self.style.WARNING("No running service found"))
