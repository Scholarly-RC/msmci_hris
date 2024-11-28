import json
from collections import Counter

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models import Q

from attendance.enums import Months
from attendance.utils.date_utils import (
    get_date_object_from_date_str,
    get_readable_date_from_date_object,
)
from leave.utils import get_users_with_leave
from payroll.utils import get_payslip_year_list, get_users_with_payslip
from performance.utils import (
    get_finalized_user_evaluation_year_list,
    get_user_evaluation_users,
)
from reports_and_analytics.enums import (
    AttendanceReports,
    LeaveReports,
    Modules,
    PayrollReports,
    PerformanceAndLearningReports,
    UsersReports,
)


def get_list_of_modules(for_hr: bool = False):
    """
    Retrieves a list of module display names and their corresponding values, excluding the USERS module
    unless the `for_hr` parameter is set to True. This function returns a list of tuples, where each tuple
    contains the display name and value of a module from the `Modules` enumeration.
    """
    return [
        (module.get_display_name(), module.value)
        for module in Modules
        if for_hr or module.value != Modules.USERS.value
    ]


def get_reports_for_specific_module(module: str = "", for_hr: bool = False):
    """
    Retrieves reports for a specified module based on the provided module name.
    Depending on the module, it calls the appropriate report generation function,
    returning the relevant reports. If the module is not recognized, it returns an empty list.
    """
    if module == Modules.ATTENDANCE.value:
        return get_attendancee_reports(for_hr)
    if module == Modules.PERFORMANCE_AND_LEARNING.value:
        return get_performance_and_learning_reports()
    if module == Modules.PAYROLL.value:
        return get_payroll_reports(for_hr=for_hr)
    if module == Modules.LEAVE.value:
        return get_leave_reports()
    if module == Modules.USERS.value:
        return get_users_reports()
    return []


def get_filter_contexts_for_specific_report(
    report: str = "", for_hr: bool = False
) -> dict:
    """
    Retrieves filter contexts for a specified report type. Depending on the report,
    it constructs a context dictionary that may include user lists and year selections.
    The function checks the report type and, if applicable, adds relevant data based
    on the `for_hr` flag. If the report is not recognized, it returns an empty dictionary.
    """
    if report == PerformanceAndLearningReports.EMPLOYEE_PERFORMANCE_SUMMARY.value:
        context = {"years": get_finalized_user_evaluation_year_list()}
        if for_hr:
            context["users"] = get_user_evaluation_users()
        return context
    if report == PayrollReports.YEARLY_SALARY_EXPENSE.value:
        return {"years": get_payslip_year_list()}
    if report == PayrollReports.EMPLOYEE_YEARLY_SALARY_SUMMARY.value:
        context = {"years": get_payslip_year_list()}
        if for_hr:
            context["users"] = get_users_with_payslip()
        return context
    if report == LeaveReports.EMPLOYEE_LEAVE_SUMMARY.value:
        context = {}
        if for_hr:
            context["users"] = get_users_with_leave()
        return context
    return {}


### Attendance Report Utils ###
def get_attendancee_reports(for_hr: bool = False):
    """
    Retrieves a list of attendance reports, returning tuples containing the report value
    and its display name.
    """
    return [
        (
            attendance_report.value,
            attendance_report.get_display_name(),
        )
        for attendance_report in AttendanceReports
        if for_hr
        or attendance_report.value != AttendanceReports.DAILY_STAFFING_REPORT.value
    ]


def get_daily_staffing_report_data(selected_date_str):
    """
    Retrieves the staffing report data for a given date, including department-wise shift data
    and individual schedules for that date.
    """
    DailyShiftScheduleModel = apps.get_model("attendance", "DailyShiftSchedule")
    DepartmentModel = apps.get_model("core", "Department")
    selected_date = get_date_object_from_date_str(date_str=selected_date_str)
    schedules = DailyShiftScheduleModel.objects.filter(
        date=selected_date, daily_shift_records__isnull=False
    ).order_by("user__first_name", "user__userdetails__department__name")

    department_list = []
    department_count_list = []

    department_with_records = DepartmentModel.objects.filter(
        daily_shift_records__isnull=False, daily_shift_records__date=selected_date
    )

    for department in department_with_records:
        department_list.append(department.name.title())
        department_count_list.append(
            department.daily_shift_records.filter(date=selected_date)
            .first()
            .shifts.count()
        )

    schedules_data = {
        "department_list": department_list,
        "department_count_list": department_count_list,
    }

    schedules_table_data = {"schedules": schedules}

    return {
        "chart_option_data": json.dumps(schedules_data),
        "schedules_table_data": schedules_table_data,
        "selected_date": selected_date_str,
    }


