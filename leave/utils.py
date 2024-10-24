from django.apps import apps
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth

from attendance.utils.date_utils import get_date_object
from hris.exceptions import RoleError
from leave.enums import LeaveRequestAction


def get_department_heads(selected_department):
    """
    Retrieves a list of users who are designated as department heads for the specified department.
    It filters users based on their role and department affiliation.
    """
    UserDetailsModel = apps.get_model("core", "UserDetails")
    department_head = UserDetailsModel.Role.DEPARTMENT_HEAD.value

    return User.objects.filter(
        userdetails__department=selected_department,
        userdetails__role=department_head,
    )


def get_directors():
    """
    Retrieves a list of users who hold the role of director.
    It filters users based on their role affiliation within the user details model.
    """
    UserDetailsModel = apps.get_model("core", "UserDetails")
    director = UserDetailsModel.Role.DIRECTOR.value

    return User.objects.filter(userdetails__role=director)


def get_presidents():
    """
    Retrieves a list of users who hold the role of president.
    It filters users based on their role affiliation within the user details model.
    """
    UserDetailsModel = apps.get_model("core", "UserDetails")
    president = UserDetailsModel.Role.PRESIDENT.value

    return User.objects.filter(userdetails__role=president)


def get_approvers_per_department(selected_department) -> dict:
    """
    Retrieves the approvers for a specified department's leave requests.
    It returns a dictionary containing the department approver, director approver,
    president approver, and HR approver. If no approvers are found, an empty dictionary is returned.
    """
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
    """
    Retrieves the appropriate leave approvers for a given user based on their department
    and role. It checks the user's role against defined approver roles and raises an error
    if any required approvers are missing. Returns a dictionary containing the approver IDs
    and their status for the user's leave request. If no approvers are found for the role,
    it returns None.
    """
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
    """
    Retrieves the available leave types from the Leave model.
    It returns a list of choices that represent the different types of leave defined in the system.
    """
    LeaveModel = apps.get_model("leave", "Leave")
    return LeaveModel.LeaveType.choices


def group_leave_by_month_and_year(leave):
    """
    Groups leave records by month and year, counting the number of leaves for each
    month. It returns a list of dictionaries, each containing the formatted month/year
    and the corresponding leave records for that period.
    """
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
    """
    Retrieves all leave records for a specified user and groups them by month and year.
    It returns a structured list of leave records for the user, formatted by month.
    """
    leave = user.user_leaves.all()

    return group_leave_by_month_and_year(leave)


def get_users_with_leave():
    """
    Retrieves a list of active users who have approved leave requests.
    It filters users based on the status of their leave approvals and returns
    a distinct list, ordered by first name.
    """
    return (
        User.objects.filter(
            Q(is_active=True)
            & Q(user_leaves__isnull=False)
            & Q(
                user_leaves__first_approver_data__status=LeaveRequestAction.APPROVED.value
            )
            & Q(
                user_leaves__second_approver_data__status=LeaveRequestAction.APPROVED.value
            )
        )
        .order_by("first_name")
        .distinct()
    )


def get_leave_to_review(
    user, specific_user_id: int = "", month: int = "", year: int = ""
):
    """
    Retrieves leave records for review by a specified user, optionally filtering by
    a specific user ID, month, and year. It returns the grouped leave data by month
    and year, including the user's status for each leave request.
    """
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
    """
    Retrieves a list of distinct years in which leave records exist.
    The years are ordered chronologically and returned as a list.
    """
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
    """
    Checks if a user has any approved leave on a specified date.
    Returns True if there is an approved leave record for that date; otherwise, returns False.
    """
    selected_date = get_date_object(year=year, month=month, day=day)
    approved_status = LeaveRequestAction.APPROVED.value

    return user.user_leaves.filter(
        Q(first_approver_data__status=approved_status)
        | Q(second_approver_data__status=approved_status),
        date=selected_date,
    )
