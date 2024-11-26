from enum import Enum


class Modules(Enum):
    ATTENDANCE = "ATTENDANCE"
    PERFORMANCE_AND_LEARNING = "PERFORMANCE_AND_LEARNING"
    PAYROLL = "PAYROLL"
    LEAVE = "LEAVE"
    USERS = "USERS"

    def get_display_name(self):
        if self.value == Modules.PERFORMANCE_AND_LEARNING.value:
            return "Performance and Learning"
        return self.value


class AttendanceReports(Enum):
    DAILY_STAFFING_REPORT = "DAILY_STAFFING_REPORT"

    def get_display_name(self):
        if self.value == AttendanceReports.DAILY_STAFFING_REPORT.value:
            return "Daily Staffing Report"
        return self.value


class PerformanceAndLearningReports(Enum):
    EMPLOYEE_PERFORMANCE_SUMMARY = "EMPLOYEE_PERFORMANCE_SUMMARY"

    def get_display_name(self):
        if (
            self.value
            == PerformanceAndLearningReports.EMPLOYEE_PERFORMANCE_SUMMARY.value
        ):
            return "Employee Performance Summary"
        return self.value


class PayrollReports(Enum):
    YEARLY_SALARY_EXPENSE = "YEARLY_SALARY_EXPENSE"
    EMPLOYEE_YEARLY_SALARY_SUMMARY = "EMPLOYEE_YEARLY_SALARY_SUMMARY"

    def get_display_name(self):
        if self.value == PayrollReports.YEARLY_SALARY_EXPENSE.value:
            return "Yearly Salary Expense"
        if self.value == PayrollReports.EMPLOYEE_YEARLY_SALARY_SUMMARY.value:
            return "Employee Yearly Salary Summary"
        return self.value


class LeaveReports(Enum):
    EMPLOYEE_LEAVE_SUMMARY = "EMPLOYEE_LEAVE_SUMMARY"

    def get_display_name(self):
        if self.value == LeaveReports.EMPLOYEE_LEAVE_SUMMARY.value:
            return "Employee Leave Summary"
        return self.value


class UsersReports(Enum):
    ALL_EMPLOYEES = "ALL_EMPLOYEES"
    EMPLOYEES_PER_DEPARTMENT = "EMPLOYEES_PER_DEPARTMENT"
    AGE = "AGE"
    GENDER = "GENDER"
    YEARS_OF_EXPERIENCE = "YEARS_OF_EXPERIENCE"
    EDUCATION_LEVEL = "EDUCATION_LEVEL"
    RELIGION = "RELIGION"

    def get_display_name(self):
        if self.value == UsersReports.ALL_EMPLOYEES.value:
            return "All Employees"
        if self.value == UsersReports.EMPLOYEES_PER_DEPARTMENT.value:
            return "Employees Per Department"
        if self.value == UsersReports.YEARS_OF_EXPERIENCE.value:
            return "Years of Experience"
        if self.value == UsersReports.EDUCATION_LEVEL.value:
            return "Education Level"
        return self.value
