from django.apps import apps
from django.db.models import Q
from django.http import QueryDict

from attendance.utils.date_utils import get_date_object


def get_user_overtime_approver(user):
    """
    Retrieves the appropriate overtime approvers based on the user's role.
    The approvers are returned based on a hierarchy:
    Employee → Department Head → Director → President → HR.
    If no approver exists, an empty queryset is returned.
    """
    UserModel = apps.get_model("auth", "User")
    UserDetailsModel = apps.get_model("core", "UserDetails")

    roles = UserDetailsModel.Role

    user_role = user.userdetails.role
    if user_role == roles.EMPLOYEE.value:
        department = user.userdetails.department
        approvers = UserModel.objects.filter(
            Q(is_active=True),
            Q(userdetails__department=department),
            Q(userdetails__role=roles.DEPARTMENT_HEAD.value),
        )
        return approvers

    if user_role == roles.DEPARTMENT_HEAD.value:
        approvers = UserModel.objects.filter(
            Q(is_active=True),
            Q(userdetails__role=roles.DIRECTOR.value),
        )
        return approvers

    if user_role == roles.DIRECTOR.value:
        approvers = UserModel.objects.filter(
            Q(is_active=True),
            Q(userdetails__role=roles.PRESIDENT.value),
        )
        return approvers

    if user_role == roles.PRESIDENT.value:
        approvers = UserModel.objects.filter(
            Q(is_active=True),
            Q(userdetails__role=roles.HR.value),
        )
        return approvers

    return UserModel.objects.none()


def get_user_overtime_requests(user):
    """
    Retrieves all overtime requests for the given user, ordered by date in descending order.
    """
    return user.overtime_requests.all().order_by("-date")


def get_user_overtime_requests_to_approve(user):
    """
    Retrieves all overtime requests that are pending approval for the given user, ordered by date in descending order.
    """
    return user.approved_overtimes.all().order_by("-date")


def get_overtime_requests_year_list(overtime_requests):
    """
    Returns a list of distinct years from the given overtime requests, ordered by year in descending order.
    """
    overtime_requests = (
        overtime_requests.values_list("date__year", flat=True)
        .order_by("-date__year")
        .distinct()
    )

    return list(overtime_requests)


def get_all_overtime_request(filter_data: QueryDict = {}):
    """
    Retrieves a queryset of overtime requests, optionally filtered by user, year, department, status, and approver.
    Returns the filtered list of overtime requests, ordered by date in descending order.
    """
    OvertimeModel = apps.get_model("attendance", "Overtime")
    overtime_requests = OvertimeModel.objects.select_related(
        "user__userdetails__department",
        "approver__userdetails__department",
    ).order_by("-date")

    if not filter_data:
        return overtime_requests

    user_search = filter_data.get("user_search")
    selected_year = filter_data.get("selected_year")
    selected_department = filter_data.get("selected_department")
    selected_status = filter_data.get("selected_status")
    selected_approver = filter_data.get("selected_approver")

    if user_search:
        user_search_filter = (
            Q(user__first_name__icontains=user_search)
            | Q(user__last_name__icontains=user_search)
            | Q(user__userdetails__middle_name__icontains=user_search)
            | Q(user__email__icontains=user_search)
        )
        overtime_requests = overtime_requests.filter(user_search_filter)

    if selected_year and selected_year != "0":
        overtime_requests = overtime_requests.filter(Q(date__year=selected_year))

    if selected_department and selected_department != "0":
        overtime_requests = overtime_requests.filter(
            Q(user__userdetails__department_id=selected_department)
        )

    if selected_status and selected_status != "0":
        overtime_requests = overtime_requests.filter(Q(status=selected_status))

    if selected_approver and selected_approver != "0":
        overtime_requests = overtime_requests.filter(Q(approver_id=selected_approver))

    return overtime_requests


def get_overtime_request_status_list():
    """
    Returns a list of possible overtime request status choices.
    """
    OvertimeModel = apps.get_model("attendance", "Overtime")
    return OvertimeModel.Status.choices


def get_overtime_request_approvers():
    """
    Returns a queryset of users who are eligible to approve overtime requests (i.e., have approved overtime).
    """
    UserModel = apps.get_model("auth", "User")
    return UserModel.objects.select_related("userdetails").exclude(
        approved_overtimes__isnull=True
    )


def check_user_has_approved_overtime_on_specific_date_range(
    user, day_range, month: int, year: int
):
    """
    Checks if the user has approved overtime for each day in the specified date range.
    Returns a dictionary with the day as the key and a boolean indicating approval status as the value.
    """
    selected_dates = [
        get_date_object(year=year, month=month, day=day) for day in day_range
    ]

    OvertimeModel = apps.get_model("attendance", "Overtime")
    approved_status = OvertimeModel.Status.APPROVED.value

    overtime_queryset = user.overtime_requests.filter(
        date__in=selected_dates, status=approved_status
    )

    approved_overtime_data = {day: False for day in day_range}

    for overtime in overtime_queryset:
        overtime_day = overtime.date.day
        if overtime_day in approved_overtime_data:
            approved_overtime_data[overtime_day] = True

    return approved_overtime_data
