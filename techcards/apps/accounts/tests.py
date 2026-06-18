"""Unit tests for the accounts app (models and views)."""

from django.test import TestCase, Client
from django.urls import reverse

from .models import FreeCardUsage, User


class UserModelTest(TestCase):
    """Tests for the custom User model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            tech_card_quota=5,
        )

    def test_user_str(self):
        self.assertIn("testuser", str(self.user))

    def test_add_quota(self):
        initial_quota = self.user.tech_card_quota
        self.user.add_quota(3)
        self.user.refresh_from_db()
        self.assertEqual(self.user.tech_card_quota, initial_quota + 3)

    def test_consume_quota_success(self):
        initial_quota = self.user.tech_card_quota
        result = self.user.consume_quota()
        self.assertTrue(result)
        self.user.refresh_from_db()
        self.assertEqual(self.user.tech_card_quota, initial_quota - 1)

    def test_consume_quota_zero_returns_false(self):
        self.user.tech_card_quota = 0
        self.user.save()
        result = self.user.consume_quota()
        self.assertFalse(result)

    def test_is_admin_property(self):
        self.assertFalse(self.user.is_admin)
        self.user.role = User.Role.ADMIN
        self.assertTrue(self.user.is_admin)

    def test_default_role_is_user(self):
        new_user = User.objects.create_user(username="user2", password="pass")
        self.assertEqual(new_user.role, User.Role.USER)


class FreeCardUsageTest(TestCase):
    """Tests for free card usage tracking."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser2", password="pass")

    def test_has_used_free_false_initially(self):
        self.assertFalse(FreeCardUsage.has_used_free(self.user, "ГОСТ 7512-82"))

    def test_has_used_free_true_after_creation(self):
        FreeCardUsage.objects.create(user=self.user, normative_doc_code="ГОСТ 7512-82")
        self.assertTrue(FreeCardUsage.has_used_free(self.user, "ГОСТ 7512-82"))

    def test_unique_constraint(self):
        FreeCardUsage.objects.create(user=self.user, normative_doc_code="ГОСТ 7512-82")
        with self.assertRaises(Exception):
            FreeCardUsage.objects.create(user=self.user, normative_doc_code="ГОСТ 7512-82")


class CabinetViewTest(TestCase):
    """Tests for personal cabinet view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="cabuser", password="pass123")
        self.url = reverse("accounts:cabinet")

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/accounts/login/?next={self.url}")

    def test_cabinet_accessible_for_authenticated_user(self):
        self.client.login(username="cabuser", password="pass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Личный кабинет")

    def test_cabinet_shows_quota(self):
        self.user.tech_card_quota = 7
        self.user.save()
        self.client.login(username="cabuser", password="pass123")
        response = self.client.get(self.url)
        self.assertContains(response, "7")
