"""
Отправка тестового письма для проверки настроек SMTP/API на сервере.

Использование:
    python manage.py send_test_email user@example.com
"""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Отправляет тестовое письмо для проверки EMAIL_* настроек'

    def add_arguments(self, parser):
        parser.add_argument('recipient', help='Адрес получателя')
        parser.add_argument(
            '--subject', default='НК-Карта: тест почты', help='Тема письма',
        )

    def handle(self, *args, **options):
        recipient = options['recipient'].strip()
        backend = settings.EMAIL_BACKEND
        self.stdout.write(f'Backend: {backend}')
        self.stdout.write(f'Host: {getattr(settings, "EMAIL_HOST", "—")}:{getattr(settings, "EMAIL_PORT", "—")}')
        self.stdout.write(f'From: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'To: {recipient}')

        try:
            sent = send_mail(
                options['subject'],
                'Тестовое письмо НК-Карта. Если вы его получили — почта настроена верно.',
                settings.DEFAULT_FROM_EMAIL,
                [recipient],
                fail_silently=False,
            )
        except Exception as exc:
            raise CommandError(f'Ошибка отправки: {exc}') from exc

        if sent != 1:
            raise CommandError(f'send_mail вернул {sent}, ожидалось 1')
        self.stdout.write(self.style.SUCCESS('Письмо отправлено успешно.'))
