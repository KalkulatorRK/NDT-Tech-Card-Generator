"""
Payment processing service using YooKassa SDK.

YooKassa credentials are set via YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY
environment variables.
"""

import logging
import uuid

from django.conf import settings
from django.urls import reverse

from .models import PaymentTransaction, TariffPlan

logger = logging.getLogger(__name__)


def _get_yookassa_client():
    """Configure and return the YooKassa Configuration object."""
    import yookassa
    yookassa.Configuration.account_id = settings.YOOKASSA_SHOP_ID
    yookassa.Configuration.secret_key = settings.YOOKASSA_SECRET_KEY
    return yookassa


def create_payment(user, tariff: TariffPlan, request) -> PaymentTransaction:
    """
    Create a YooKassa payment and return the transaction record.

    The caller should redirect the user to transaction.yookassa_confirmation_url.
    """
    transaction = PaymentTransaction.objects.create(
        user=user,
        tariff=tariff,
        amount=tariff.price,
        status=PaymentTransaction.Status.PENDING,
    )

    return_url = request.build_absolute_uri(
        reverse("payments:payment_return", kwargs={"pk": transaction.pk})
    )

    if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
        # Development mode: simulate successful payment
        logger.warning("YooKassa not configured — simulating payment success.")
        transaction.yookassa_confirmation_url = return_url
        transaction.yookassa_payment_id = f"dev-{transaction.pk}"
        transaction.save()
        return transaction

    try:
        yk = _get_yookassa_client()
        payment = yk.Payment.create({
            "amount": {
                "value": str(tariff.price),
                "currency": "RUB",
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url,
            },
            "capture": True,
            "description": f"Тарифный план «{tariff}» для пользователя {user.username}",
            "metadata": {"transaction_id": str(transaction.pk)},
        }, str(uuid.uuid4()))

        transaction.yookassa_payment_id = payment.id
        transaction.yookassa_confirmation_url = payment.confirmation.confirmation_url
        transaction.save()
    except Exception as exc:
        logger.exception("YooKassa payment creation failed for transaction %s", transaction.pk)
        transaction.status = PaymentTransaction.Status.FAILED
        transaction.save()
        raise RuntimeError(f"Ошибка платёжной системы: {exc}") from exc

    return transaction


def process_webhook(payload: dict) -> None:
    """
    Handle YooKassa webhook notification.

    Expected payload format from YooKassa documentation.
    """
    event = payload.get("event")
    payment_obj = payload.get("object", {})
    payment_id = payment_obj.get("id")

    transaction = PaymentTransaction.objects.filter(yookassa_payment_id=payment_id).first()
    if not transaction:
        logger.warning("No transaction found for YooKassa payment_id=%s", payment_id)
        return

    if event == "payment.succeeded":
        transaction.on_payment_succeeded()
    elif event in ("payment.canceled", "payment.failed"):
        transaction.status = PaymentTransaction.Status.CANCELED
        transaction.save(update_fields=["status", "updated_at"])
