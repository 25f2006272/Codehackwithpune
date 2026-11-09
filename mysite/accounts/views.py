from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.db import transaction

from .forms import SignUpForm
from .models import UserProfile


def signup_view(request):

    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = SignUpForm(request.POST)

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

    return render(request, "accounts/signup.html", {
        "form": form
    })


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
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