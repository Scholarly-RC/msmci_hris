from enum import Enum


class Modules(Enum):
    ATTENDANCE = "ATTENDANCE"
    PERFORMANCE_AND_LEARNING = "PERFORMANCE_AND_LEARNING"
    PAYROLL = "PAYROLL"
    LEAVE = "LEAVE"


class AttendanceReports(Enum):
    ATTENDANCE = "ATTENDANCE"


class PayrollReports(Enum):
    YEARLY_SALARY_EXPENSE = "YEARLY_SALARY_EXPENSE"

    def get_display_name(self):
        if self.value == PayrollReports.YEARLY_SALARY_EXPENSE.value:
            return "Yearly Salary Expense"
        return None
