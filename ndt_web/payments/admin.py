"""Административная панель для «Платежей»."""

from django.contrib import admin

from .models import SubscriptionPlan, UserSubscription, Payment


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'duration_days', 'generation_limit', 'price',
        'price_per_generation', 'is_popular', 'is_active',
    )
    list_editable = ('is_popular', 'is_active')
    search_fields = ('name', 'description')


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'plan', 'status', 'generations_used',
        'period_start', 'period_end', 'created_at',
    )
    list_filter = ('status', 'plan')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'period_end'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'plan', 'amount', 'status', 'created_at', 'completed_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'yookassa_payment_id')
    readonly_fields = ('created_at', 'completed_at', 'yookassa_payment_id')
    date_hierarchy = 'created_at'
