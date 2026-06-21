"""
Формы приложения «Аккаунты».

Регистрация, вход, редактирование профиля.
"""

from django import forms
from django.conf import settings
from django.contrib.auth.forms import (
    UserCreationForm, AuthenticationForm, PasswordChangeForm,
)
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML

from .models import CustomUser


def _recaptcha_enabled() -> bool:
    """reCAPTCHA включается только при наличии ключей в настройках."""
    return bool(
        getattr(settings, 'RECAPTCHA_PUBLIC_KEY', '')
        and getattr(settings, 'RECAPTCHA_PRIVATE_KEY', '')
    )


class RegistrationForm(UserCreationForm):
    """Форма регистрации нового пользователя."""

    email = forms.EmailField(
        required=True, label='Электронная почта',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email'}),
    )
    first_name = forms.CharField(
        max_length=150, required=True, label='Имя',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    last_name = forms.CharField(
        max_length=150, required=True, label='Фамилия',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    organization = forms.CharField(
        max_length=255, required=False, label='Организация',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    # Согласие с условиями использования
    agree_terms = forms.BooleanField(
        required=True, label='Я согласен с условиями использования сервиса',
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'organization',
                  'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Логин'
        self.fields['username'].help_text = (
            'Только буквы, цифры и символы @/./+/-/_. Не более 150 символов.'
        )
        self.fields['password1'].label = 'Пароль'
        self.fields['password2'].label = 'Повторите пароль'

        # Применяем Bootstrap-класс к полям
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput,
                                         forms.PasswordInput, forms.Select)):
                field.widget.attrs.setdefault('class', 'form-control')

        if _recaptcha_enabled():
            from django_recaptcha.fields import ReCaptchaField
            from django_recaptcha.widgets import ReCaptchaV3
            self.fields['captcha'] = ReCaptchaField(
                widget=ReCaptchaV3(action='register'),
                label='',
            )

    def clean_email(self):
        """Проверяет, что email ещё не зарегистрирован."""
        email = self.cleaned_data.get('email', '').strip().lower()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError(
                'Пользователь с таким адресом электронной почты уже зарегистрирован.'
            )
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.organization = self.cleaned_data.get('organization', '')
        user.email_verified = False
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """Форма входа в систему."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Логин или email'
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'autofocus': True})
        self.fields['password'].label = 'Пароль'
        self.fields['password'].widget.attrs.update({'class': 'form-control'})

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.email_verified:
            self.email_not_verified = True
            raise forms.ValidationError(
                'Подтвердите адрес электронной почты. '
                'Проверьте входящие или запросите повторную отправку письма.',
                code='email_not_verified',
            )


class ResendVerificationForm(forms.Form):
    """Форма повторной отправки письма подтверждения."""

    email = forms.EmailField(
        label='Электронная почта',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'autofocus': True}),
    )


class ProfileEditForm(forms.ModelForm):
    """Форма редактирования профиля пользователя."""

    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email',
            'organization', 'phone', 'position',
            'ndt_certificate_number', 'ndt_level',
            'ndt_methods', 'certificate_expiry',
        ]
        labels = {
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'email': 'Электронная почта',
            'organization': 'Организация',
            'phone': 'Телефон',
            'position': 'Должность',
            'ndt_certificate_number': 'Номер удостоверения НК',
            'ndt_level': 'Уровень квалификации',
            'ndt_methods': 'Методы НК',
            'certificate_expiry': 'Срок действия удостоверения',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'organization': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (___) ___-__-__'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'ndt_certificate_number': forms.TextInput(attrs={'class': 'form-control'}),
            'ndt_level': forms.Select(
                attrs={'class': 'form-select'},
                choices=[
                    ('', '— не указан —'),
                    ('I', 'I уровень'),
                    ('II', 'II уровень'),
                    ('III', 'III уровень'),
                ],
            ),
            'ndt_methods': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'РК, ВИК, УЗК'},
            ),
            'certificate_expiry': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
            ),
        }

    def clean_certificate_expiry(self):
        """Предупреждение, если срок действия удостоверения истёк."""
        expiry = self.cleaned_data.get('certificate_expiry')
        if expiry and expiry < timezone.now().date():
            # Не блокируем — только данные, реальную проверку можно добавить
            pass
        return expiry
