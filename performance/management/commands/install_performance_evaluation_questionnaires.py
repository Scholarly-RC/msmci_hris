import json

from django.core.management.base import BaseCommand

from performance.models import Questionnaire


class Command(BaseCommand):
    help = "Install performance evaluation questionnaires."

    def handle(self, *args, **options):
        try:
            with open("fixtures/evaluation_questionnaire_data.json", "r") as f:
                data = json.load(f)
                for questionnaire in data:
                    Questionnaire.objects.get_or_create(content=questionnaire)
        except Exception as error:
            self.stdout.write(f"{error}")
        else:
            self.stdout.write("Questionnaires successfully installed.")