### Performance and Learning Report Utils ###
def get_performance_and_learning_reports(for_hr: bool = False):
    """
    Retrieves a list of performance and learning reports, returning tuples that
    include the report value and its display name.
    """
    return [
        (
            performance_and_learning_report.value,
            performance_and_learning_report.get_display_name(),
        )
        for performance_and_learning_report in PerformanceAndLearningReports
    ]


def get_employee_performance_evaluation_summary_data(selected_year, selected_user):
    """
    Generates a summary of an employee's performance evaluations for a specific year.
    It retrieves the user's evaluations, calculates self and peer ratings for each quarter,
    and returns a dictionary containing the ratings data, quarter labels, and selected user information
    for reporting purposes.
    """
    UserModel = get_user_model()
    UserEvaluationModel = apps.get_model("performance", "UserEvaluation")

    user = UserModel.objects.get(id=selected_user)
    user_evaluations = user.evaluatee_evaluations.filter(
        Q(year=selected_year) & Q(is_finalized=True)
    ).order_by("quarter")

    quarters_list = [quarter[0] for quarter in UserEvaluationModel.Quarter.choices]

    self_rating_value_list = []
    peer_rating_value_list = []
    for quarter in quarters_list:
        user_evaluation = user_evaluations.filter(quarter=quarter).first()
        if user_evaluation:
            self_rating, peer_rating = (
                user_evaluation.get_overall_self_and_peer_rating_mean()
            )
            self_rating_value_list.append(round(self_rating, 2))
            peer_rating_value_list.append(round(peer_rating, 2))
        else:
            self_rating_value_list.append(0)
            peer_rating_value_list.append(0)

    employee_performance_evaluation_data = {
        "quarters_list": quarters_list,
        "self_rating_value_list": self_rating_value_list,
        "peer_rating_value_list": peer_rating_value_list,
    }

    employee_performance_evaluation_table_data = [
        ("First Quarter", self_rating_value_list[0], peer_rating_value_list[0]),
        ("Second Quarter", self_rating_value_list[1], peer_rating_value_list[1]),
    ]

    return {
        "chart_option_data": json.dumps(employee_performance_evaluation_data),
        "employee_performance_evaluation_table_data": employee_performance_evaluation_table_data,
        "selected_year": selected_year,
        "selected_user": user,
    }


### Payroll Report Utils ###
def get_payroll_reports(for_hr: bool = False):
    """
    Retrieves a list of payroll reports, returning tuples that include each report's value
    and display name. If the `for_hr` parameter is set to False, the YEARLY_SALARY_EXPENSE
    report is excluded from the output.
    """
    return [
        (payroll_report.value, payroll_report.get_display_name())
        for payroll_report in PayrollReports
        if for_hr or payroll_report.value != PayrollReports.YEARLY_SALARY_EXPENSE.value
    ]


def get_yearly_salary_expense_report_data(selected_year):
    """
    Computes and retrieves the total net salary expenses for each month of a specified year.
    It aggregates net salaries from released payslips, constructs a data dictionary with
    monthly totals and overall expenses, and returns the data formatted for reporting purposes.
    """

    def _get_total_net_income(months, payslips):
        total_amount = 0
        total_list = []
        for month in months:
            total = 0
            for payslip in payslips.filter(month=month):
                net_salary = payslip.get_data().get("net_salary")
                total += net_salary
            total_amount += total
            total_list.append(str(round(total, 2)))
        return total_list, round(total_amount, 2)

    PayslipModel = apps.get_model("payroll", "Payslip")
    payslips = PayslipModel.objects.filter(released=True, year=selected_year).order_by(
        "month"
    )
    months_value = payslips.values_list("month", flat=True).distinct()
    months_name = [Months(month).name[:3].title() for month in months_value]

    total_per_month_list, total_expenses = _get_total_net_income(months_value, payslips)

    yearly_salary_expense_data = {
        "months": months_name,
        "total_amounts": total_per_month_list,
    }

    yearly_salary_expense_table_data = []

    for month_count in range(months_value.count()):
        yearly_salary_expense_table_data.append(
            (
                Months(months_value[month_count]).name.title(),
                total_per_month_list[month_count],
            )
        )

    return {
        "chart_option_data": json.dumps(yearly_salary_expense_data),
        "yearly_salary_expense_table_data": yearly_salary_expense_table_data,
        "total_expenses": total_expenses,
        "selected_year": selected_year,
    }


