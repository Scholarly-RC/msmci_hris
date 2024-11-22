import json

from django.http import HttpResponse
from django_htmx.http import reswap, retarget, trigger_client_event
from render_block import render_block_to_string

from hris.utils import generate_short_string_id


def show_alert(request):
    context = {}
    global_alert_template = "components/global_alert.html"
    if request.method == "GET" and request.htmx:
        data = request.GET
        details = json.loads(data.get("details", {}))
        alert_id = generate_short_string_id()
        alert_close_id = generate_short_string_id()
        alert_duration = details.get("duration")
        context.update(
            {
                "alert_id": alert_id,
                "alert_close_id": alert_close_id,
                "alert_message": details.get("message"),
                "alert_type": details.get("type"),
                "alert_duration": alert_duration,
            }
        )
        response = HttpResponse()
        response.content = render_block_to_string(
            global_alert_template,
            "global_alert",
            context,
        )
        response = trigger_client_event(
            response,
            "showGlobalAlert",
            {
                "alertId": alert_id,
                "alertCloseId": alert_close_id,
                "alertDuration": alert_duration,
            },
            after="swap",
        )
        response = retarget(response, "#global_alert_container")
        response = reswap(response, "beforeend")
        return response
