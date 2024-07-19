import calendar
import datetime

from attendance.enums import Months


def get_list_of_months():
    return [(month.name, month.value) for month in Months]


def get_readable_date(year, month: int, day) -> str:
    return f"{Months(month).name} {day}, {year}"


def get_readable_date_from_date_oject(dateobject: datetime.date) -> str:
    return dateobject.strftime("%B %d, %Y")


def get_date_object(year: int, month: int, day: int) -> datetime.date:
    return datetime.date(year, month, day)
