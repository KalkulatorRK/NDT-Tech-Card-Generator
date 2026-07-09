"""
Представления приложения «Платежи».

Страница подписок, оплата через ЮKassa.
"""

import json
import uuid
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone

from .models import SubscriptionPlan, Payment
from accounts.models import UserBalance
from accounts.subscriptions import activate_subscription, get_subscription_status

logger = logging.getLogger(__name__)


def _fulfill_payment(payment: Payment) -> None:
    """Активирует подписку после успешной оплаты."""
    if payment.status == Payment.STATUS_SUCCEEDED and payment.subscription_id:
        return
    subscription = activate_subscription(payment.user, payment.plan)
    payment.subscription = subscription
    payment.status = Payment.STATUS_SUCCEEDED
    payment.completed_at = timezone.now()
    payment.save(update_fields=['subscription', 'status', 'completed_at'])


def tariffs_view(request):
    """Страница выбора плана подписки."""
    plans = SubscriptionPlan.objects.filter(is_active=True)
    subscription_status = None
    if request.user.is_authenticated:
        UserBalance.objects.get_or_create(user=request.user)
        subscription_status = get_subscription_status(request.user)

    return render(request, 'payments/tariffs.html', {
        'plans': plans,
        'subscription_status': subscription_status,
    })


@login_required
def checkout_view(request, tariff_id):
    """
    Инициация платежа через ЮKassa.

    Если ЮKassa не настроена — симулируем успешный платёж (для тестирования).
    """
    plan = get_object_or_404(SubscriptionPlan, pk=tariff_id, is_active=True)

    if request.method == 'POST':
        payment = Payment.objects.create(
            user=request.user,
            plan=plan,
            amount=plan.price,
            status=Payment.STATUS_PENDING,
        )

        yookassa_configured = bool(settings.YOOKASSA_SHOP_ID and settings.YOOKASSA_SECRET_KEY)

        if yookassa_configured:
            try:
                payment_result = _create_yookassa_payment(
                    payment=payment,
                    plan=plan,
                    return_url=f"{settings.SITE_URL}/payments/success/{payment.pk}/",
                )
                if payment_result.get('confirmation_url'):
                    payment.yookassa_payment_id = payment_result['payment_id']
                    payment.yookassa_confirmation_url = payment_result['confirmation_url']
                    payment.save()
                    return redirect(payment_result['confirmation_url'])
            except Exception as e:
                logger.error(f'ЮKassa error: {e}')
                messages.error(request, f'Ошибка при создании платежа: {e}')
                payment.status = Payment.STATUS_CANCELED
                payment.save()
                return redirect('tariffs')
        else:
            logger.warning('ЮKassa не настроена. Используется тестовый режим.')
            _fulfill_payment(payment)
            messages.success(
                request,
                f'Тестовая оплата прошла успешно! Подписка «{plan.name}» активирована '
                f'({plan.generation_limit} генераций на {plan.duration_label}).',
            )
            return redirect('cabinet')

    return render(request, 'payments/checkout.html', {'plan': plan})


@login_required
def payment_success_view(request, payment_id):
    """Страница успешного платежа (callback от ЮKassa)."""
    payment = get_object_or_404(Payment, pk=payment_id, user=request.user)

    if payment.status == Payment.STATUS_SUCCEEDED:
        messages.success(request, 'Оплата прошла успешно!')
    elif payment.status == Payment.STATUS_PENDING:
        if _check_yookassa_payment(payment):
            _fulfill_payment(payment)
            messages.success(
                request,
                f'Оплата подтверждена! Подписка «{payment.plan.name}» активирована.',
            )
        else:
            messages.warning(request, 'Платёж ещё обрабатывается. Попробуйте позже.')

    return redirect('cabinet')


@csrf_exempt
@require_POST
def yookassa_webhook_view(request):
    """Webhook для получения уведомлений от ЮKassa."""
    try:
        body = json.loads(request.body)
        event_type = body.get('event')

        if event_type == 'payment.succeeded':
            payment_data = body.get('object', {})
            yookassa_id = payment_data.get('id')

            try:
                payment = Payment.objects.get(yookassa_payment_id=yookassa_id)
                if payment.status != Payment.STATUS_SUCCEEDED:
                    _fulfill_payment(payment)
                    logger.info(
                        'Подписка «%s» активирована для %s',
                        payment.plan.name, payment.user,
                    )
            except Payment.DoesNotExist:
                logger.warning(f'Платёж ЮKassa {yookassa_id} не найден в базе.')

        elif event_type == 'payment.canceled':
            payment_data = body.get('object', {})
            yookassa_id = payment_data.get('id')
            Payment.objects.filter(
                yookassa_payment_id=yookassa_id,
                status=Payment.STATUS_PENDING,
            ).update(status=Payment.STATUS_CANCELED)

    except json.JSONDecodeError:
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f'Ошибка обработки webhook ЮKassa: {e}')
        return HttpResponse(status=500)

    return HttpResponse(status=200)


def _create_yookassa_payment(payment: Payment, plan: SubscriptionPlan, return_url: str) -> dict:
    try:
        import yookassa
        from yookassa import Configuration, Payment as YKPayment

        Configuration.configure(
            account_id=settings.YOOKASSA_SHOP_ID,
            secret_key=settings.YOOKASSA_SECRET_KEY,
        )

        idempotence_key = str(uuid.uuid4())
        payment_obj = YKPayment.create({
            'amount': {
                'value': str(plan.price),
                'currency': 'RUB',
            },
            'confirmation': {
                'type': 'redirect',
                'return_url': return_url,
            },
            'capture': True,
            'description': (
                f'Карта-НК: подписка «{plan.name}» '
                f'({plan.generation_limit} ген./{plan.duration_label})'
            ),
            'metadata': {
                'payment_db_id': str(payment.pk),
                'user_id': str(payment.user.pk),
                'plan_id': str(plan.pk),
            },
        }, idempotence_key)

        return {
            'payment_id': payment_obj.id,
            'confirmation_url': payment_obj.confirmation.confirmation_url,
        }
    except ImportError:
        raise RuntimeError('Библиотека yookassa не установлена. Выполните: pip install yookassa')


def _check_yookassa_payment(payment: Payment) -> bool:
    try:
        import yookassa
        from yookassa import Configuration, Payment as YKPayment

        Configuration.configure(
            account_id=settings.YOOKASSA_SHOP_ID,
            secret_key=settings.YOOKASSA_SECRET_KEY,
        )
        yk_payment = YKPayment.find_one(payment.yookassa_payment_id)

        if yk_payment.status == 'succeeded':
            return True
    except Exception as e:
        logger.error(f'Ошибка проверки статуса ЮKassa: {e}')

    return False
