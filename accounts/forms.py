from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "auth-input", "placeholder": "Ваш email"}),
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "username": "Имя пользователя",
            "email": "Ваш email",
            "password1": "Пароль",
            "password2": "Повторите пароль",
        }
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", "auth-input")
            if name in placeholders:
                field.widget.attrs.setdefault("placeholder", placeholders[name])


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {"username": "Имя пользователя", "password": "Пароль"}
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", "auth-input")
            if name in placeholders:
                field.widget.attrs.setdefault("placeholder", placeholders[name])
