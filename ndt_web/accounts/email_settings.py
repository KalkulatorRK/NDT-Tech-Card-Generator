"""Выбор бэкенда исходящей почты (Unisender Go / Resend / SMTP / консоль)."""


def resolve_email_backend(
    *,
    unisender_go_api_key: str = '',
    resend_api_key: str = '',
    email_host: str = '',
    email_host_user: str = '',
    email_host_password: str = '',
    explicit_backend: str = '',
) -> tuple[str, str | None]:
    """
    Возвращает (EMAIL_BACKEND, предупреждение или None).

    Приоритет: Unisender Go (РФ) → Resend → SMTP (Brevo и др.) → консоль.
  """
    if unisender_go_api_key.strip():
        return 'anymail.backends.unisender_go.EmailBackend', None

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
            'Задайте UNISENDER_GO_API_KEY (РФ) или RESEND_API_KEY и удалите '
            'EMAIL_BACKEND, EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD.'
        )

    return backend or 'django.core.mail.backends.console.EmailBackend', None
