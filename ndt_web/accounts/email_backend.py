"""
SMTP-бэкенд с проверкой: Яндекс SMTP с облачных IP не работает (ошибка 535).
"""

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as DjangoSMTPBackend


YANDEX_SMTP_BLOCKED_MSG = (
    'Яндекс SMTP (smtp.yandex.ru) недоступен с облачных серверов (ошибка 535). '
    'На Render задайте BREVO_SMTP_KEY (smtp-relay.brevo.com) или RESEND_API_KEY. '
    'См. .env.example.'
)


def is_yandex_smtp_host(host: str | None = None) -> bool:
    host = (host or getattr(settings, 'EMAIL_HOST', '') or '').lower()
    return 'yandex' in host


class SafeSMTPBackend(DjangoSMTPBackend):
    """SMTP с запретом Яндекса и понятной ошибкой до подключения."""

    def open(self):
        if is_yandex_smtp_host(self.host or settings.EMAIL_HOST):
            raise OSError(YANDEX_SMTP_BLOCKED_MSG)
        return super().open()
