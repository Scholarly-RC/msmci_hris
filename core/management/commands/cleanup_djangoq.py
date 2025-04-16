from django.core.management.base import BaseCommand
from django.utils import timezone
from django_q.conf import Conf
from django_q.models import Schedule, Task


class Command(BaseCommand):
    help = "Cleans up queued and scheduled tasks in Django Q2"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--queued",
            action="store_true",
            help="Only clean up queued tasks",
        )
        parser.add_argument(
            "--scheduled",
            action="store_true",
            help="Only clean up scheduled tasks",
        )
        parser.add_argument(
            "--failed",
            action="store_true",
            help="Also clean up failed tasks",
        )
        parser.add_argument(
            "--cluster",
            type=str,
            default=None,
            help="Only clean up tasks from a specific cluster",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        clean_queued = options["queued"] or not (
            options["queued"] or options["scheduled"]
        )
        clean_scheduled = options["scheduled"] or not (
            options["queued"] or options["scheduled"]
        )
        clean_failed = options["failed"]
        cluster = options["cluster"]

        if dry_run:
            self.stdout.write(
                self.style.NOTICE("Dry run mode - no tasks will actually be deleted")
            )

        # Clean up queued tasks
        if clean_queued:
            queued_tasks = Task.objects.filter(
                started__isnull=True,  # Not started yet
                stopped__isnull=True,  # Not stopped yet
                success__isnull=True,  # Not succeeded or failed yet
            )

            if cluster:
                queued_tasks = queued_tasks.filter(cluster=cluster)

            count = queued_tasks.count()
            if count > 0:
                self.stdout.write(f"Found {count} queued tasks to delete")
                if not dry_run:
                    deleted, _ = queued_tasks.delete()
                    self.stdout.write(
                        self.style.SUCCESS(f"Deleted {deleted} queued tasks")
                    )
            else:
                self.stdout.write("No queued tasks to delete")

        # Clean up scheduled tasks
        if clean_scheduled:
            scheduled_tasks = Schedule.objects.filter(
                repeats__lte=0,  # One-time tasks or exhausted repeats
                next_run__lt=timezone.now(),  # Past their run time
            )

            if cluster:
                scheduled_tasks = scheduled_tasks.filter(cluster=cluster)

            count = scheduled_tasks.count()
            if count > 0:
                self.stdout.write(f"Found {count} scheduled tasks to delete")
                if not dry_run:
                    deleted, _ = scheduled_tasks.delete()
                    self.stdout.write(
                        self.style.SUCCESS(f"Deleted {deleted} scheduled tasks")
                    )
            else:
                self.stdout.write("No scheduled tasks to delete")

        # Clean up failed tasks if requested
        if clean_failed:
            failed_tasks = Task.objects.filter(success=False)

            if cluster:
                failed_tasks = failed_tasks.filter(cluster=cluster)

            count = failed_tasks.count()
            if count > 0:
                self.stdout.write(f"Found {count} failed tasks to delete")
                if not dry_run:
                    deleted, _ = failed_tasks.delete()
                    self.stdout.write(
                        self.style.SUCCESS(f"Deleted {deleted} failed tasks")
                    )
            else:
                self.stdout.write("No failed tasks to delete")

        if dry_run:
            self.stdout.write(
                self.style.NOTICE("Dry run complete - no tasks were deleted")
            )
