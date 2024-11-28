from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models import Q


def get_user_shift_swap_request(user):
    """
    Retrieves all shift swap requests for a given user, ordered by the creation date in descending order.
    """
    return user.shift_swap_requests.order_by("-created")


def get_pending_swap_requests(approver):
    """
    Retrieves all pending shift swap requests for a given approver, ordered by the creation date in descending order.
    """
    return approver.shift_swaps_as_approver.order_by("-created")


def get_users_involved_with_swap_requests(approver):
    """
    Retrieves a list of users who are involved in shift swap requests, either as requestors or targets,
    where the given approver is involved. The users are ordered by their first name.
    """
    UserModel = get_user_model()
    users = (
        UserModel.objects.filter(
            Q(
                Q(shift_swap_requests__isnull=False)
                & Q(shift_swap_requests__approver=approver)
            )
            | Q(
                Q(shift_swap_target__isnull=False)
                & Q(shift_swap_target__approver=approver)
            )
        )
        .distinct()
        .order_by("first_name")
    )
    return users


def get_years_for_existing_swap_requests():
    """
    Retrieves a list of distinct years for which shift swap requests exist.
    Returns a list of years.
    """
    ShiftSwapModel = apps.get_model("attendance", "ShiftSwap")
    years = ShiftSwapModel.objects.values_list(
        "requested_shift__date__year", flat=True
    ).distinct()
    return years
