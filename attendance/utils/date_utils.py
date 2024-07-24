import calendar
import datetime

from attendance.enums import Months


def get_list_of_months():
    return [(month.name, month.value) for month in Months]


def get_months_dict():
    return {month.value: month.name for month in Months}


def get_readable_date(year, month: int, day) -> str:
    return f"{Months(month).name} {day}, {year}"


def get_readable_date_from_date_oject(dateobject: datetime.date) -> str:
    return dateobject.strftime("%B %d, %Y")


def get_date_object(year: int, month: int, day: int) -> datetime.date:
    return datetime.date(year, month, day)


def get_time_object(time_str: str):
    return datetime.datetime.strptime(time_str, "%H:%M").time()


def get_twenty_four_hour_time_str_from_time_object(time_object):
    return time_object.strftime("%H:%M")


def get_number_of_days_in_a_month(year: int, month: int):
    return calendar.monthrange(year, month)