def get_employee_yearly_salary_salary_report_data(selected_year, selected_user):
    """
    Retrieves and calculates the yearly salary data for a specific employee.
    It aggregates net salaries from the user's payslips for the selected year,
    constructs a data dictionary with monthly totals, and returns the data
    formatted for reporting, including total salary and month-wise breakdown.
    """
    UserModel = get_user_model()
    user = UserModel.objects.get(id=selected_user)
    payslips = user.payslips.filter(year=selected_year, released=True)

    months = payslips.values_list("month", flat=True).distinct()

    months_list = [Months(month).name[:3].title() for month in months]

    total_amount = []

    for month in months:
        amount = 0
        for payslip in payslips.filter(month=month):
            amount += payslip.get_data().get("net_salary")
        total_amount.append(round(amount, 2))

    total_amount_list = [str(amount) for amount in total_amount]

    total_salary = str(round(sum(total_amount), 2))

    employee_yearly_salary_expense_data = {
        "months": months_list,
        "total_amount_list": total_amount_list,
    }

    employee_yearly_salary_expense_table_data = []
    for month_count in range(months.count()):
        employee_yearly_salary_expense_table_data.append(
            (
                Months(months[month_count]).name.title(),
                total_amount_list[month_count],
            )
        )

    return {
        "chart_option_data": json.dumps(employee_yearly_salary_expense_data),
        "employee_yearly_salary_expense_table_data": employee_yearly_salary_expense_table_data,
        "total_salary": total_salary,
        "selected_year": selected_year,
        "selected_user": user,
    }


### Leave Report Utils ###
def get_leave_reports(for_hr: bool = False):
    """
    Retrieves a list of leave reports, returning tuples that include each report's value
    and display name.
    """
    return [
        (leave_report.value, leave_report.get_display_name())
        for leave_report in LeaveReports
    ]


def get_employee_leave_summary_report_data(selected_user, from_date, to_date):
    """
    Generates a summary of an employee's leave records within a specified date range.
    It retrieves leave data, categorizes it into paid, unpaid, and work-related trip types,
    and returns a structured dictionary containing chart data and detailed leave records for reporting.
    """
    UserModel = get_user_model()
    LeaveModel = apps.get_model("leave", "Leave")

    paid_type = LeaveModel.LeaveType.PAID.value
    unpaid_type = LeaveModel.LeaveType.UNPAID.value
    work_related_trip_type = LeaveModel.LeaveType.WORK_RELATED_TRIP.value

    user = UserModel.objects.get(id=selected_user)
    from_date = get_date_object_from_date_str(from_date)
    to_date = get_date_object_from_date_str(to_date)

    leaves = user.user_leaves.filter(date__gte=from_date, date__lte=to_date).order_by(
        "date"
    )

    employee_leave_data_list = [
        {"x": "Paid", "y": leaves.filter(type=paid_type).count()},
        {"x": "Unpaid", "y": leaves.filter(type=unpaid_type).count()},
        {
            "x": "Work Related Trip",
            "y": leaves.filter(type=work_related_trip_type).count(),
        },
    ]

    employee_leave_table_data = leaves

    return {
        "chart_option_data": json.dumps({"leave_data_list": employee_leave_data_list}),
        "employee_leave_table_data": employee_leave_table_data,
        "from_date_display": get_readable_date_from_date_object(from_date),
        "to_date_display": get_readable_date_from_date_object(to_date),
        "from_date": str(from_date),
        "to_date": str(to_date),
        "selected_user": user,
    }


### User Report Utils ###
def get_users_reports():
    """
    Retrieves a list of user reports, returning tuples that include each report's value
    and display name. This function provides a straightforward way to access available
    user report options.
    """
    return [
        (users_report.value, users_report.get_display_name())
        for users_report in UsersReports
    ]


def get_all_employees_report_data(as_of_date=""):
    """
    Retrieves a report of all active employees, excluding superusers, and who were hired on or before
    the specified `as_of_date`. The report includes the list of employee names and a table of user data.
    """
    as_of_date = get_date_object_from_date_str(as_of_date)
    UserModel = get_user_model()
    users = (
        UserModel.objects.filter(
            is_active=True,
            is_superuser=False,
            userdetails__date_of_hiring__lte=as_of_date,
        )
        .exclude(
            Q(first_name__isnull=True)
            | Q(first_name="")
            | Q(last_name__isnull=True)
            | Q(last_name="")
        )
        .order_by("first_name")
    )

    user_list = [user.userdetails.get_user_fullname() for user in users]

    users_table_data = {"users": users}

    return {
        "chart_option_data": json.dumps(user_list),
        "users_table_data": users_table_data,
        "as_of_date": str(as_of_date),
    }


