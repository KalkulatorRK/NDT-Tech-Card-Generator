from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import PaymentTransaction, TariffPlan


@admin.register(TariffPlan)
class TariffPlanAdmin(admin.ModelAdmin):
    list_display = ("cards_count", "price", "price_per_card", "is_active", "sort_order")
    list_editable = ("price", "is_active", "sort_order")
    ordering = ("sort_order",)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "tariff", "amount", "status", "yookassa_payment_id", "created_at")
    list_filter = ("status",)
    search_fields = ("user__username", "user__email", "yookassa_payment_id")
    readonly_fields = ("created_at", "updated_at", "yookassa_payment_id", "yookassa_confirmation_url")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    actions = ["mark_succeeded"]

    @admin.action(description=_("Подтвердить платёж вручную"))
    def mark_succeeded(self, request, queryset):
        for tx in queryset.filter(status=PaymentTransaction.Status.PENDING):
            tx.on_payment_succeeded()
        self.message_user(request, _("Выбранные платежи подтверждены."))
