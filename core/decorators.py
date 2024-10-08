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
