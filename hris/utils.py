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
    """
    Creates and triggers a global alert with the specified message, type, and duration.
    The alert is sent to the client-side via the `initializeGlobalAlert` event.
    """
    context = {"message": message, "type": type, "duration": duration}
    response = trigger_client_event(
        response, "initializeGlobalAlert", context, after="swap"
    )
    return response


def generate_short_string_id(length=5) -> str:
    """
    Generates a random short string ID of the specified length using lowercase letters.
    Default length is 5 characters.
    """
    return "".join(random.choices(string.ascii_lowercase, k=length))
