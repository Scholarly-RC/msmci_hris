from django.apps import apps
from django.db import transaction

from core.utils import string_to_date
from hris.exceptions import InvalidLeaveRequestAction, UserNotApprover
from leave.enums import LeaveRequestAction
from leave.utils import get_approvers_per_user


@transaction.atomic
def process_set_department_approver(payload):
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
    except Exception as error:
        raise error


@transaction.atomic
def process_set_user_leave_credit(payload):
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
    except Exception as error:
        raise error


@transaction.atomic
def process_create_leave_request(user, payload):
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
    except Exception as error:
        raise error


@transaction.atomic
def process_submit_leave_request_response(user, payload):
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
    except Exception as error:
        raise error


@transaction.atomic
def process_delete_submit_leave_request(leave):
    try:
        leave.delete()
    except Exception as error:
        raise error
