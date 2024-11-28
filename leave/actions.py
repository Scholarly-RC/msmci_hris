import logging

from django.apps import apps
from django.db import transaction

from core.utils import string_to_date
from hris.exceptions import InvalidLeaveRequestAction, UserNotApprover
from leave.enums import LeaveRequestAction
from leave.utils import get_approvers_per_user

logger = logging.getLogger(__name__)


@transaction.atomic
def process_set_department_approver(payload):
    """
    Sets the department approvers (department head, director, president, and HR)
    for a specified department based on the provided payload.
    If an approver already exists, updates their data; otherwise, creates new approvers.
    """
    try:
        UserModel = apps.get_model("auth", "User")
        DepartmentModel = apps.get_model("core", "Department")
        LeaveApproverModel = apps.get_model("leave", "LeaveApprover")

        department_head = UserModel.objects.get(
            id=payload.get("selected_department_head")
        )
        director = UserModel.objects.get(id=payload.get("selected_director"))
        president = UserModel.objects.get(id=payload.get("selected_president"))
        hr = UserModel.objects.get(id=payload.get("selected_hr"))

        department = DepartmentModel.objects.get(id=payload.get("selected_department"))
        leave_approver, leave_approver_created = (
            LeaveApproverModel.objects.get_or_create(
                department=department,
                defaults={
                    "department_approver": department_head,
                    "director_approver": director,
                    "president_approver": president,
                    "hr_approver": hr,
                },
            )
        )

        if not leave_approver_created:
            leave_approver.department_approver = department_head
            leave_approver.director_approver = director
            leave_approver.president_approver = president
            leave_approver.hr_approver = hr

            leave_approver.save()

        return leave_approver
    except Exception:
        logger.error(
            "An error occurred while setting department approvers", exc_info=True
        )
        raise


@transaction.atomic
def process_set_user_leave_credit(payload):
    """
    Sets or updates the leave credit for a specified user based on the provided payload.
    If a leave credit entry does not exist for the user, it creates a new one.
    """
    try:
        UserModel = apps.get_model("auth", "User")
        LeaveCreditModel = apps.get_model("leave", "LeaveCredit")

        amount = payload.get("credit_amount")
        user_id = payload.get("user")
        user = UserModel.objects.get(id=user_id)
        leave_credit, leave_credit_created = LeaveCreditModel.objects.get_or_create(
            user=user, defaults={"credits": payload.get("credit_amount")}
        )

        if not leave_credit_created:
            leave_credit.credits = amount
            leave_credit.save()

        return leave_credit, user
    except Exception:
        logger.error(
            "An error occurred while setting leave credit for user", exc_info=True
        )
        raise


@transaction.atomic
def process_create_leave_request(user, payload):
    """
    Creates a new leave request for the given user with the specified leave type, date,
    and additional information. Also determines and sets the approvers for the request.
    """
    try:
        LeaveModel = apps.get_model("leave", "Leave")
        type = payload.get("leave_type")
        date = string_to_date(payload.get("leave_date"))
        info = payload.get("leave_info")

        first_approver_data, second_approver_data = get_approvers_per_user(user)

        new_leave = LeaveModel.objects.create(
            user=user,
            type=type,
            date=date,
            info=info,
            first_approver_data=first_approver_data,
            second_approver_data=second_approver_data,
        )

        return new_leave
    except Exception:
        logger.error(
            "An error occurred while creating a leave request for user", exc_info=True
        )
        raise


@transaction.atomic
def process_submit_leave_request_response(user, payload):
    """
    Submits the response (approve/reject) for a leave request by an approver.
    The function updates the status of the first or second approver's data.
    """

    def _set_approver_data(data, choice):
        if choice == "APPROVE":
            data["status"] = LeaveRequestAction.APPROVED.value
            return
        if choice == "REJECT":
            data["status"] = LeaveRequestAction.REJECTED.value
            return
        raise InvalidLeaveRequestAction("Invalid choice for approval.")

    try:
        LeaveModel = apps.get_model("leave", "Leave")

        choice = payload.get("choice")
        leave_id = payload.get("leave")

        leave = LeaveModel.objects.get(id=leave_id)

        if leave.first_approver_data["approver"] == user.id:
            _set_approver_data(leave.first_approver_data, choice)
        elif leave.second_approver_data["approver"] == user.id:
            _set_approver_data(leave.second_approver_data, choice)
        else:
            raise UserNotApprover(
                "You do not have approval rights for this leave request."
            )
        leave.save()
        return leave
    except Exception:
        logger.error(
            "An error occurred while submitting leave request response for user",
            exc_info=True,
        )
        raise


@transaction.atomic
def process_delete_submit_leave_request(leave):
    """
    Deletes the specified leave request. If the leave is approved and credits have been used,
    it also adjusts the user's used leave credits.
    """
    try:
        if (
            leave.get_status() == LeaveRequestAction.APPROVED.value
            and leave.user.leavecredit.used_credits
        ):
            leave.user.leavecredit.used_credits -= 1
            leave.user.leavecredit.save()
        leave.delete()
    except Exception:
        logger.error("An error occurred while deleting leave request", exc_info=True)
        raise


@transaction.atomic
def process_add_user_used_leave_credits(user):
    """
    Increments the used leave credits for a specified user by one.
    """
    try:
        if not user.leavecredit.used_credits:
            user.leavecredit.used_credits = 1
        else:
            user.leavecredit.used_credits += 1
        user.leavecredit.save()
    except Exception:
        logger.error(
            "An error occurred while updating used leave credits for user",
            exc_info=True,
        )
        raise


@transaction.atomic
def process_reset_user_leave_credits(user_id):
    """
    Resets the used leave credits for a specified user, ensuring the user’s credit usage is set back to zero.
    """
    try:
        LeaveCreditModel = apps.get_model("leave", "LeaveCredit")

        leave_credit = LeaveCreditModel.objects.get(user__id=user_id)

        leave_credit.reset_used_credits()
        return leave_credit, leave_credit.user
    except Exception:
        logger.error(
            "An error occurred while resetting leave credits for user ID", exc_info=True
        )
        raise
