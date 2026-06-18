"""Unit tests for the quality assessment app."""

from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import User
from apps.standards.models import NDTMethod, NormativeDocument


class QualityHomeViewTest(TestCase):
    def test_home_accessible_without_login(self):
        client = Client()
        response = client.get(reverse("quality:home"))
        self.assertEqual(response.status_code, 200)

    def test_home_shows_document_form(self):
        response = Client().get(reverse("quality:home"))
        self.assertContains(response, "Нормативный документ")


class QualityAssessViewTest(TestCase):
    def setUp(self):
        method = NDTMethod.objects.create(code="RT", name="Радиографический")
        self.doc = NormativeDocument.objects.create(
            method=method,
            code="ГОСТ 7512-82",
            name="Test",
            data_module="ndt_data.gost_7512",
            is_active=True,
            has_quality_criteria=True,
        )
        self.url = reverse("quality:assess", kwargs={"doc_id": self.doc.pk})

    def test_assess_page_accessible_for_guest(self):
        """Guests can access the assessment page (within 3 free uses)."""
        client = Client()
        session = client.session
        session.create()
        response = client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_assess_shows_criteria_table(self):
        client = Client()
        response = client.get(self.url)
        self.assertContains(response, "Тип дефекта")


class NDTDataModuleTest(TestCase):
    """Tests for ndt_data modules directly."""

    def test_gost_7512_generate_card_data(self):
        from ndt_data.gost_7512 import generate_card_data
        data = generate_card_data({
            "thickness_mm": 10,
            "weld_category": "II",
            "radiation_source": "Ir192",
            "object_type": "pipe",
        })
        self.assertIn("sensitivity_class", data)
        self.assertEqual(data["sensitivity_class"], "II")
        self.assertIn("sfd_min_mm", data)

    def test_gost_7512_evaluate_defect_crack(self):
        from ndt_data.gost_7512 import evaluate_defect
        result = evaluate_defect({"defect_type": "crack", "thickness_mm": 10, "size_mm": 0.5})
        self.assertEqual(result["result"], "unacceptable")

    def test_gost_7512_evaluate_defect_acceptable_pore(self):
        from ndt_data.gost_7512 import evaluate_defect
        result = evaluate_defect({
            "defect_type": "pore",
            "weld_category": "III",
            "thickness_mm": 10,
            "size_mm": 0.5,
            "count": 3,
        })
        self.assertEqual(result["result"], "acceptable")

    def test_rd_03_606_03_generate_card_data(self):
        from ndt_data.rd_03_606_03 import generate_card_data
        data = generate_card_data({
            "thickness_mm": 5,
            "weld_category": "I",
            "object_type": "pipe",
        })
        self.assertIn("allowable_undercut_depth_mm", data)
        self.assertEqual(data["allowable_undercut_depth_mm"], 0.1)

    def test_rd_03_606_03_evaluate_crack_unacceptable(self):
        from ndt_data.rd_03_606_03 import evaluate_defect
        result = evaluate_defect({"defect_type": "crack", "weld_category": "I", "size_mm": 0})
        self.assertEqual(result["result"], "unacceptable")

    def test_get_quality_criteria_not_empty(self):
        from ndt_data.gost_7512 import get_quality_criteria
        criteria = get_quality_criteria()
        self.assertGreater(len(criteria), 0)
