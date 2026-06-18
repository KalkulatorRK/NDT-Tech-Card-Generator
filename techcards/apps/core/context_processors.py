"""Global context variables available in all templates."""

from django.conf import settings


def global_settings(request):
    """Inject site-wide settings into every template context."""
    quota = 0
    if request.user.is_authenticated:
        quota = request.user.tech_card_quota

    return {
        "SUPPORT_EMAIL": settings.SUPPORT_EMAIL,
        "TELEGRAM_LINK": settings.TELEGRAM_LINK,
        "user_quota": quota,
    }
