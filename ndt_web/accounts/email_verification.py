"""
Подтверждение адреса электронной почты при регистрации.
"""

import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from .models import CustomUser

logger = logging.getLogger(__name__)


class EmailSendError(Exception):
    """Ошибка отправки письма подтверждения."""


def build_verification_url(user: CustomUser) -> str:
    """Формирует URL для подтверждения email."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    site_url = settings.SITE_URL.rstrip('/')
    return f'{site_url}/accounts/verify/{uid}/{token}/'


def _format_email_error(exc: Exception) -> str:
    """Переводит типичные ошибки SMTP в понятные подсказки."""
    message = str(exc)
    if '535' in message and 'access rights' in message.lower():
        return (
            'Яндекс отклонил вход: у ящика moohobor@yandex.ru не включена отправка '
            'через почтовые программы (SMTP). Откройте mail.yandex.ru → Настройки → '
            '«Почтовые программы» → разрешите доступ с IMAP/SMTP, затем используйте '
            '«Пароль приложения» из id.yandex.ru в переменной EMAIL_HOST_PASSWORD на Render.'
        )
    if '535' in message or 'authentication failed' in message.lower():
        return (
            'Ошибка авторизации SMTP. Проверьте EMAIL_HOST_USER и EMAIL_HOST_PASSWORD '
            'на Render: нужен пароль приложения Яндекса (не обычный пароль от аккаунта).'
        )
    return (
        'Не удалось отправить письмо. Проверьте настройки SMTP на сервере '
        'или повторите попытку позже.'
    )


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

    try:
        sent = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception(
            'SMTP error sending verification email to %s via %s:%s',
            user.email,
            settings.EMAIL_HOST,
            settings.EMAIL_PORT,
        )
        raise EmailSendError(_format_email_error(exc)) from exc

    if sent != 1:
        logger.error('send_mail returned %s for %s', sent, user.email)
        raise EmailSendError('Письмо не было отправлено. Повторите попытку позже.')


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
