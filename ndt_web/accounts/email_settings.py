"""Выбор бэкенда исходящей почты (Resend / SMTP / консоль)."""


def resolve_email_backend(
    *,
    resend_api_key: str,
    email_host: str,
    email_host_user: str,
    email_host_password: str,
    explicit_backend: str = '',
) -> tuple[str, str | None]:
    """
    Возвращает (EMAIL_BACKEND, предупреждение или None).

    Resend имеет наивысший приоритет. Явный EMAIL_BACKEND=smtp без хоста
    игнорируется — типичная ошибка после перехода с Яндекс SMTP на Resend.
    """
    if resend_api_key.strip():
        return 'anymail.backends.resend.EmailBackend', None

    host = email_host.strip()
    user = email_host_user.strip()
    password = email_host_password.strip()
    backend = explicit_backend.strip()

    if host and user and password:
        return backend or 'accounts.email_backend.SafeSMTPBackend', None

    if backend and 'smtp' in backend.lower():
        return 'django.core.mail.backends.console.EmailBackend', (
            'EMAIL_BACKEND указывает на SMTP, но EMAIL_HOST не задан. '
            'Для Render задайте RESEND_API_KEY и удалите EMAIL_BACKEND, '
            'EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD.'
        )

    return backend or 'django.core.mail.backends.console.EmailBackend', None
