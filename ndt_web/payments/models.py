"""
Модели приложения «Платежи».

Тарифные планы, история платежей.
"""

from django.db import models
from accounts.models import CustomUser


class TariffPlan(models.Model):
    """Тарифный план для покупки кредитов на создание техкарт."""

    cards_count = models.IntegerField(verbose_name='Количество кредитов')
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Цена, руб.',
    )
    description = models.CharField(max_length=200, blank=True, verbose_name='Описание')
    is_popular = models.BooleanField(default=False, verbose_name='Популярный')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Тарифный план'
        verbose_name_plural = 'Тарифные планы'
        ordering = ['cards_count']

    def __str__(self):
        return f'{self.cards_count} кред. — {self.price} руб.'

    @property
    def price_per_card(self):
        """Цена за один кредит."""
        if self.cards_count:
            return round(self.price / self.cards_count, 2)
        return self.price


class Payment(models.Model):
    """Запись о платеже пользователя."""

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
    tariff = models.ForeignKey(
        TariffPlan, on_delete=models.PROTECT,
        verbose_name='Тарифный план',
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
