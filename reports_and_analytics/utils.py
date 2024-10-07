import json
from collections import Counter
from datetime import datetime
from decimal import Decimal

from django.apps import apps
from django.db.models import Q
from django.utils.timezone import make_aware

from attendance.enums import Months
from attendance.utils.attendance_utils import (
    get_employees_with_attendance_record,
    get_user_clocked_time,
    get_user_daily_shift_record_shifts,
)
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
    return [
        (module.get_display_name(), module.value)
        for module in Modules
        if for_hr or module.value != Modules.USERS.value
    ]


def get_reports_for_specific_module(module: str = "", for_hr: bool = False):
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
    if report == AttendanceReports.EMPLOYEE_PUNCTUALITY_RATE.value:
        context = {}
        if for_hr:
            context["users"] = get_employees_with_attendance_record()
        return context
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
    return [
        (
            attendance_report.value,
            attendance_report.get_display_name(),
        )
        for attendance_report in AttendanceReports
    ]


def get_employee_punctuality_report_data(selected_user, from_date, to_date):
    UserModel = apps.get_model("auth", "User")
    AttendanceRecordModel = apps.get_model("attendance", "AttendanceRecord")
    in_punch = AttendanceRecordModel.Punch.TIME_IN.value
    user = UserModel.objects.get(id=selected_user)
    from_date = get_date_object_from_date_str(from_date)
    to_date = get_date_object_from_date_str(to_date)
    attendance_records = user.biometricdetail.attendance_records.filter(
        Q(timestamp__gte=from_date) & Q(timestamp__lte=to_date) & Q(punch=in_punch)
    )
    on_time_or_early = 0
    late = 0
    for attendance_record in attendance_records:
        timestamp = attendance_record.get_timestamp_localtime()
        daily_shift = get_user_daily_shift_record_shifts(
            user,
            timestamp.year,
            timestamp.month,
            timestamp.day,
        )

        if daily_shift:
            clocked_time = get_user_clocked_time(
                user,
                timestamp.year,
                timestamp.month,
                timestamp.day,
                daily_shift.shift if daily_shift else None,
            )
            if "-" in clocked_time["clock_in_time_diff_formatted"]:
                late += 1
            else:
                on_time_or_early += 1
    attendance_status = ["On Time / Early", "Late"]
    attendance_values = [on_time_or_early, late]

    return {
        "chart_option_data": json.dumps(
            {
                "attendance_status": attendance_status,
                "attendance_values": attendance_values,
            }
        ),
        "from_date": str(from_date),
        "to_date": str(to_date),
        "from_date_display": get_readable_date_from_date_object(from_date),
        "to_date_display": get_readable_date_from_date_object(to_date),
        "selected_user": user,
    }


### Performance and Learning Report Utils ###
def get_performance_and_learning_reports(for_hr: bool = False):
    return [
        (
            performance_and_learning_report.value,
            performance_and_learning_report.get_display_name(),
        )
        for performance_and_learning_report in PerformanceAndLearningReports
    ]


def get_employee_performance_evaluation_summary_data(selected_year, selected_user):
    UserModel = apps.get_model("auth", "User")
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

    return {
        "chart_option_data": json.dumps(
            {
                "quarters_list": quarters_list,
                "self_rating_value_list": self_rating_value_list,
                "peer_rating_value_list": peer_rating_value_list,
            }
        ),
        "selected_year": selected_year,
        "selected_user": user,
    }


### Payroll Report Utils ###
def get_payroll_reports(for_hr: bool = False):
    return [
        (payroll_report.value, payroll_report.get_display_name())
        for payroll_report in PayrollReports
        if for_hr or payroll_report.value != PayrollReports.YEARLY_SALARY_EXPENSE.value
    ]


def get_yearly_salary_expense_report_data(selected_year):
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

    return {
        "chart_option_data": json.dumps(
            {"months": months_name, "total_amounts": total_per_month_list}
        ),
        "total_expenses": total_expenses,
        "selected_year": selected_year,
    }


