"""
Диагностика настроек почты на сервере (Render и др.).

Использование:
    python manage.py check_email_config
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.email_settings import resolve_email_backend


def _mask_secret(value: str) -> str:
    value = (value or '').strip()
    if not value:
        return '— не задан —'
    if len(value) <= 8:
        return '*** (задан)'
    return f'{value[:6]}...{value[-2:]} (задан, {len(value)} симв.)'


class Command(BaseCommand):
    help = 'Показывает активный бэкенд почты и подсказки по исправлению'

    def handle(self, *args, **options):
        resend_key = getattr(settings, 'RESEND_API_KEY', '')
        host = getattr(settings, 'EMAIL_HOST', '')
        backend = settings.EMAIL_BACKEND

        self.stdout.write('=== Диагностика почты НК-Карта ===')
        self.stdout.write(f'EMAIL_BACKEND: {backend}')
        self.stdout.write(f'UNISENDER_GO_API_KEY: {_mask_secret(getattr(settings, "UNISENDER_GO_API_KEY", ""))}')
        self.stdout.write(f'RESEND_API_KEY: {_mask_secret(resend_key)}')
        self.stdout.write(f'EMAIL_HOST: {host or "— пусто —"}')
        self.stdout.write(f'EMAIL_PORT: {getattr(settings, "EMAIL_PORT", "—")}')
        self.stdout.write(f'EMAIL_HOST_USER: {getattr(settings, "EMAIL_HOST_USER", "") or "—"}')
        self.stdout.write(f'DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'SITE_URL: {getattr(settings, "SITE_URL", "")}')

        resolved, warning = resolve_email_backend(
            unisender_go_api_key=getattr(settings, 'UNISENDER_GO_API_KEY', ''),
            resend_api_key=resend_key,
            email_host=host,
            email_host_user=getattr(settings, 'EMAIL_HOST_USER', ''),
            email_host_password=getattr(settings, 'EMAIL_HOST_PASSWORD', ''),
            explicit_backend='',
        )

        if 'unisender' in backend.lower():
            self.stdout.write(self.style.SUCCESS(
                '\nOK: используется Unisender Go (РФ). '
                'DEFAULT_FROM_EMAIL должен быть на подтверждённом домене.'
            ))
            return

        if 'resend' in backend.lower():
            self.stdout.write(self.style.SUCCESS(
                '\nOK: используется Resend API. Для теста: '
                'python manage.py send_test_email torf1@yandex.ru'
            ))
            return

        if warning:
            self.stdout.write(self.style.ERROR(f'\nПРОБЛЕМА: {warning}'))

        if 'smtp' in backend.lower() and not host:
            self.stdout.write(self.style.ERROR(
                '\nПричина ошибки «via :587» в логах: SMTP без хоста.\n'
                'На Render:\n'
                '  1. Добавьте RESEND_API_KEY=re_...\n'
                '  2. УДАЛИТЕ: EMAIL_BACKEND, EMAIL_HOST, EMAIL_HOST_USER, '
                'EMAIL_HOST_PASSWORD, EMAIL_PORT\n'
                '  3. Оставьте: DEFAULT_FROM_EMAIL=onboarding@resend.dev\n'
                '  4. Manual Deploy → Clear build cache\n'
            ))
            return

        if 'console' in backend.lower():
            self.stdout.write(self.style.WARNING(
                '\nПочта не настроена (письма не уходят на email).\n'
                'Для РФ: UNISENDER_GO_API_KEY на https://go.unisender.ru'
            ))
            return

        if resolved != backend:
            self.stdout.write(self.style.WARNING(
                f'\nОжидаемый бэкенд по переменным: {resolved}'
            ))

        self.stdout.write(self.style.WARNING('\nПроверьте переменные Environment на Render.'))
