"""Разрешение настроек SMTP (Brevo, приоритет над Яндекс)."""


def resolve_smtp_settings(
    *,
    brevo_smtp_key: str = '',
    brevo_login: str = '',
    email_host: str = '',
    email_port: int = 587,
    email_use_tls: bool = True,
    email_use_ssl: bool = False,
    email_host_user: str = '',
    email_host_password: str = '',
) -> dict:
    """
    Возвращает итоговые SMTP-параметры.

    Если задан BREVO_SMTP_KEY — хост Brevo подставляется автоматически.
    """
    host = email_host.strip()
    port = email_port
    use_tls = email_use_tls
    use_ssl = email_use_ssl
    user = email_host_user.strip()
    password = email_host_password.strip()

    if brevo_smtp_key.strip():
        host = 'smtp-relay.brevo.com'
        port = 587
        use_tls = True
        use_ssl = False
        password = brevo_smtp_key.strip()
        if brevo_login.strip():
            user = brevo_login.strip()

    if port == 465:
        use_ssl = True
        use_tls = False
    elif port == 587:
        use_tls = True
        use_ssl = False

    return {
        'EMAIL_HOST': host,
        'EMAIL_PORT': port,
        'EMAIL_USE_TLS': use_tls,
        'EMAIL_USE_SSL': use_ssl,
        'EMAIL_HOST_USER': user,
        'EMAIL_HOST_PASSWORD': password,
    }