def get_employees_per_department_report_data(as_of_date=""):
    """
    Retrieves a report of employees grouped by department, including the department names and the number
    of employees in each department, as of the specified `as_of_date`.
    """
    as_of_date = get_date_object_from_date_str(as_of_date)
    DepartmentModel = apps.get_model("core", "Department")

    department_list = []
    department_count_list = []

    departments = DepartmentModel.objects.all().order_by("name")

    for department in departments:
        department_list.append(department.name.title())
        department_count_list.append(department.users.count())

    departments_data = {
        "department_list": department_list,
        "department_count_list": department_count_list,
    }

    departments_table_data = {"departments": departments}

    return {
        "chart_option_data": json.dumps(departments_data),
        "departments_table_data": departments_table_data,
        "as_of_date": str(as_of_date),
    }


def get_age_demographics_report_data(as_of_date=""):
    """
    Generates age demographics data for active users as of a specified date.
    It calculates the age of each user, categorizes them into defined age groups,
    and returns a structured dictionary containing the age group counts and user details
    for reporting purposes.
    """
    as_of_date = get_date_object_from_date_str(as_of_date)

    def _age_group_counter(age_list):
        age_groups_counts = Counter()

        for age in age_list:
            if 18 <= age <= 24:
                age_groups_counts["18-24"] += 1
            elif 25 <= age <= 39:
                age_groups_counts["25-39"] += 1
            elif 40 <= age <= 54:
                age_groups_counts["40-54"] += 1
            elif 55 <= age <= 64:
                age_groups_counts["55-64"] += 1
            elif age >= 65:
                age_groups_counts["65-Up"] += 1

        return [count for _, count in age_groups_counts.items()]

    UserDetailsModel = apps.get_model("core", "UserDetails")
    age_list = []
    users = (
        UserDetailsModel.objects.exclude(date_of_birth__isnull=True)
        .filter(
            user__is_active=True,
            date_of_birth__isnull=False,
            date_of_hiring__lte=as_of_date,
        )
        .order_by("-date_of_birth")
    )
    for userdetail in users:
        age = (
            as_of_date.year
            - userdetail.date_of_birth.year
            - (
                (as_of_date.month, as_of_date.day)
                < (userdetail.date_of_birth.month, userdetail.date_of_birth.day)
            )
        )

        age_list.append(age)

    age_groups = ["18-24", "25-39", "40-54", "55-64", "65-Up"]
    age_group_count = _age_group_counter(age_list)

    age_demographic_data = {
        "age_groups": age_groups,
        "age_group_count": age_group_count,
    }

    age_demographic_table_data = [
        {"user": users[i], "age": age_list[i]} for i in range(users.count())
    ]

    return {
        "chart_option_data": json.dumps(age_demographic_data),
        "age_demographic_table_data": age_demographic_table_data,
        "as_of_date": str(as_of_date),
    }


def get_gender_demographics_report_data(as_of_date=""):
    """
    Generates gender demographics data for active users as of a specified date.
    It counts the number of male and female users, returning a structured dictionary
    containing gender counts and details for reporting purposes.
    """
    as_of_date = get_date_object_from_date_str(as_of_date)
    UserDetailsModel = apps.get_model("core", "UserDetails")

    user_details_list = UserDetailsModel.objects.exclude(gender__isnull=True).filter(
        user__is_active=True, date_of_hiring__lte=as_of_date
    )

    male_gender = UserDetailsModel.Gender.MALE.value
    female_gender = UserDetailsModel.Gender.FEMALE.value

    male_count = user_details_list.filter(gender=male_gender).count()
    female_count = user_details_list.filter(gender=female_gender).count()
    total_count = user_details_list.count()

    gender_group = ["Male", "Female"]
    gender_group_count = [male_count, female_count]

    gender_demographic_data = {
        "gender_group": gender_group,
        "gender_group_count": gender_group_count,
    }

    gender_demographic_table_data = {
        "male_count": male_count,
        "female_count": female_count,
    }

    return {
        "chart_option_data": json.dumps(gender_demographic_data),
        "gender_demographic_table_data": gender_demographic_table_data,
        "as_of_date": str(as_of_date),
    }


