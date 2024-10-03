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


def get_all_holidays_list():
    """
    Retrieves a list of all holidays from the Holiday model.
    """
    holiday_model = apps.get_model("attendance", "Holiday")
    all_holidays = holiday_model.objects.all()
    return all_holidays


def get_holiday_for_specific_month_and_year(month: int, year: int):
    """
    Retrieves holidays for a specific month and year, combining regular and non-regular holidays.
    """
    special_holidays_for_this_specific_month_and_year = (
        get_all_holidays_list()
        .filter(month=month, year=year, is_regular=False)
        .values_list("day", "name")
    )
    regular_holidays_for_this_specific_month_and_year = (
        get_all_holidays_list()
        .filter(month=month, is_regular=True)
        .values_list("day", "name")
    )
    combined_holidays = (
        special_holidays_for_this_specific_month_and_year
        | regular_holidays_for_this_specific_month_and_year
    )
    return combined_holidays


def get_holiday_for_specific_day(day: int, month: int, year: int):
    """
    # Retrieves a list of holidays that occur on a specific day, month, and year.
    """
    regular_holidays = get_all_holidays_list().filter(
        day=day, month=month, is_regular=True
    )
    special_holidays = get_all_holidays_list().filter(
        day=day, month=month, year=year, is_regular=False
    )

    combined_holidays = special_holidays | regular_holidays
    return combined_holidays
