"""Сервис управления подписками пользователей."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from payments.models import SubscriptionPlan, UserSubscription


def get_active_subscription(user) -> UserSubscription | None:
    """Возвращает текущую активную подписку пользователя или None."""
    now = timezone.now()
    sub = (
        UserSubscription.objects
        .filter(
            user=user,
            status=UserSubscription.STATUS_ACTIVE,
            period_start__lte=now,
            period_end__gt=now,
        )
        .select_related('plan')
        .order_by('-period_end')
        .first()
    )
    if sub:
        sub.expire_if_needed()
        if sub.is_current:
            return sub
    return None


def activate_subscription(user, plan: SubscriptionPlan) -> UserSubscription:
    """
    Активирует подписку после успешной оплаты.

    Предыдущие активные подписки переводятся в «истекла».
    """
    now = timezone.now()
    UserSubscription.objects.filter(
        user=user,
        status=UserSubscription.STATUS_ACTIVE,
    ).update(status=UserSubscription.STATUS_EXPIRED)

    return UserSubscription.objects.create(
        user=user,
        plan=plan,
        status=UserSubscription.STATUS_ACTIVE,
        period_start=now,
        period_end=now + timedelta(days=plan.duration_days),
        generations_used=0,
    )


def get_subscription_status(user) -> dict:
    """Сводка подписки для UI."""
    sub = get_active_subscription(user)
    if not sub:
        return {
            'active': False,
            'plan_name': '',
            'generations_used': 0,
            'generations_limit': 0,
            'generations_remaining': 0,
            'period_end': None,
        }
    return {
        'active': True,
        'plan_name': sub.plan.name,
        'generations_used': sub.generations_used,
        'generations_limit': sub.plan.generation_limit,
        'generations_remaining': sub.generations_remaining,
        'period_end': sub.period_end,
        'subscription': sub,
    }