def get_years_of_experience_report_data(as_of_date=""):
    """
    Generates a report on years of experience for active users as of a specified date.
    It calculates the number of years each user has been employed, compiles this data into
    groups, and returns a structured dictionary containing the experience counts and
    average years of experience for reporting purposes.
    """
    as_of_date = get_date_object_from_date_str(as_of_date)
    UserDetailsModel = apps.get_model("core", "UserDetails")

    user_details_list = (
        UserDetailsModel.objects.exclude(date_of_hiring__isnull=True)
        .filter(user__is_active=True, date_of_hiring__lte=as_of_date)
        .order_by("date_of_hiring")
    )

    years_of_experience_list = []
    for user_detail in user_details_list:
        years_of_experience = as_of_date.year - user_detail.date_of_hiring.year
        years_of_experience_list.append(years_of_experience)

    years_of_experience_group_list = sorted(set(years_of_experience_list))
    years_of_experience_count_group_list = [
        years_of_experience_list.count(num) for num in years_of_experience_group_list
    ]
    years_of_experience_average = (
        (sum(years_of_experience_list) / len(years_of_experience_list))
        if years_of_experience_list
        else 0
    )

    years_of_expernce_data = {
        "years_of_experience_group_list": years_of_experience_group_list,
        "years_of_experience_count_group_list": years_of_experience_count_group_list,
    }

    years_of_expernce_table_data = {"users": user_details_list}

    return {
        "chart_option_data": json.dumps(years_of_expernce_data),
        "years_of_expernce_table_data": years_of_expernce_table_data,
        "years_of_experience_average": round(years_of_experience_average, 2),
        "as_of_date": str(as_of_date),
    }


def get_education_level_report_data(as_of_date=""):
    """
    Generates a report on the educational levels of active users as of a specified date.
    It collects data on users' educational attainment, counts the number of users in each
    educational category, and returns a structured dictionary containing this information
    for reporting purposes.
    """
    as_of_date = get_date_object_from_date_str(as_of_date)
    UserDetailsModel = apps.get_model("core", "UserDetails")
    EducationalAttainment = UserDetailsModel.EducationalAttainment

    user_details_list = UserDetailsModel.objects.exclude(
        Q(education__isnull=True) | Q(education="")
    ).filter(user__is_active=True, date_of_hiring__lte=as_of_date)

    education_attainment_list = (
        user_details_list.values_list("education", flat=True)
        .order_by("-education")
        .distinct()
    )

    total = user_details_list.count()

    education_attainment_count_list = [
        user_details_list.filter(education=education).count()
        for education in education_attainment_list
    ]

    education_attainment_list = [
        str(EducationalAttainment(code).label) for code in education_attainment_list
    ]

    education_level_data = {
        "education_attainment_list": list(education_attainment_list),
        "education_attainment_count_list": list(education_attainment_count_list),
    }

    education_level_table_data = []

    for education_count in range(len(education_attainment_list)):
        education_level_table_data.append(
            (
                education_attainment_list[education_count],
                education_attainment_count_list[education_count],
            )
        )

    return {
        "chart_option_data": json.dumps(education_level_data),
        "education_level_table_data": education_level_table_data,
        "as_of_date": str(as_of_date),
    }


def get_religion_report_data(as_of_date=""):
    """
    Generates a report on the religious affiliations of active users as of a specified date.
    It collects data on users' religions, counts the number of users in each category,
    and returns a structured dictionary containing this information for reporting purposes.
    """
    as_of_date = get_date_object_from_date_str(as_of_date)
    UserDetailsModel = apps.get_model("core", "UserDetails")
    Religion = UserDetailsModel.Religion

    user_details_list = UserDetailsModel.objects.exclude(
        Q(religion__isnull=True) | Q(religion="")
    ).filter(user__is_active=True, date_of_hiring__lte=as_of_date)

    religion_list = (
        user_details_list.values_list("religion", flat=True)
        .order_by("religion")
        .distinct()
    )

    religion_count_list = [
        user_details_list.filter(religion=religion).count()
        for religion in religion_list
    ]

    religion_list = [str(Religion(code).label) for code in religion_list]

    religion_data = {
        "education_attainment_list": list(religion_list),
        "education_attainment_count_list": list(religion_count_list),
    }

    religion_data_table_data = []

    for religion_count in range(len(religion_list)):
        religion_data_table_data.append(
            (
                religion_list[religion_count],
                religion_count_list[religion_count],
            )
        )

    return {
        "chart_option_data": json.dumps(religion_data),
        "religion_data_table_data": religion_data_table_data,
        "as_of_date": str(as_of_date),
    }
