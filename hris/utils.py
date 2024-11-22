import random
import string
from typing import Literal

from django_htmx.http import trigger_client_event


def create_global_alert_instance(
    response,
    message: str,
    type: Literal["INFO", "WARNING", "SUCCESS", "DANGER"],
    duration: int = 5,
):
    context = {"message": message, "type": type, "duration": duration}
    response = trigger_client_event(
        response, "initializeGlobalAlert", context, after="swap"
    )
    return response


def generate_short_string_id(length=5) -> str:
    return ''.join(random.choices(string.ascii_lowercase, k=length))
