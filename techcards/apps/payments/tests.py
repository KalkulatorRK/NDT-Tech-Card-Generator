"""Unit tests for payments app."""

from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import User
from .models import PaymentTransaction, TariffPlan


class TariffPlanTest(TestCase):
    def test_str_representation(self):
        tariff = TariffPlan(cards_count=5, price=Decimal("800.00"))
        self.assertIn("5", str(tariff))
        self.assertIn("800", str(tariff))

    def test_price_per_card(self):
        tariff = TariffPlan(cards_count=5, price=Decimal("800.00"))
        self.assertEqual(tariff.price_per_card, Decimal("160.00"))


class PaymentTransactionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="payuser", password="pass", tech_card_quota=0)
        self.tariff = TariffPlan.objects.create(cards_count=3, price=Decimal("600.00"))

    def test_on_payment_succeeded_credits_quota(self):
        tx = PaymentTransaction.objects.create(
            user=self.user,
            tariff=self.tariff,
            amount=Decimal("600.00"),
            status=PaymentTransaction.Status.PENDING,
        )
        tx.on_payment_succeeded()
        self.user.refresh_from_db()
        self.assertEqual(self.user.tech_card_quota, 3)
        self.assertEqual(tx.status, PaymentTransaction.Status.SUCCEEDED)

    def test_on_payment_succeeded_idempotent(self):
        """Calling on_payment_succeeded twice should not double-credit quota."""
        tx = PaymentTransaction.objects.create(
            user=self.user,
            tariff=self.tariff,
            amount=Decimal("600.00"),
            status=PaymentTransaction.Status.SUCCEEDED,
        )
        tx.on_payment_succeeded()
        self.user.refresh_from_db()
        # Status already succeeded, so quota should NOT be added again
        self.assertEqual(self.user.tech_card_quota, 0)


class TariffListViewTest(TestCase):
    def test_tariff_list_accessible(self):
        client = Client()
        TariffPlan.objects.create(cards_count=1, price=Decimal("300"))
        response = client.get(reverse("payments:tariffs"))
        self.assertEqual(response.status_code, 200)

    def test_tariff_list_requires_login_for_payment(self):
        tariff = TariffPlan.objects.create(cards_count=1, price=Decimal("300"))
        client = Client()
        response = client.post(reverse("payments:pay", kwargs={"tariff_pk": tariff.pk}))
        self.assertEqual(response.status_code, 302)  # Redirect to login
