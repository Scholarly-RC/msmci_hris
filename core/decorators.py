from functools import wraps

from django.shortcuts import redirect

from core.models import UserDetails


def hr_required(redirect_url):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if (
                getattr(request.user.userdetails, "role", None)
                != UserDetails.Role.HR.value
            ):
                return redirect(redirect_url)
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def hr_or_dept_head_required(redirect_url):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user_details = getattr(request.user, "userdetails", None)
            if not user_details:
                return redirect(redirect_url)

            is_hr = user_details.role == UserDetails.Role.HR.value
            can_modify = getattr(user_details, "can_modify_shift", False)

            if not (is_hr or can_modify):
                return redirect(redirect_url)

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
