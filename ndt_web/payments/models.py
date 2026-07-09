"""
Модели приложения «Платежи».

Подписки с лимитом генераций техкарт и история платежей.
"""

from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.utils import timezone

from accounts.models import CustomUser


class SubscriptionPlan(models.Model):
    """Тарифный план-подписка с лимитом генераций за период."""

    name = models.CharField(max_length=100, verbose_name='Название')
    duration_days = models.PositiveIntegerField(
        default=30,
        verbose_name='Длительность, дней',
        help_text='Например, 30 — подписка на 1 месяц',
    )
    generation_limit = models.PositiveIntegerField(
        verbose_name='Лимит генераций за период',
        help_text='Сколько техкарт можно создать за срок подписки',
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Цена, руб.',
    )
    description = models.CharField(max_length=300, blank=True, verbose_name='Описание')
    is_popular = models.BooleanField(default=False, verbose_name='Популярный')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'План подписки'
        verbose_name_plural = 'Планы подписки'
        ordering = ['price']

    def __str__(self):
        return f'{self.name} — {self.generation_limit} ген./{self.duration_days} дн.'

    @property
    def duration_label(self) -> str:
        if self.duration_days == 30:
            return '1 месяц'
        if self.duration_days == 90:
            return '3 месяца'
        if self.duration_days == 365:
            return '1 год'
        return f'{self.duration_days} дн.'

    @property
    def price_per_generation(self):
        if self.generation_limit:
            return round(self.price / self.generation_limit, 2)
        return self.price


class UserSubscription(models.Model):
    """Активная или завершённая подписка пользователя."""

    STATUS_ACTIVE = 'active'
    STATUS_EXPIRED = 'expired'
    STATUS_CANCELED = 'canceled'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Активна'),
        (STATUS_EXPIRED, 'Истекла'),
        (STATUS_CANCELED, 'Отменена'),
    ]

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='subscriptions',
        verbose_name='Пользователь',
    )
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.PROTECT, related_name='user_subscriptions',
        verbose_name='План подписки',
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE,
        verbose_name='Статус',
    )
    period_start = models.DateTimeField(verbose_name='Начало периода')
    period_end = models.DateTimeField(verbose_name='Окончание периода')
    generations_used = models.PositiveIntegerField(
        default=0, verbose_name='Использовано генераций в периоде',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Подписка пользователя'
        verbose_name_plural = 'Подписки пользователей'
        ordering = ['-period_end']

    def __str__(self):
        return f'{self.user} — {self.plan.name} ({self.get_status_display()})'

    @property
    def is_current(self) -> bool:
        now = timezone.now()
        return (
            self.status == self.STATUS_ACTIVE
            and self.period_start <= now < self.period_end
        )

    @property
    def generations_remaining(self) -> int:
        if not self.is_current:
            return 0
        return max(0, self.plan.generation_limit - self.generations_used)

    def record_generation(self) -> None:
        self.generations_used += 1
        self.save(update_fields=['generations_used', 'updated_at'])

    def expire_if_needed(self) -> None:
        if self.status == self.STATUS_ACTIVE and timezone.now() >= self.period_end:
            self.status = self.STATUS_EXPIRED
            self.save(update_fields=['status', 'updated_at'])


class Payment(models.Model):
    """Запись о платеже за подписку."""

    STATUS_PENDING = 'pending'
    STATUS_SUCCEEDED = 'succeeded'
    STATUS_CANCELED = 'canceled'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Ожидает оплаты'),
        (STATUS_SUCCEEDED, 'Оплачено'),
        (STATUS_CANCELED, 'Отменено'),
    ]

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='payments',
        verbose_name='Пользователь',
    )
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.PROTECT,
        verbose_name='План подписки',
    )
    subscription = models.ForeignKey(
        UserSubscription, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='payments',
        verbose_name='Активированная подписка',
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Сумма, руб.',
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_PENDING, verbose_name='Статус',
    )
    yookassa_payment_id = models.CharField(
        max_length=200, blank=True, verbose_name='ID платежа ЮKassa',
    )
    yookassa_confirmation_url = models.URLField(
        max_length=500, blank=True, verbose_name='URL подтверждения',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата завершения')

    class Meta:
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']

    def __str__(self):
        return f'Платёж #{self.pk} — {self.user} — {self.amount} руб. ({self.get_status_display()})'


# Обратная совместимость для старого кода и миграций данных
TariffPlan = SubscriptionPlan
