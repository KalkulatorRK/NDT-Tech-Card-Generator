"""Тесты расчётных модулей normative (порт логики KalkulatorRK2)."""

from datetime import date
from django.test import SimpleTestCase

from normative.calculations import (
    HALF_LIFE_DAYS,
    calc_remaining_activity,
    calc_scheme_5a,
    calc_geometric_unsharpness_full,
)


class RadioactivityTests(SimpleTestCase):
    def test_half_life_constants(self):
        self.assertEqual(HALF_LIFE_DAYS['Ir-192'], 73.83)
        self.assertEqual(HALF_LIFE_DAYS['Se-75'], 119.78)

    def test_decay_formula(self):
        result = calc_remaining_activity(
            'Ir-192', 10.0, '2024-01-01', '2024-01-01',
        )
        self.assertAlmostEqual(result['remaining_activity_ci'], 10.0, places=4)


class Scheme5aTests(SimpleTestCase):
    def test_n_from_f_over_d_table(self):
        """N выбирается по f/D, как в KalkulatorRK2, а не как min(N) из таблицы."""
        result = calc_scheme_5a(
            focal_spot_mm=2.0,
            d_outer_mm=200,
            d_inner_mm=180,
            sensitivity_mm=2.0,
        )
        self.assertIn('N', result)
        self.assertGreaterEqual(result['N'], 4)
        self.assertIsNotNone(result['f_min_mm'])


class GeometricUnsharpnessTests(SimpleTestCase):
    def test_ug_calculation(self):
        result = calc_geometric_unsharpness_full(2.0, 10.0, 700.0, sensitivity_mm=2.0)
        self.assertAlmostEqual(result['ug_mm'], 0.029, places=2)
        self.assertTrue(result['gost_ok'])
