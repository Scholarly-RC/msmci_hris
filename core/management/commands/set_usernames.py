from django.core.management.base import BaseCommand

from core.actions import process_update_username


class Command(BaseCommand):
    help = "Update the usernames for all users."

    def handle(self, *args, **options):
        try:
            process_update_username()
        except Exception as error:
            self.stdout.write(self.style.ERROR(f"An error occurred: {error}"))
        else:
            self.stdout.write(
                self.style.SUCCESS("Usernames have been successfully updated.")
            )
