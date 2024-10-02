import calendar
import datetime

from attendance.enums import Months


def get_list_of_months():
    """
    Returns a list of tuples with month names and their corresponding values from the Months enumeration.
    """
    return [(month.name, month.value) for month in Months]


def get_months_dict():
    """
    Returns a dictionary mapping month values to their corresponding names from the Months enumeration.
    """
    return {month.value: month.name for month in Months}


def get_readable_date(year, month: int, day) -> str:
    """
    Returns a human-readable date string in the format "Month Day, Year" for the given year, month, and day.
    """
    return f"{Months(month).name} {day}, {year}"


def get_readable_date_from_date_object(dateobject: datetime.date) -> str:
    """
    Converts a datetime.date object to a human-readable date string in the format "Month Day, Year".
    """
    return dateobject.strftime("%B %d, %Y")


def get_date_object(year: int, month: int, day: int) -> datetime.date:
    """
    Returns a datetime.date object for the specified year, month, and day.
    """
    return datetime.date(year, month, day)


def get_date_object_from_date_str(date_str: str):
    """
    Returns a datetime.date object for the specified date string.
    """
    date_object = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    return date_object


def get_time_object(time_str: str):
    """
    Converts a time string in "HH:MM" format to a datetime.time object.
    """
    return datetime.datetime.strptime(time_str, "%H:%M").time()


def get_twenty_four_hour_time_str_from_time_object(time_object):
    """
    Converts a datetime.time object to a 24-hour format time string "HH:MM".
    """
    return time_object.strftime("%H:%M")


def get_number_of_days_in_a_month(year: int, month: int):
    """
    Returns the number of days in the specified month and year.
    """
    return calendar.monthrange(year, month)
