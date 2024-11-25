def get_user_shift_swap_request(user):
    return user.shift_swap_requests.order_by("-created")


def get_pending_swap_requests(approver):
    return approver.shift_swaps_as_approver.order_by("-created")
