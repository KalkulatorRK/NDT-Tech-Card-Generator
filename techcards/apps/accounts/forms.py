"""Forms for user profile management."""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import User


class ProfileUpdateForm(forms.ModelForm):
    """Form for editing user profile details."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone", "organization")
        labels = {
            "first_name": _("Имя"),
            "last_name": _("Фамилия"),
            "email": _("Email"),
            "phone": _("Телефон"),
            "organization": _("Организация"),
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "+7 (___) ___-__-__"}),
            "organization": forms.TextInput(attrs={"class": "form-control"}),
        }
