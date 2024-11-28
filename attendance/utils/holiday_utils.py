from django.apps import apps


def get_holidays(year=""):
    """
    Retrieves all holidays, separating them into regular and special holidays.
    Optionally filters special holidays by the specified year.
    Returns two querysets: regular holidays and special holidays.
    """
    HolidayModel = apps.get_model("attendance", "Holiday")
    holidays = HolidayModel.objects.order_by("-year", "-month", "-day")
    regular_holidays = holidays.filter(is_regular=True)
    special_holidays = holidays.filter(is_regular=False)
    if year and year != "0":
        special_holidays = special_holidays.filter(year=year)
    return regular_holidays, special_holidays


def get_holidays_year_list() -> list:
    """
    Retrieves a list of distinct years that have special holidays.
    The list is ordered in descending order.
    """
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
    HolidayModel = apps.get_model("attendance", "Holiday")
    all_holidays = HolidayModel.objects.all()
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


def get_holiday_for_specific_date_range(day_range, month: int, year: int):
    """
    Retrieves holidays (regular and special) for each day in the specified date range.
    Returns a dictionary with the day as the key and a queryset of holidays as the value.
    """
    all_holidays = get_all_holidays_list().filter(month=month, year=year)

    holiday_data = {day: [] for day in day_range}

    days_set = set(day_range)

    relevant_holidays = all_holidays.filter(day__in=days_set)

    for holiday in relevant_holidays:
        if holiday.day in holiday_data:
            holiday_data[holiday.day].append(holiday)

    return holiday_data
