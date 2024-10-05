from django.apps import apps


def get_all_shifts():
    ShiftModel = apps.get_model("attendance", "Shift")
    return ShiftModel.objects.all().order_by("start_time")
