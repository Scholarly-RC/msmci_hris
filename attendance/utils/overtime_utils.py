from django.apps import apps
from django.db.models import Q


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
