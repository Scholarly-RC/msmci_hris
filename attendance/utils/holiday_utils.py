from django.apps import apps


def get_holidays(year=""):
    HolidayModel = apps.get_model("attendance", "Holiday")
    holidays = HolidayModel.objects.order_by("-year", "-month", "-day")
    regular_holidays = holidays.filter(is_regular=True)
    special_holidays = holidays.filter(is_regular=False)
    if year and year != "0":
        special_holidays = special_holidays.filter(year=year)
    return regular_holidays, special_holidays


def get_holidays_year_list() -> list:
    HolidayModel = apps.get_model("attendance", "Holiday")

    holiday_years = (
        HolidayModel.objects.filter(is_regular=False, year__isnull=False)
        .values_list("year", flat=True)
        .order_by("-year")
        .distinct()
    )

    return list(holiday_years)
