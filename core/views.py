from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django_htmx.http import (HttpResponseClientRedirect, reswap, retarget,
                              trigger_client_event)
from render_block import render_block_to_string

from core.models import BiometricDetail, Department, UserDetails
from core.utils import (check_if_biometric_uid_exists, check_user_has_password,
                        get_civil_status_list, get_education_list,
                        get_or_create_intial_user_one_to_one_fields,
                        password_validation, profile_picture_validation,
                        string_to_date, update_user_and_user_details)


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
            response = HttpResponseClientRedirect(reverse("core:profile"))
            return response
        else:
            if not password:
                if not check_user_has_password(email=email):
                    context.update({"user_email": email})
                    response.content = render_block_to_string(
                        "core/components/set_password.html",
                        "set_password_form",
                        context,
                    )
                    response = retarget(response, "#login_card")
                    response = reswap(response, "outerHTML")
                    return response

            context.update(
                {
                    "login_error_message": "Email or password is incorrect. Please try again.",
                }
            )
            response.content = render_block_to_string(
                "core/login.html", "login_error_message", context
            )
            response = retarget(response, "#login_error_message")
            response = reswap(response, "outerHTML")
            return response

    return render(request, "core/login.html", context)


def set_new_user_password(request):
    context = {}
    password = request.POST["password"]
    confirm_password = request.POST["confirm_password"]
    response = HttpResponse()

    errors = password_validation(password, confirm_password)

    if errors:
        context.update({"password_validation_errors": errors})
        response.content = render_block_to_string(
            "core/components/set_password.html", "set_error_message", context
        )
        response = retarget(response, "#error_list")
        response = reswap(response, "outerHTML")
        return response

    user_email = request.POST["email"]
    user = User.objects.get(email=user_email)
    user.set_password(password)
    user.save()

    context.update(
        {
            "password_successfully_set_message": "Your password has been set. Please login."
        }
    )
    response.content = render_block_to_string("core/login.html", "login_card", context)
    response = retarget(response, "#login_card")
    response = reswap(response, "outerHTML")
    return response


def user_logout(request):
    logout(request)
    response = HttpResponse()
    response = HttpResponseClientRedirect(reverse("core:login"))
    return response


def user_register(request):
    context = {}
    return render(request, "core/register.html", context)


### USER PROFILE ###
@login_required(login_url="/login")
def user_profile(request):
    user = request.user
    departments = Department.objects.filter(is_active=True)
    education_list = get_education_list()
    civil_status_list = get_civil_status_list()
    context = {
        "current_user": user,
        "department_list": departments,
        "civil_status_list": civil_status_list,
        "education_list": education_list,
    }
    get_or_create_intial_user_one_to_one_fields(user)
    if request.method == "POST":
        updated_user = update_user_and_user_details(
            user_instance=user, querydict=request.POST
        )
        context.update(
            {"show_alert": True, "alert_message": "Profile successfully updated."}
        )
        response = HttpResponse()
        response.content = render_block_to_string(
            "core/user_profile.html", "profile_information_section", context
        )
        response = retarget(response, "#profile_information_section")
        response = reswap(response, "outerHTML")
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
        response = retarget(response, "#password_information_section")
        response = reswap(response, "outerHTML")

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
def upload_user_profile_picture(request):
    context = {"show_alert": True}
    if request.FILES:
        profile_picture = request.FILES.get("profile_picture")
        error = profile_picture_validation(profile_picture)

        response = HttpResponse()
        response = retarget(response, "#profile_picture_section")
        response = reswap(response, "outerHTML")

        if error:
            context.update({"error": True, "alert_message": error})
            response.content = render_block_to_string(
                "core/user_profile.html", "profile_picture_section", context
            )

        if error is None:
            user = request.user
            user_details = request.user.userdetails
            user_details.profile_picture = profile_picture
            user_details.save()
            context.update(
                {
                    "error": False,
                    "alert_message": "Profile picture successfully uploaded.",
                    "new_profile_picture": user_details.profile_picture.url,
                }
            )
            response.content = render_block_to_string(
                "core/user_profile.html", "profile_picture_section", context
            )
            response = retarget(response, "#profile_picture_section")
            response = reswap(response, "outerHTML")

    return response


### USER MANAGEMENT ###
@login_required(login_url="/login")
def user_management(request):
    users = User.objects.exclude(id=request.user.id)
    context = {"users": users}
    return render(request, "core/user_management.html", context)


@login_required(login_url="/login")
def add_new_user(request):
    context = {}
    first_name = request.POST["first_name"]
    last_name = request.POST["last_name"]
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
                get_or_create_intial_user_one_to_one_fields(user)
                response = HttpResponseClientRedirect(reverse("core:user_management"))
            else:
                context.update({"add_user_error_message": "Email already exists."})
                response.content = render_block_to_string(
                    "core/user_management.html", "add_user_error_message", context
                )
                response = retarget(response, "#add_user_error_message")
                response = reswap(response, "outerHTML")
        except IntegrityError:
            context.update(
                {"add_user_error_message": "User credentials already exists."}
            )
            response.content = render_block_to_string(
                "core/user_management.html", "add_user_error_message", context
            )
            response = retarget(response, "#add_user_error_message")
            response = reswap(response, "outerHTML")
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
    response = reswap(response, "outerHTML")
    return response


@login_required(login_url="/login")
def modify_user_details(request, pk):
    user = User.objects.get(id=pk)
    get_or_create_intial_user_one_to_one_fields(user)
    departments = Department.objects.all()
    civil_status_list = get_civil_status_list()
    education_list = get_education_list()
    context = {
        "selected_user": user,
        "department_list": departments,
        "civil_status_list": civil_status_list,
        "education_list": education_list,
    }
    if request.POST:
        response = HttpResponse()
        updated_user = update_user_and_user_details(
            user_instance=user, querydict=request.POST
        )
        context.update(
            {
                "show_alert": True,
                "error": False,
                "alert_message": "User successfully updated.",
                "selected_user": updated_user,
            }
        )
        response.content = render_block_to_string(
            "core\modify_user_profile.html", "profile_information_section", context
        )
        response = retarget(response, "#profile_information_section")
        response = reswap(response, "outerHTML")
        return response

    return render(request, "core/modify_user_profile.html", context)


@login_required(login_url="/login")
def modify_user_biometric_details(request, pk):
    context = {}
    if request.htmx and request.POST:
        data = request.POST
        user = User.objects.get(id=pk)
        uid_in_device = data.get("uid_in_device", None)
        context.update(
            {
                "show_alert": True,
                "error": False,
                "alert_message": "User biometric configuration successfully updated.",
                "selected_user": user,
            }
        )
        if not check_if_biometric_uid_exists(current_user=user, uid=uid_in_device):
            biometric_details = user.biometricdetail
            biometric_details.uid_in_device = data.get("uid_in_device", None)
            biometric_details.save()
        else:
            context.update(
                {
                    "error": True,
                    "alert_message": "Provided ID is already in use by another user.",
                }
            )
        response = HttpResponse()
        response.content = render_block_to_string(
            "core\modify_user_profile.html", "biometric_configuration_section", context
        )
        response = retarget(response, "#biometric_configuration_section")
        response = reswap(response, "outerHTML")
        return response
