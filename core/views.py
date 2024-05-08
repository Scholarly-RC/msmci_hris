from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse
from render_block import render_block_to_string

from django.db.utils import IntegrityError


@login_required(login_url="/login")
def main(request):
    return render(request, "core/login.html")


def user_login(request):
    context = {}
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]
        user = authenticate(request, username=email, password=password)
        response = HttpResponse()
        if user is not None:
            login(request, user)
            response["HX-Redirect"] = reverse("core:profile")
            return response
        else:
            context.update(
                {"login_error_message": "Email or password is incorrect. Please try again."}
            )
            response.content = render_block_to_string(
                "core/login.html", "login_error_message", context
            )
            response["HX-Retarget"] = "#login_error_message"
            response["HX-Reswap"] = "outerHTML"
            return response

    return render(request, "core/login.html", context)

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
    context = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
    }
    return render(request, "core/user_profile.html", context)


@login_required(login_url="/login")
def user_management(request):
    users = User.objects.exclude(id=request.user.id)
    context = {'users': users}
    return render(request, "core/user_management.html", context)


@login_required(login_url="/login")
def add_new_user(request):
    context = {}
    first_name = request.POST['first_name'].lower()
    last_name = request.POST['last_name'].lower()
    email = request.POST['email'].lower()

    if request.method == "POST":
        response = HttpResponse()
        try:
            user, created = User.objects.get_or_create(email=email, defaults={'first_name': first_name, 'last_name': last_name, 'email': email, 'username': f'{first_name}_{last_name}'})
            if created:
                user.set_password(last_name)
                #TODO: Create User Details Here
                response["HX-Redirect"] = reverse("core:user_management")
            else:
                context.update({'add_user_error_message': "Email already exists."})
                response.content = render_block_to_string(
                        "core/user_management.html", "add_user_error_message", context
                    )
                response["HX-Retarget"] = "#add_user_error_message"
                response["HX-Reswap"] = "outerHTML"
        except IntegrityError:
            context.update({'add_user_error_message': "User credentials already exists."})
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

    context = {'user': user}
    response = HttpResponse()
    response.content = render_block_to_string(
                        "core/user_management.html", "user_table_record", context
                    )
    response["HX-Reswap"] = "outerHTML"
    return response
