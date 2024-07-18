import calendar

from attendance.enums import Months


def get_list_of_months():
    return [(month.name, month.value) for month in Months]


def get_readable_date(year, month: int, day):
    return f"{Months(month).name} {day}, {year}"
