"""Unit tests for standards app models."""

from django.test import TestCase

from .models import NDTMethod, NormativeDocument


class NDTMethodTest(TestCase):
    def test_str_representation(self):
        method = NDTMethod(code="VT", name="Визуальный и измерительный")
        self.assertIn("VT", str(method))

    def test_method_code_choices(self):
        valid_codes = [c[0] for c in NDTMethod.Code.choices]
        self.assertIn("VT", valid_codes)
        self.assertIn("RT", valid_codes)
        self.assertIn("PT", valid_codes)
        self.assertIn("LT", valid_codes)


class NormativeDocumentTest(TestCase):
    def setUp(self):
        self.method = NDTMethod.objects.create(
            code="RT", name="Радиографический"
        )

    def test_str_representation(self):
        doc = NormativeDocument.objects.create(
            method=self.method,
            code="ГОСТ 7512-82",
            name="Радиографический метод",
        )
        self.assertIn("ГОСТ 7512-82", str(doc))

    def test_get_data_module_returns_none_without_path(self):
        doc = NormativeDocument(method=self.method, code="TEST", name="Test doc")
        self.assertIsNone(doc.get_data_module())

    def test_get_data_module_returns_module(self):
        doc = NormativeDocument.objects.create(
            method=self.method,
            code="ГОСТ 7512-82",
            name="Test",
            data_module="ndt_data.gost_7512",
        )
        module = doc.get_data_module()
        self.assertIsNotNone(module)
        self.assertTrue(callable(module.generate_card_data))
