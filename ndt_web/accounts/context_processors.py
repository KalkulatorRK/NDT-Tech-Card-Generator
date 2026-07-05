"""Глобальный контекст шаблонов для приложения accounts."""

from .models import UserBalance


def user_balance(request):
    """Баланс оплаченных кредитов текущего пользователя (для navbar и др.)."""
    if not request.user.is_authenticated:
        return {'user_balance': None}

    balance, _ = UserBalance.objects.get_or_create(user=request.user)
    return {'user_balance': balance}
