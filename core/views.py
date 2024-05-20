from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from render_block import render_block_to_string

from core.utils import check_user_has_password, password_validation, string_to_date
from core.models import UserDetails, Department


@login_required(login_url="/login")
def main(request):
    return render(request, "core/login.html")


def user_login(request):
    context = {}
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]
        # check_user_has_password(email=email)
        user = authenticate(request, username=email, password=password)
        response = HttpResponse()
        if user is not None:
            login(request, user)
            response["HX-Redirect"] = reverse("core:profile")
            return response
        else:
            if not password:
                if not check_user_has_password(email=email):
                    context.update(
                        {
                            "user_email": email
                        }
                    )
                    response.content = render_block_to_string(
                        "core/components/set_password.html", "set_password_form", context
                    )
                    response["HX-Retarget"] = "#login_card"
                    response["HX-Reswap"] = "outerHTML"
                    return response

            context.update(
                {
                    "login_error_message": "Email or password is incorrect. Please try again.",
                }
            )
            response.content = render_block_to_string(
                "core/login.html", "login_error_message", context
            )
            response["HX-Retarget"] = "#login_error_message"
            response["HX-Reswap"] = "outerHTML"
            return response

    return render(request, "core/login.html", context)


def set_new_user_password(request):
    context = {}
    password = request.POST["password"]
    confirm_password = request.POST["confirm_password"]
    response = HttpResponse()

    errors = password_validation(password, confirm_password)

    if errors:
        context.update(
                {
                    "password_validation_errors": errors
                }
            )
        response.content = render_block_to_string(
                        "core/components/set_password.html", "set_error_message", context
                    )
        response["HX-Retarget"] = "#error_list"
        response["HX-Reswap"] = "outerHTML"
        return response
    
    user_email = request.POST['email']
    user = User.objects.get(email=user_email)
    user.set_password(password)
    user.save()

    context.update(
            {
                "password_successfully_set_message": "Your password has been set. Please login."
            }
        )
    response.content = render_block_to_string(
                    "core/login.html", "login_card", context
                )
    response["HX-Retarget"] = "#login_card"
    response["HX-Reswap"] = "outerHTML"
    return response

def user_logout(request):
    logout(request)
    response = HttpResponse()
    response["HX-Redirect"] = reverse("core:login")
    return response


def user_register(request):
    context = {}
    return render(request, "core/register.html", context)


@login_required(login_url="/login")
def user_profile(request):
    user = request.user
    user_details, created = UserDetails.objects.get_or_create(user=user, defaults={"user": user})
    departments = Department.objects.all()

    if request.method == "POST":
        data = request.POST

        user.first_name = data['first_name']
        user.last_name = data['last_name']
        user.save()

        user_details.address = data['address']
        user_details.phone_number = data['phone_number']
        if data['birthday']:
            user_details.date_of_birth = string_to_date(data['birthday'])
        if data['day_of_hiring']:
            user_details.date_of_hiring = string_to_date(data['day_of_hiring'])
        user_details.rank = data['rank']
        user_details.save()
    # TODO: Add Educational Attainment
    context = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "address": user_details.address or "",
        "phone_number": user_details.phone_number or "",
        "birthday": user_details.str_date_of_birth(),
        "department_list": departments,
        "department": user_details.department,
        "date_of_hiring": user_details.str_date_of_hiring(),
        "employee_number": user_details.employee_number or "",
        "rank": user_details.rank or ""
    }

    if request.method == "POST":
        context.update({"show_alert": True, "alert_message": "Profile successfully updated."})
        response = HttpResponse()
        response.content = render_block_to_string(
                "core/user_profile.html", "profile_information_section", context
        )
        response["HX-Retarget"] = "#profile_information_section"
        response["HX-Reswap"] = "outerHTML"
        return response

    return render(request, "core/user_profile.html", context)


@login_required(login_url="/login")
def change_user_password(request):
    context = {"show_alert": True}
    if request.method == "POST":
        current_password = request.POST["current_password"]
        new_password = request.POST["new_password"]
        confirm_password = request.POST["confirm_password"]

        response = HttpResponse()
        response["HX-Retarget"] = "#password_information_section"
        response["HX-Reswap"] = "outerHTML"

        if new_password != confirm_password:
            context.update(
                {"error": True, "alert_message": "Passwords does not match."}
            )
            response.content = render_block_to_string(
                "core/user_profile.html", "password_information_section", context
            )
            return response

        correct_password = request.user.check_password(current_password)

        if correct_password:
            if current_password == new_password:
                context.update(
                    {
                        "error": True,
                        "alert_message": "New password cannot be the same as your old password.",
                    }
                )
                response.content = render_block_to_string(
                    "core/user_profile.html", "password_information_section", context
                )
                return response
            else:
                context.update(
                    {"error": False, "alert_message": "Passwords successfully changed."}
                )
                response.content = render_block_to_string(
                    "core/user_profile.html", "password_information_section", context
                )
                return response
        else:
            context.update(
                {
                    "error": True,
                    "alert_message": "The current password you entered is incorrect.",
                }
            )
            response.content = render_block_to_string(
                "core/user_profile.html", "password_information_section", context
            )
            return response


@login_required(login_url="/login")
def user_management(request):
    users = User.objects.exclude(id=request.user.id)
    context = {"users": users}
    return render(request, "core/user_management.html", context)


@login_required(login_url="/login")
def add_new_user(request):
    context = {}
    first_name = request.POST["first_name"].lower()
    last_name = request.POST["last_name"].lower()
    email = request.POST["email"].lower()

    if request.method == "POST":
        response = HttpResponse()
        try:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "username": f"{first_name}_{last_name}",
                },
            )
            if created:
                response["HX-Redirect"] = reverse("core:user_management")
            else:
                context.update({"add_user_error_message": "Email already exists."})
                response.content = render_block_to_string(
                    "core/user_management.html", "add_user_error_message", context
                )
                response["HX-Retarget"] = "#add_user_error_message"
                response["HX-Reswap"] = "outerHTML"
        except IntegrityError:
            context.update(
                {"add_user_error_message": "User credentials already exists."}
            )
            response.content = render_block_to_string(
                "core/user_management.html", "add_user_error_message", context
            )
            response["HX-Retarget"] = "#add_user_error_message"
            response["HX-Reswap"] = "outerHTML"
    return response


@login_required(login_url="/login")
def toggle_user_status(request, pk):
    user = User.objects.get(id=pk)
    user.is_active = not user.is_active
    user.save()

    context = {"user": user}
    response = HttpResponse()
    response.content = render_block_to_string(
        "core/user_management.html", "user_table_record", context
    )
    response["HX-Reswap"] = "outerHTML"
    return response
