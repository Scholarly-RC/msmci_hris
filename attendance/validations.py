def add_holiday_validation(payload):
    context = {}

    holiday_name = payload.get("holiday_name").strip()

    if not holiday_name:
        context["empty_holiday_name"] = "Holiday name required."

    return context
