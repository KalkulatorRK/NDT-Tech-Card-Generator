"""Unit tests for the cards app (models, services, views)."""

from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import FreeCardUsage, User
from apps.standards.models import NDTMethod, NormativeDocument
from .models import TechCard
from .services import can_create_card


class TechCardModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="carduser", password="pass")
        method = NDTMethod.objects.create(code="RT", name="Радиографический")
        self.doc = NormativeDocument.objects.create(
            method=method, code="ГОСТ 7512-82", name="Тест"
        )

    def test_str_representation(self):
        card = TechCard.objects.create(
            user=self.user,
            normative_doc=self.doc,
            title="Тестовая карта",
        )
        self.assertIn("Тестовая карта", str(card))

    def test_default_status_is_pending(self):
        card = TechCard(
            user=self.user, normative_doc=self.doc, title="Test"
        )
        self.assertEqual(card.status, TechCard.Status.PENDING)


class CanCreateCardServiceTest(TestCase):
    def setUp(self):
        method = NDTMethod.objects.create(code="VT", name="Визуальный")
        self.doc = NormativeDocument.objects.create(
            method=method, code="РД 03-606-03", name="Test"
        )
        self.user = User.objects.create_user(username="svcuser", password="pass", tech_card_quota=0)

    def test_anonymous_user_cannot_create(self):
        anonymous = MagicMock()
        anonymous.is_authenticated = False
        allowed, reason, is_free = can_create_card(anonymous, self.doc)
        self.assertFalse(allowed)

    def test_free_card_allowed_on_first_use(self):
        allowed, reason, is_free = can_create_card(self.user, self.doc)
        self.assertTrue(allowed)
        self.assertTrue(is_free)

    def test_no_quota_and_used_free_denied(self):
        FreeCardUsage.objects.create(user=self.user, normative_doc_code=self.doc.code)
        allowed, reason, is_free = can_create_card(self.user, self.doc)
        self.assertFalse(allowed)
        self.assertFalse(is_free)

    def test_with_quota_and_used_free_allowed(self):
        FreeCardUsage.objects.create(user=self.user, normative_doc_code=self.doc.code)
        self.user.tech_card_quota = 3
        self.user.save()
        allowed, reason, is_free = can_create_card(self.user, self.doc)
        self.assertTrue(allowed)
        self.assertFalse(is_free)


class CardWizardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="wizuser", password="pass")
        method = NDTMethod.objects.create(code="RT", name="Радиографический")
        self.doc = NormativeDocument.objects.create(
            method=method,
            code="ГОСТ 7512-82",
            name="Test",
            data_module="ndt_data.gost_7512",
            is_active=True,
            has_card_template=True,
        )
        self.step1_url = reverse("cards:wizard_step1")

    def test_step1_requires_login(self):
        response = self.client.get(self.step1_url)
        self.assertRedirects(response, f"/accounts/login/?next={self.step1_url}")

    def test_step1_renders_for_authenticated(self):
        self.client.login(username="wizuser", password="pass")
        response = self.client.get(self.step1_url)
        self.assertEqual(response.status_code, 200)

    def test_step1_post_redirects_to_step2(self):
        self.client.login(username="wizuser", password="pass")
        response = self.client.post(self.step1_url, {"normative_doc": self.doc.pk})
        self.assertRedirects(
            response, reverse("cards:wizard_step2", kwargs={"doc_id": self.doc.pk})
        )

    def test_step2_renders(self):
        self.client.login(username="wizuser", password="pass")
        response = self.client.get(
            reverse("cards:wizard_step2", kwargs={"doc_id": self.doc.pk})
        )
        self.assertEqual(response.status_code, 200)


class CardExampleViewTest(TestCase):
    def test_example_accessible_without_login(self):
        client = Client()
        response = client.get(reverse("cards:card_example"))
        self.assertEqual(response.status_code, 200)
