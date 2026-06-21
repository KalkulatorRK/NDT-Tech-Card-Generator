"""
Подтверждение адреса электронной почты при регистрации.
"""

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from .models import CustomUser


def build_verification_url(user: CustomUser) -> str:
    """Формирует URL для подтверждения email."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    site_url = settings.SITE_URL.rstrip('/')
    return f'{site_url}/accounts/verify/{uid}/{token}/'


def send_verification_email(user: CustomUser) -> None:
    """Отправляет письмо с ссылкой для подтверждения email."""
    verification_url = build_verification_url(user)
    context = {
        'user': user,
        'verification_url': verification_url,
        'site_name': 'НК-Карта',
    }
    subject = 'Подтверждение регистрации на НК-Карта'
    message = render_to_string('accounts/email/verification_email.txt', context)
    html_message = render_to_string('accounts/email/verification_email.html', context)
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )


def verify_email_token(uidb64: str, token: str) -> tuple[bool, CustomUser | None, str]:
    """
    Проверяет токен подтверждения email.

    :return: (успех, пользователь или None, сообщение)
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        return False, None, 'Недействительная ссылка подтверждения.'

    if user.email_verified:
        return True, user, 'Адрес электронной почты уже подтверждён.'

    if not default_token_generator.check_token(user, token):
        return False, user, 'Ссылка подтверждения недействительна или устарела.'

    user.email_verified = True
    user.save(update_fields=['email_verified'])
    return True, user, 'Адрес электронной почты успешно подтверждён.'
