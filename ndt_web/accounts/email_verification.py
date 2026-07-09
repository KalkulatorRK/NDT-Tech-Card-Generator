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

from .email_backend import YANDEX_SMTP_BLOCKED_MSG, is_yandex_smtp_host
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


def _assert_email_can_send() -> None:
    """Проверка конфигурации до отправки."""
    backend = getattr(settings, 'EMAIL_BACKEND', '')
    if 'console' in backend or 'locmem' in backend:
        raise EmailSendError(
            'Почта на сервере не настроена. На Render задайте UNISENDER_GO_API_KEY '
            '(РФ) или RESEND_API_KEY. Удалите старые EMAIL_HOST* и EMAIL_BACKEND.'
        )
    if 'unisender' in backend.lower() or 'resend' in backend.lower():
        if 'unisender' in backend.lower() and not getattr(settings, 'UNISENDER_GO_API_KEY', '').strip():
            raise EmailSendError('UNISENDER_GO_API_KEY не задан на сервере.')
        if 'resend' in backend.lower() and not getattr(settings, 'RESEND_API_KEY', '').strip():
            raise EmailSendError('RESEND_API_KEY не задан на сервере.')
        return
    if 'smtp' in backend.lower() and not getattr(settings, 'EMAIL_HOST', '').strip():
        raise EmailSendError(
            'Ошибка конфигурации: SMTP без EMAIL_HOST (в логах «via :587»). '
            'Задайте RESEND_API_KEY на Render и удалите переменные EMAIL_BACKEND, '
            'EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD.'
        )
    if is_yandex_smtp_host():
        raise EmailSendError(YANDEX_SMTP_BLOCKED_MSG)


def _format_email_error(exc: Exception) -> str:
    """Переводит типичные ошибки SMTP в понятные подсказки."""
    message = str(exc)
    if YANDEX_SMTP_BLOCKED_MSG in message or (
        '535' in message and 'access rights' in message.lower()
    ):
        return YANDEX_SMTP_BLOCKED_MSG
    if '535' in message or 'authentication failed' in message.lower():
        return (
            'Ошибка авторизации SMTP. Если настроен Resend — удалите на Render '
            'EMAIL_BACKEND и EMAIL_HOST* (должен остаться только RESEND_API_KEY).'
        )
    if 'resend' in message.lower() or 'anymail' in message.lower():
        if 'only send testing emails' in message.lower() or 'verify a domain' in message.lower():
            return (
                'Resend в тестовом режиме: с onboarding@resend.dev письма уходят только '
                'на адрес владельца аккаунта Resend. Для torf1@yandex.ru и других '
                'пользователей верифицируйте домен на resend.com/domains и задайте на Render '
                'DEFAULT_FROM_EMAIL=noreply@ваш-домен.ru (например utbniti.ru).'
            )
        return f'Ошибка Resend API: {message}'
    return (
        'Не удалось отправить письмо. Выполните на Render: '
        'python manage.py check_email_config'
    )


def send_verification_email(user: CustomUser) -> None:
    """Отправляет письмо с ссылкой для подтверждения email."""
    verification_url = build_verification_url(user)
    site_url = settings.SITE_URL.rstrip('/')
    context = {
        'user': user,
        'verification_url': verification_url,
        'site_name': 'Карта-НК',
        'logo_url': f'{site_url}/static/img/brand/app-icon.png',
    }
    subject = 'Подтверждение регистрации на Карта-НК'
    message = render_to_string('accounts/email/verification_email.txt', context)
    html_message = render_to_string('accounts/email/verification_email.html', context)

    _assert_email_can_send()

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
            'Email error sending verification to %s (backend=%s, from=%s)',
            user.email,
            settings.EMAIL_BACKEND,
            settings.DEFAULT_FROM_EMAIL,
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
