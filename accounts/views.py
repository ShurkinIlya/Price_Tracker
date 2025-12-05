from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from products.models import Offer, ProductQuery, OfferHistory, PriceAlert
from .forms import CustomAuthenticationForm, CustomUserCreationForm


def register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Добро пожаловать, {user.username}! Аккаунт создан.")
            return redirect("home")
        for error in form.errors.values():
            messages.error(request, error)
    else:
        form = CustomUserCreationForm()
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"С возвращением, {username}!")
                return redirect("home")
        else:
            messages.error(request, "Неверные имя пользователя или пароль.")
    else:
        form = CustomAuthenticationForm()
    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.success(request, "Вы вышли из аккаунта.")
    return redirect("home")


@login_required
def profile_view(request):
    user = request.user
    tracked_count = ProductQuery.objects.filter(created_by=user).count()
    history_count = OfferHistory.objects.filter(query__created_by=user).count()
    alerts_count = 0
    return render(
        request,
        "accounts/profile.html",
        {
            "user": user,
            "tracked_count": tracked_count,
            "history_count": history_count,
            "alerts_count": alerts_count,
        },
    )


@login_required
def clear_history(request):
    user = request.user
    # Remove alerts, offers, history by deleting queries owned by the user
    ProductQuery.objects.filter(created_by=user).delete()
    messages.success(request, "История очищена. Оповещения и предложения сброшены.")
    return redirect("profile")