def get_employee_yearly_salary_salary_report_data(selected_year, selected_user):
    UserModel = apps.get_model("auth", "User")
    user = UserModel.objects.get(id=selected_user)
    payslips = user.payslips.filter(year=selected_year)

    months = payslips.values_list("month", flat=True)

    months_list = [Months(month).name[:3].title() for month in months]

    total_amount = []

    for month in months:
        amount = 0
        for payslip in payslips.filter(month=month):
            amount += payslip.get_data().get("net_salary")
        total_amount.append(round(amount, 2))

    total_amount_list = [str(amount) for amount in total_amount]

    total_salary = str(round(sum(total_amount)))

    return {
        "chart_option_data": json.dumps(
            {"months": months_list, "total_amount_list": total_amount_list}
        ),
        "total_salary": total_salary,
        "selected_year": selected_year,
        "selected_user": user,
    }


### Leave Report Utils ###
def get_leave_reports(for_hr: bool = False):
    return [
        (leave_report.value, leave_report.get_display_name())
        for leave_report in LeaveReports
    ]


def get_employee_leave_summary_report_data(selected_user, from_date, to_date):
    UserModel = apps.get_model("auth", "User")
    LeaveModel = apps.get_model("leave", "Leave")

    paid_type = LeaveModel.LeaveType.PAID.value
    unpaid_type = LeaveModel.LeaveType.UNPAID.value
    work_related_trip_type = LeaveModel.LeaveType.WORK_RELATED_TRIP.value

    user = UserModel.objects.get(id=selected_user)
    from_date = get_date_object_from_date_str(from_date)
    to_date = get_date_object_from_date_str(to_date)

    leaves = user.user_leaves.filter(date__gte=from_date, date__lte=to_date)

    leave_data_list = [
        {"x": "Paid", "y": leaves.filter(type=paid_type).count()},
        {"x": "Unpaid", "y": leaves.filter(type=unpaid_type).count()},
        {
            "x": "Work Related Trip",
            "y": leaves.filter(type=work_related_trip_type).count(),
        },
    ]
    return {
        "chart_option_data": json.dumps({"leave_data_list": leave_data_list}),
        "from_date_display": get_readable_date_from_date_object(from_date),
        "to_date_display": get_readable_date_from_date_object(to_date),
        "from_date": str(from_date),
        "to_date": str(to_date),
        "selected_user": user,
    }


### User Report Utils ###
def get_users_reports():
    return [
        (users_report.value, users_report.get_display_name())
        for users_report in UsersReports
    ]


def get_age_demographics_report_data(as_of_date=""):
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
    for userdetail in UserDetailsModel.objects.exclude(
        date_of_birth__isnull=True
    ).filter(user__is_active=True, date_of_hiring__lte=as_of_date):
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

    return {
        "chart_option_data": json.dumps(
            {"age_groups": age_groups, "age_group_count": age_group_count}
        ),
        "as_of_date": str(as_of_date),
    }


def get_gender_demographics_report_data(as_of_date=""):
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

    return {
        "chart_option_data": json.dumps(
            {
                "gender_group": gender_group,
                "gender_group_count": gender_group_count,
            }
        ),
        "as_of_date": str(as_of_date),
    }


def get_years_of_experience_report_data(as_of_date=""):
    as_of_date = get_date_object_from_date_str(as_of_date)
    UserDetailsModel = apps.get_model("core", "UserDetails")

    user_details_list = UserDetailsModel.objects.exclude(
        date_of_hiring__isnull=True
    ).filter(user__is_active=True, date_of_hiring__lte=as_of_date)

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

    return {
        "chart_option_data": json.dumps(
            {
                "years_of_experience_group_list": years_of_experience_group_list,
                "years_of_experience_count_group_list": years_of_experience_count_group_list,
            }
        ),
        "years_of_experience_average": round(years_of_experience_average, 2),
        "as_of_date": str(as_of_date),
    }


def get_education_level_report_data(as_of_date=""):
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

    return {
        "chart_option_data": json.dumps(
            {
                "education_attainment_list": list(education_attainment_list),
                "education_attainment_count_list": list(
                    education_attainment_count_list
                ),
            }
        ),
        "as_of_date": str(as_of_date),
    }
