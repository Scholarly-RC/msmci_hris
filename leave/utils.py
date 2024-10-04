from django.apps import apps
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth

from attendance.utils.date_utils import get_date_object
from hris.exceptions import RoleError
from leave.enums import LeaveRequestAction


def get_department_heads(selected_department):
    """ """
    user_details_model = apps.get_model("core", "UserDetails")
    department_head = user_details_model.Role.DEPARTMENT_HEAD.value

    return User.objects.filter(
        userdetails__department=selected_department,
        userdetails__role=department_head,
    )


def get_directors():
    """ """
    user_details_model = apps.get_model("core", "UserDetails")
    director = user_details_model.Role.DIRECTOR.value

    return User.objects.filter(userdetails__role=director)


def get_presidents():
    """ """
    user_details_model = apps.get_model("core", "UserDetails")
    president = user_details_model.Role.PRESIDENT.value

    return User.objects.filter(userdetails__role=president)


def get_approvers_per_department(selected_department) -> dict:
    approvers = selected_department.leave_approvers.first()
    if not approvers:
        return {}

    return {
        "department_approver": approvers.department_approver,
        "director_approver": approvers.director_approver,
        "president_approver": approvers.president_approver,
        "hr_approver": approvers.hr_approver,
    }


def get_approvers_per_user(user):
    department = user.userdetails.department
    role = user.userdetails.Role
    user_role = user.userdetails.role
    approvers = get_approvers_per_department(department)

    role_approvers = {
        role.EMPLOYEE.value: ["department_approver", "hr_approver"],
        role.DEPARTMENT_HEAD.value: ["director_approver", "hr_approver"],
        role.DIRECTOR.value: ["president_approver", "hr_approver"],
        role.PRESIDENT.value: ["hr_approver"],
    }

    if user_role in role_approvers:
        required_approvers = role_approvers[user_role]
        if any(not approvers[approver] for approver in required_approvers):
            missing_roles = [
                approver for approver in required_approvers if not approvers[approver]
            ]
            raise RoleError(
                f"Roles not set: {', '.join(missing_roles)} for {department} department."
            )

        return {
            "approver": approvers[required_approvers[0]].id,
            "status": LeaveRequestAction.PENDING.value,
        }, {
            "approver": approvers[required_approvers[1]].id,
            "status": LeaveRequestAction.PENDING.value,
        }

    return None


def get_leave_types():
    LeaveModel = apps.get_model("leave", "Leave")
    return LeaveModel.LeaveType.choices


def group_leave_by_month_and_year(leave):
    grouped_leaves = (
        leave.values(month=TruncMonth("date"))
        .annotate(leaves_count=Count("id"))
        .order_by("-month")
    )

    result = []
    for group in grouped_leaves:
        month_date = group["month"].strftime("%B %Y")  # Format the date as needed
        leaves_in_month = leave.filter(
            date__month=group["month"].month, date__year=group["month"].year
        )

        result.append({"date": month_date, "leave": list(leaves_in_month)})

    return result


def get_user_leave(user: User):
    leave = user.user_leaves.all()

    return group_leave_by_month_and_year(leave)


def get_leave_to_review(
    user, specific_user_id: int = "", month: int = "", year: int = ""
):
    LeaveModel = apps.get_model("leave", "Leave")

    leave = LeaveModel.objects.filter(
        Q(first_approver_data__approver=user.id)
        | Q(second_approver_data__approver=user.id)
    )

    if specific_user_id and specific_user_id != "0":
        leave = leave.filter(user__id=specific_user_id)

    if month and month != "0":
        leave = leave.filter(date__month=month)

    if year and year != "0":
        leave = leave.filter(date__year=year)

    grouped_leave = group_leave_by_month_and_year(leave)

    for leave_data in grouped_leave:
        new_leave_list = []
        for leave in leave_data["leave"]:
            new_leave_list.append([leave, leave.get_user_status(user)])

        leave_data["leave"] = new_leave_list

    return grouped_leave


def get_leave_year_list() -> list:
    LeaveModel = apps.get_model("leave", "Leave")

    leave_years = (
        LeaveModel.objects.values_list("date__year", flat=True)
        .order_by("date__year")
        .distinct()
    )

    return list(leave_years)


def check_user_has_approved_leave_on_specific_date(
    user, day: int, month: int, year: int
) -> bool:
    selected_date = get_date_object(year=year, month=month, day=day)
    approved_status = LeaveRequestAction.APPROVED.value

    return user.user_leaves.filter(
        Q(first_approver_data__status=approved_status)
        | Q(second_approver_data__status=approved_status),
        date=selected_date,
    )
