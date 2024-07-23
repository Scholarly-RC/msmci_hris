from django.core.management.base import BaseCommand
from attendance.models import AttendanceRecord


class Command(BaseCommand):
    help = "Resets all of the attendance records."

    def handle(self, *args, **options):
        AttendanceRecord.objects.all().delete()
        self.stdout.write("All attendance records successfully deleted.")
