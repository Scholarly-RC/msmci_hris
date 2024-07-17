import calendar
from attendance.enums import Months


def get_list_of_months():
    return [(month.name, month.value) for month in Months]
