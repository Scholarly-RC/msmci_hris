import uuid
from typing import Literal

from django_htmx.http import trigger_client_event


def generate_short_uuid(length=5) -> str:
    return str(uuid.uuid4()).replace("-", "")[:length]


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
