def get_user_shift_swap_request(user):
    return user.shift_swap_requests.order_by("-created")
