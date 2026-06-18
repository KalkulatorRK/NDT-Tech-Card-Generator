"""Views for payment processing."""

import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import PaymentTransaction, TariffPlan
from .services import create_payment, process_webhook

logger = logging.getLogger(__name__)


def tariff_list(request):
    """Show available tariff plans."""
    tariffs = TariffPlan.objects.filter(is_active=True)
    user_quota = request.user.tech_card_quota if request.user.is_authenticated else 0
    return render(request, "payments/tariff_list.html", {
        "tariffs": tariffs,
        "user_quota": user_quota,
    })


@login_required
@require_POST
def initiate_payment(request, tariff_pk):
    """Start payment flow for the chosen tariff."""
    tariff = get_object_or_404(TariffPlan, pk=tariff_pk, is_active=True)
    try:
        transaction = create_payment(request.user, tariff, request)
        if transaction.yookassa_confirmation_url:
            return redirect(transaction.yookassa_confirmation_url)
        messages.error(request, _("Не удалось получить ссылку на оплату."))
    except RuntimeError as exc:
        messages.error(request, str(exc))
    return redirect("payments:tariffs")


@login_required
def payment_return(request, pk):
    """Return URL after YooKassa redirect."""
    transaction = get_object_or_404(PaymentTransaction, pk=pk, user=request.user)

    from django.conf import settings
    # In dev mode: auto-confirm
    if transaction.yookassa_payment_id.startswith("dev-"):
        transaction.on_payment_succeeded()
        messages.success(request, _(
            f"Оплата успешно подтверждена (тестовый режим). "
            f"Начислено {transaction.tariff.cards_count} разработок."
        ))
        return redirect("accounts:cabinet")

    # Check status from YooKassa
    if not settings.YOOKASSA_SHOP_ID:
        messages.info(request, _("Ожидается подтверждение оплаты."))
        return redirect("accounts:cabinet")

    try:
        import yookassa
        yookassa.Configuration.account_id = settings.YOOKASSA_SHOP_ID
        yookassa.Configuration.secret_key = settings.YOOKASSA_SECRET_KEY
        yk_payment = yookassa.Payment.find_one(transaction.yookassa_payment_id)
        if yk_payment.status == "succeeded":
            transaction.on_payment_succeeded()
            messages.success(request, _(f"Оплата прошла успешно! Начислено {transaction.tariff.cards_count} разработок."))
        else:
            messages.info(request, _(f"Статус платежа: {yk_payment.status}."))
    except Exception:
        messages.info(request, _("Статус платежа уточняется."))

    return redirect("accounts:cabinet")


@csrf_exempt
@require_POST
def yookassa_webhook(request):
    """Receive and process YooKassa webhook notifications."""
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    try:
        process_webhook(payload)
    except Exception:
        logger.exception("Webhook processing error")
        return HttpResponse(status=500)

    return HttpResponse(status=200)


@login_required
def payment_history(request):
    """User's payment history."""
    transactions = PaymentTransaction.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "payments/payment_history.html", {"transactions": transactions})
