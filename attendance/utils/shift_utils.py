from django.apps import apps


def get_all_shifts():
    """
    Retrieves all shifts, ordered by their start time.
    Returns a queryset of all shift instances.
    """
    ShiftModel = apps.get_model("attendance", "Shift")
    return ShiftModel.objects.all().order_by("start_time")
