import re

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.db import transaction

from .forms import SignUpForm, EmailAuthenticationForm
from .models import UserProfile


def generate_username(email):
    base = email.split("@")[0]
    base = re.sub(r"[^a-zA-Z0-9_]", "", base).lower()
    base = base[:140] or "user"

    username = base
    counter = 1

    while User.objects.filter(username__iexact=username).exists():
        username = f"{base[:135]}_{counter}"
        counter += 1

    return username


def signup_view(request):

    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":

        data = request.POST.copy()

        full_name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()

        name_parts = full_name.split()

        data["first_name"] = name_parts[0] if name_parts else ""
        data["last_name"] = " ".join(name_parts[1:])

        data["username"] = generate_username(email) if email else ""

        data["password1"] = data.get("password", "")
        data["password2"] = data.get("confirm_password", "")

        form = SignUpForm(data)

        if form.is_valid():

            with transaction.atomic():

                user = form.save()

                display_name = (
                    f"{user.first_name} {user.last_name}"
                ).strip()

                UserProfile.objects.create(
                    user=user,
                    display_name=display_name or user.username
                )

            login(request, user)

            messages.success(
                request,
                "Your account has been created successfully!"
            )

            return redirect("home")

    else:
        form = SignUpForm()

    return render(
        request,
        "accounts/signup.html",
        {"form": form}
    )


class CustomLoginView(LoginView):

    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


@login_required
def logout_view(request):

    if request.method == "POST":

        logout(request)

        messages.success(
            request,
            "You have been logged out successfully."
        )

        return redirect("login")

    return redirect("home")