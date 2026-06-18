"""
Payment models: tariff plans and transaction records.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class TariffPlan(models.Model):
    """Pre-defined tariff: N tech cards for P roubles."""

    cards_count = models.PositiveIntegerField(verbose_name=_("Количество техкарт"))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Цена (руб.)"))
    is_active = models.BooleanField(default=True, verbose_name=_("Активен"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("Порядок отображения"))

    class Meta:
        verbose_name = _("Тарифный план")
        verbose_name_plural = _("Тарифные планы")
        ordering = ["sort_order", "cards_count"]

    def __str__(self):
        return f"{self.cards_count} техкарт — {self.price} руб."

    @property
    def price_per_card(self) -> Decimal:
        if self.cards_count:
            return (self.price / self.cards_count).quantize(Decimal("0.01"))
        return self.price


class PaymentTransaction(models.Model):
    """Records a single payment attempt and its outcome."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Ожидает оплаты")
        SUCCEEDED = "succeeded", _("Оплачено")
        CANCELED = "canceled", _("Отменено")
        FAILED = "failed", _("Ошибка")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name=_("Пользователь"),
    )
    tariff = models.ForeignKey(
        TariffPlan,
        on_delete=models.PROTECT,
        verbose_name=_("Тариф"),
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Сумма (руб.)"))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Статус"),
    )
    yookassa_payment_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("ID платежа ЮKassa"),
    )
    yookassa_confirmation_url = models.URLField(
        blank=True,
        verbose_name=_("Ссылка на оплату"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    class Meta:
        verbose_name = _("Транзакция")
        verbose_name_plural = _("Транзакции")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.tariff} — {self.status}"

    def on_payment_succeeded(self):
        """Credit the user's quota after successful payment."""
        if self.status != self.Status.SUCCEEDED:
            self.status = self.Status.SUCCEEDED
            self.save(update_fields=["status", "updated_at"])
            self.user.add_quota(self.tariff.cards_count)
