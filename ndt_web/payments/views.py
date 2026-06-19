"""
Представления приложения «Платежи».

Отображение тарифов, инициация и подтверждение платежа.
Интеграция с ЮKassa (заглушка — настраивается через переменные окружения).
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

from .models import TariffPlan, Payment
from accounts.models import UserBalance

logger = logging.getLogger(__name__)


def tariffs_view(request):
    """Страница выбора тарифного плана."""
    tariffs = TariffPlan.objects.filter(is_active=True)
    user_balance = None
    if request.user.is_authenticated:
        user_balance, _ = UserBalance.objects.get_or_create(user=request.user)

    return render(request, 'payments/tariffs.html', {
        'tariffs': tariffs,
        'user_balance': user_balance,
    })


@login_required
def checkout_view(request, tariff_id):
    """
    Инициация платежа через ЮKassa.

    Если ЮKassa не настроена — симулируем успешный платёж (для тестирования).
    """
    tariff = get_object_or_404(TariffPlan, pk=tariff_id, is_active=True)

    if request.method == 'POST':
        # Создаём запись о платеже
        payment = Payment.objects.create(
            user=request.user,
            tariff=tariff,
            amount=tariff.price,
            status=Payment.STATUS_PENDING,
        )

        yookassa_configured = bool(settings.YOOKASSA_SHOP_ID and settings.YOOKASSA_SECRET_KEY)

        if yookassa_configured:
            # Реальная интеграция ЮKassa
            try:
                payment_result = _create_yookassa_payment(
                    payment=payment,
                    tariff=tariff,
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
            # Тестовый режим: автоматически подтверждаем платёж
            logger.warning('ЮKassa не настроена. Используется тестовый режим.')
            payment.status = Payment.STATUS_SUCCEEDED
            payment.completed_at = timezone.now()
            payment.yookassa_payment_id = f'test_{uuid.uuid4().hex[:10]}'
            payment.save()

            # Начисляем кредиты
            balance, _ = UserBalance.objects.get_or_create(user=request.user)
            balance.add_credits(tariff.cards_count)

            messages.success(
                request,
                f'Тестовый платёж выполнен успешно! '
                f'На ваш счёт зачислено {tariff.cards_count} операций.'
            )
            return redirect('cabinet')

    return render(request, 'payments/checkout.html', {'tariff': tariff})


@login_required
def payment_success_view(request, payment_id):
    """Страница успешного платежа (callback от ЮKassa)."""
    payment = get_object_or_404(Payment, pk=payment_id, user=request.user)

    if payment.status == Payment.STATUS_SUCCEEDED:
        messages.success(request, 'Оплата прошла успешно!')
    elif payment.status == Payment.STATUS_PENDING:
        # Проверяем статус через API ЮKassa
        if _check_yookassa_payment(payment):
            balance, _ = UserBalance.objects.get_or_create(user=request.user)
            balance.add_credits(payment.tariff.cards_count)
            messages.success(
                request,
                f'Оплата подтверждена! Начислено {payment.tariff.cards_count} операций.'
            )
        else:
            messages.warning(request, 'Платёж ещё обрабатывается. Попробуйте позже.')

    return redirect('cabinet')


@csrf_exempt
@require_POST
def yookassa_webhook_view(request):
    """
    Webhook для получения уведомлений от ЮKassa об изменении статуса платежа.
    """
    try:
        body = json.loads(request.body)
        event_type = body.get('event')

        if event_type == 'payment.succeeded':
            payment_data = body.get('object', {})
            yookassa_id = payment_data.get('id')

            try:
                payment = Payment.objects.get(yookassa_payment_id=yookassa_id)
                if payment.status != Payment.STATUS_SUCCEEDED:
                    payment.status = Payment.STATUS_SUCCEEDED
                    payment.completed_at = timezone.now()
                    payment.save()

                    # Начисляем кредиты
                    balance, _ = UserBalance.objects.get_or_create(user=payment.user)
                    balance.add_credits(payment.tariff.cards_count)
                    logger.info(f'Начислено {payment.tariff.cards_count} операций для {payment.user}')

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


def _create_yookassa_payment(payment: Payment, tariff: TariffPlan, return_url: str) -> dict:
    """
    Создаёт платёж в ЮKassa.

    Требуется установка библиотеки yookassa:
    pip install yookassa

    :param payment: объект Payment
    :param tariff: объект TariffPlan
    :param return_url: URL для возврата после оплаты
    :return: словарь с payment_id и confirmation_url
    """
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
                'value': str(tariff.price),
                'currency': 'RUB',
            },
            'confirmation': {
                'type': 'redirect',
                'return_url': return_url,
            },
            'capture': True,
            'description': f'НК-Карта: {tariff.cards_count} операций ({tariff.price} руб.)',
            'metadata': {
                'payment_db_id': str(payment.pk),
                'user_id': str(payment.user.pk),
                'tariff_id': str(tariff.pk),
            },
        }, idempotence_key)

        return {
            'payment_id': payment_obj.id,
            'confirmation_url': payment_obj.confirmation.confirmation_url,
        }
    except ImportError:
        raise RuntimeError('Библиотека yookassa не установлена. Выполните: pip install yookassa')


def _check_yookassa_payment(payment: Payment) -> bool:
    """
    Проверяет статус платежа в ЮKassa.

    :param payment: объект Payment
    :return: True, если платёж подтверждён
    """
    try:
        import yookassa
        from yookassa import Configuration, Payment as YKPayment

        Configuration.configure(
            account_id=settings.YOOKASSA_SHOP_ID,
            secret_key=settings.YOOKASSA_SECRET_KEY,
        )
        yk_payment = YKPayment.find_one(payment.yookassa_payment_id)

        if yk_payment.status == 'succeeded':
            payment.status = Payment.STATUS_SUCCEEDED
            payment.completed_at = timezone.now()
            payment.save()
            return True
    except Exception as e:
        logger.error(f'Ошибка проверки статуса ЮKassa: {e}')

    return False
