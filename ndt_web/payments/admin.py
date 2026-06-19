"""Административная панель для «Платежей»."""

from django.contrib import admin
from .models import TariffPlan, Payment


@admin.register(TariffPlan)
class TariffPlanAdmin(admin.ModelAdmin):
    list_display = ('cards_count', 'price', 'price_per_card', 'is_popular', 'is_active')
    list_editable = ('is_popular', 'is_active')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'tariff', 'amount', 'status', 'created_at', 'completed_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'yookassa_payment_id')
    readonly_fields = ('created_at', 'completed_at', 'yookassa_payment_id')
    date_hierarchy = 'created_at'
