from django.apps import apps
from django.db.models import Q
from django.http import QueryDict

from attendance.utils.date_utils import get_date_object


def get_user_overtime_approver(user):
    UserModel = apps.get_model("auth", "User")
    UserDetailsModel = apps.get_model("core", "UserDetails")

    roles = UserDetailsModel.Role

    user_role = user.userdetails.role
    if user_role == roles.EMPLOYEE.value:
        department = user.userdetails.department
        approvers = UserModel.objects.filter(
            Q(userdetails__department=department),
            Q(userdetails__role=roles.DEPARTMENT_HEAD.value),
        )
        return approvers

    if user_role == roles.DEPARTMENT_HEAD.value:
        approvers = UserModel.objects.filter(
            Q(userdetails__role=roles.DIRECTOR.value),
        )
        return approvers

    if user_role == roles.DIRECTOR.value:
        approvers = UserModel.objects.filter(
            Q(userdetails__role=roles.PRESIDENT.value),
        )
        return approvers

    if user_role == roles.PRESIDENT.value:
        approvers = UserModel.objects.filter(
            Q(userdetails__role=roles.HR.value),
        )
        return approvers

    return UserModel.objects.none()


def get_user_overtime_requests(user):
    return user.overtime_requests.all().order_by("-date")


def get_user_overtime_requests_to_approve(user):
    return user.approved_overtimes.all().order_by("-date")


def get_overtime_requests_year_list(overtime_requests):
    overtime_requests = (
        overtime_requests.values_list("date__year", flat=True)
        .order_by("-date__year")
        .distinct()
    )

    return list(overtime_requests)


def get_all_overtime_request(filter_data: QueryDict = {}):
    OvertimeModel = apps.get_model("attendance", "Overtime")
    overtime_requests = OvertimeModel.objects.order_by("-date")

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
    OvertimeModel = apps.get_model("attendance", "Overtime")
    return OvertimeModel.Status.choices


def get_overtime_request_approvers():
    UserModel = apps.get_model("auth", "User")
    return UserModel.objects.exclude(approved_overtimes__isnull=True)


def check_user_has_approved_overtime_on_specific_date(
    user, day: int, month: int, year: int
) -> bool:
    OvertimeModel = apps.get_model("attendance", "Overtime")
    approved_status = OvertimeModel.Status.APPROVED.value

    selected_date = get_date_object(year=year, month=month, day=day)
    return user.overtime_requests.filter(
        date=selected_date, status=approved_status
    ).exists()
