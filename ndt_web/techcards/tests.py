"""
Тесты приложения «Технологические карты».

Проверяет модели, генератор карт и нормативные данные.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import TechCard, NormativeDocument
from .generator import RadiographicTechCardCalculator
from accounts.models import UserBalance
from normative.gost_50_05_07 import (
    get_sensitivity, get_sensitivity_mm, calc_geometric_unsharpness,
    calc_min_sfd, get_suitable_sources,
)
from normative.np_105_18 import assess_defect, assess_multiple_defects

User = get_user_model()


class NormativeDataTests(TestCase):
    """Тесты нормативных данных ГОСТ Р 50.05.07-2018."""

    def test_sensitivity_class_a_thin(self):
        """Класс А, малые толщины — 1.5%."""
        self.assertEqual(get_sensitivity(4.0, 'A'), 1.5)

    def test_sensitivity_class_a_medium(self):
        """Класс А, средние толщины (до 10 мм) — 1.0%."""
        self.assertEqual(get_sensitivity(8.0, 'A'), 1.0)

    def test_sensitivity_class_b_medium(self):
        """Класс В, 25–50 мм — 0.8%."""
        self.assertEqual(get_sensitivity(40.0, 'B'), 0.8)

    def test_sensitivity_class_c_thick(self):
        """Класс С, >100 мм — 0.8%."""
        self.assertEqual(get_sensitivity(150.0, 'C'), 0.8)

    def test_sensitivity_mm_calculation(self):
        """Размер выявляемого дефекта — правильная формула."""
        pct = get_sensitivity(10.0, 'A')  # 1.0%
        expected_mm = round(10.0 * pct / 100, 3)
        self.assertEqual(get_sensitivity_mm(10.0, 'A'), expected_mm)

    def test_geometric_unsharpness_formula(self):
        """Формула геометрической нерезкости: Ug = d*b/(f-b)."""
        ug = calc_geometric_unsharpness(2.0, 700, 5)
        expected = 2.0 * 5 / (700 - 5)
        self.assertAlmostEqual(ug, expected, places=3)

    def test_geometric_unsharpness_invalid_sfd(self):
        """SFD ≤ OFD должен вызвать ValueError."""
        with self.assertRaises(ValueError):
            calc_geometric_unsharpness(2.0, 100, 200)

    def test_min_sfd_class_a(self):
        """Минимальное SFD рассчитывается правильно для класса А."""
        # Ug_max = 0.3, OFD=5, d=2
        # SFD_min = 5*(2+0.3)/0.3 = 5*2.3/0.3 = 38.33...
        min_sfd = calc_min_sfd(2.0, 5.0, 'A')
        expected = 5 * (2.0 + 0.3) / 0.3
        self.assertAlmostEqual(min_sfd, round(expected, 1), places=1)

    def test_suitable_sources_iridium_range(self):
        """Иридий-192 появляется в диапазоне 20–100 мм."""
        sources = get_suitable_sources(30)
        codes = [s['code'] for s in sources]
        self.assertIn('Ir-192', codes)

    def test_suitable_sources_tm170_thin(self):
        """Тулий-170 появляется для тонких изделий."""
        sources = get_suitable_sources(5)
        codes = [s['code'] for s in sources]
        self.assertIn('Tm-170', codes)

    def test_suitable_sources_cobalt_thick(self):
        """Кобальт-60 для толстых изделий."""
        sources = get_suitable_sources(100)
        codes = [s['code'] for s in sources]
        self.assertIn('Co-60', codes)


class QualityAssessmentLogicTests(TestCase):
    """Тесты логики оценки качества НП-105-18."""

    def test_crack_always_rejected(self):
        """Трещина недопустима в любой категории."""
        result = assess_defect('crack', 'I', 10, size_1_mm=2.0)
        self.assertFalse(result['is_acceptable'])

    def test_lack_of_fusion_rejected(self):
        """Несплавление недопустимо."""
        result = assess_defect('lack_of_fusion', 'II', 15)
        self.assertFalse(result['is_acceptable'])

    def test_pore_acceptable_category_1(self):
        """Пора 0.5 мм при S=10 мм, категория I: max=1.0 мм → допустима."""
        result = assess_defect('pore', 'I', 10, size_1_mm=0.5)
        self.assertTrue(result['is_acceptable'])

    def test_pore_rejected_over_limit(self):
        """Пора 2.0 мм при S=10 мм, категория I: max=1.0 мм → недопустима."""
        result = assess_defect('pore', 'I', 10, size_1_mm=2.0)
        self.assertFalse(result['is_acceptable'])

    def test_pore_acceptable_category_3(self):
        """Пора 2.0 мм при S=20 мм, категория III: max=min(0.2*20,2.5)=2.5→доп."""
        result = assess_defect('pore', 'III', 20, size_1_mm=2.0)
        self.assertTrue(result['is_acceptable'])

    def test_undercut_depth_check(self):
        """Подрез: глубина 0.3 мм при S=10 мм, кат. I: max=0.5 мм → допустим."""
        result = assess_defect('undercut', 'I', 10, size_1_mm=0.3)
        self.assertTrue(result['is_acceptable'])

    def test_undercut_depth_over_limit(self):
        """Подрез: глубина 0.8 мм при S=5 мм, кат. I: max=0.25 мм → брак."""
        result = assess_defect('undercut', 'I', 5, size_1_mm=0.8)
        self.assertFalse(result['is_acceptable'])

    def test_multiple_defects_one_crack(self):
        """Одна трещина в наборе → общий вердикт БРАК."""
        defects = [
            {'type': 'crack', 'size_1': 5, 'size_2': 0, 'count': 1},
            {'type': 'pore', 'size_1': 0.5, 'size_2': 0, 'count': 1},
        ]
        result = assess_multiple_defects(defects, 'II', 10)
        self.assertFalse(result['is_acceptable'])
        self.assertEqual(result['verdict'], 'БРАК')

    def test_multiple_acceptable_defects(self):
        """Все допустимые дефекты → ГОДЕН."""
        defects = [
            {'type': 'pore', 'size_1': 0.3, 'size_2': 0, 'count': 1},
            {'type': 'undercut', 'size_1': 0.1, 'size_2': 0, 'count': 1},
        ]
        result = assess_multiple_defects(defects, 'II', 10)
        self.assertTrue(result['is_acceptable'])
        self.assertEqual(result['verdict'], 'ГОДЕН')


class TechCardCalculatorTests(TestCase):
    """Тесты вычислительного ядра генератора техкарт."""

    def setUp(self):
        self.base_input = {
            'organization': 'ТестОрг',
            'object_name': 'Трубопровод',
            'drawing_number': 'ТП-001',
            'weld_number': 'Ш-01',
            'card_number': 'ТК-001',
            'object_type': 'pipe',
            'material': '08Х18Н10Т',
            'wall_thickness': '10',
            'outer_diameter': '219.1',
            'weld_type': 'butt',
            'weld_category': 'I',
            'source_code': 'Ir-192',
            'focal_spot_mm': '2.0',
            'sfd_mm': '700',
            'ofd_mm': '5',
            'film_name': '',
            'inspector_name': '',
        }

    def test_sensitivity_class_for_cat_i(self):
        """Категория I → Класс А."""
        calc = RadiographicTechCardCalculator(self.base_input)
        params = calc.calculate()
        self.assertEqual(params['control_class'], 'A')

    def test_sensitivity_class_for_cat_ii(self):
        """Категория II → Класс В."""
        data = dict(self.base_input, weld_category='II')
        calc = RadiographicTechCardCalculator(data)
        params = calc.calculate()
        self.assertEqual(params['control_class'], 'B')

    def test_sensitivity_value_filled(self):
        """Значение чувствительности в % рассчитывается."""
        calc = RadiographicTechCardCalculator(self.base_input)
        params = calc.calculate()
        self.assertGreater(params['required_sensitivity_pct'], 0)
        self.assertGreater(params['required_sensitivity_mm'], 0)

    def test_geometric_unsharpness_computed(self):
        """Геометрическая нерезкость рассчитывается."""
        calc = RadiographicTechCardCalculator(self.base_input)
        params = calc.calculate()
        self.assertIn('geometric_unsharpness_mm', params)
        self.assertGreater(params['geometric_unsharpness_mm'], 0)

    def test_source_selected(self):
        """Источник излучения определяется."""
        calc = RadiographicTechCardCalculator(self.base_input)
        params = calc.calculate()
        self.assertIn('selected_source', params)
        self.assertTrue(params['selected_source'])

    def test_exposure_scheme_set(self):
        """Схема просвечивания определяется."""
        calc = RadiographicTechCardCalculator(self.base_input)
        params = calc.calculate()
        self.assertIn('exposure_scheme', params)
        self.assertTrue(params['exposure_scheme'])

    def test_no_errors_for_valid_input(self):
        """Корректные данные не генерируют ошибок."""
        calc = RadiographicTechCardCalculator(self.base_input)
        calc.calculate()
        self.assertEqual(len(calc.errors), 0)

    def test_warning_for_large_ug(self):
        """При большой нерезкости генерируется предупреждение."""
        data = dict(self.base_input, focal_spot_mm='5.0', sfd_mm='100', ofd_mm='50')
        calc = RadiographicTechCardCalculator(data)
        calc.calculate()
        # При SFD=100, OFD=50, d=5: Ug = 5*50/(100-50) = 5 >> 0.3 мм
        self.assertTrue(len(calc.warnings) > 0)


class NormativeDocumentModelTests(TestCase):
    """Тесты модели NormativeDocument."""

    def setUp(self):
        self.doc = NormativeDocument.objects.create(
            code='ГОСТ Р 50.05.07-2018',
            full_name='Радиографический контроль',
            control_method='RT',
            is_implemented=True,
            is_active=True,
        )

    def test_str_representation(self):
        """__str__ возвращает код документа."""
        self.assertEqual(str(self.doc), 'ГОСТ Р 50.05.07-2018')

    def test_method_display(self):
        """Метод контроля отображается корректно."""
        self.assertEqual(self.doc.get_control_method_display(), 'Радиографический контроль (РГК)')
