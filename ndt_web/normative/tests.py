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


class NP105AcceptanceCriteriaTests(SimpleTestCase):
    """Таблицы 4.8–4.11 и выбор норм для п. 10.2 техкарты."""

    def test_steel_category_ii_uses_table_48(self):
        from normative.np_105_18 import resolve_acceptance_table, lookup_acceptance_criteria
        self.assertEqual(resolve_acceptance_table('steel', 'II'), '4.8')
        row = lookup_acceptance_criteria('steel', 'II', 20.0)
        self.assertEqual(row['table'], '4.8')
        self.assertEqual(row['max_inclusion_mm'], 2.5)

    def test_steel_category_iin_uses_table_49(self):
        from normative.np_105_18 import resolve_acceptance_table, lookup_acceptance_criteria
        self.assertEqual(resolve_acceptance_table('steel', 'IIн'), '4.9')
        row = lookup_acceptance_criteria('steel', 'IIн', 20.0)
        self.assertEqual(row['table'], '4.9')
        self.assertEqual(row['max_inclusion_mm'], 1.2)

    def test_aluminum_uses_table_410(self):
        from normative.np_105_18 import resolve_acceptance_table, lookup_acceptance_criteria
        self.assertEqual(resolve_acceptance_table('aluminum', 'II'), '4.10')
        row = lookup_acceptance_criteria('aluminum', 'II', 20.0)
        self.assertEqual(row['table'], '4.10')
        self.assertEqual(row['max_length_100mm'], 18.0)

    def test_titanium_uses_table_411(self):
        from normative.np_105_18 import resolve_acceptance_table, lookup_acceptance_criteria
        self.assertEqual(resolve_acceptance_table('titanium', 'I'), '4.11')
        row = lookup_acceptance_criteria('titanium', 'I', 20.0)
        self.assertEqual(row['table'], '4.11')
        self.assertEqual(row['max_length_100mm'], 3.6)

    def test_docx_data_for_steel_iii_20mm(self):
        from normative.np_105_18 import build_acceptance_criteria_docx_data
        data = build_acceptance_criteria_docx_data('steel', 'III', 20.0)
        self.assertEqual(data['table_ref'], '4.8')
        self.assertIn('таблица N 4.8', data['intro'])
        self.assertEqual(len(data['headers']), 9)
        self.assertEqual(len(data['row_values']), 9)
        self.assertEqual(data['row_values'][2], '3')

    def test_weld_category_choices_steel_includes_in(self):
        from normative.np_105_18 import get_weld_category_choices
        codes = [c[0] for c in get_weld_category_choices('steel')]
        self.assertIn('Iн', codes)
        self.assertIn('IIн', codes)

    def test_weld_category_choices_aluminum_excludes_in(self):
        from normative.np_105_18 import get_weld_category_choices
        codes = [c[0] for c in get_weld_category_choices('aluminum')]
        self.assertNotIn('Iн', codes)
        self.assertIn('III', codes)

    def test_weld_category_choices_titanium_excludes_in(self):
        from normative.np_105_18 import get_weld_category_choices
        codes = [c[0] for c in get_weld_category_choices('titanium')]
        self.assertNotIn('Iн', codes)
        self.assertEqual(codes, ['I', 'II', 'III'])

    def test_resolve_material_type_for_categories_titanium(self):
        from normative.np_105_18 import resolve_material_type_for_categories
        from normative.gost_59023_2 import MATERIAL_TITANIUM

        self.assertEqual(
            resolve_material_type_for_categories(MATERIAL_TITANIUM, 'ВТ6', 'III'),
            'titanium',
        )
        self.assertEqual(
            resolve_material_type_for_categories(MATERIAL_TITANIUM, 'ВТ6', 'Iн'),
            'titanium',
        )

    def test_resolve_material_type_for_categories_aluminum(self):
        from normative.np_105_18 import resolve_material_type_for_categories
        from normative.gost_59023_2 import MATERIAL_ALUMINUM

        self.assertEqual(
            resolve_material_type_for_categories(MATERIAL_ALUMINUM, 'АМг6', 'II'),
            'aluminum',
        )


class NP104TitaniumPreparationTests(SimpleTestCase):
    def test_arc_welding_cleaning_width(self):
        from normative.np_104_18 import build_titanium_edge_cleaning_requirement

        text = build_titanium_edge_cleaning_requirement('30')
        self.assertIn('20,0 мм', text)
        self.assertIn('дуговую сварку', text)

    def test_esw_cleaning_width(self):
        from normative.np_104_18 import build_titanium_edge_cleaning_requirement

        text = build_titanium_edge_cleaning_requirement('20')
        self.assertIn('50,0 мм', text)
        self.assertIn('электрошлаковую сварку', text)

    def test_titanium_min_edge_zone_width(self):
        from normative.np_104_18 import get_titanium_min_edge_zone_width_mm

        self.assertEqual(get_titanium_min_edge_zone_width_mm('30'), 20.0)
        self.assertEqual(get_titanium_min_edge_zone_width_mm('20'), 50.0)


class InspectionZoneTests(SimpleTestCase):
    def test_titanium_thin_wall_haz_is_at_least_20mm(self):
        from normative.gost_59023_2 import get_inspection_zone

        zone = get_inspection_zone('С-1', 3.0, '53', material_type='titanium')
        self.assertEqual(zone['haz_width_mm'], 20.0)
        self.assertEqual(zone['zone_width_mm'], zone['bead_width_mm'] + 40.0)
        self.assertIn('НП-104-18', zone['ref'])

    def test_steel_thin_wall_keeps_default_haz(self):
        from normative.gost_59023_2 import get_inspection_zone

        zone = get_inspection_zone('С-1', 3.0, '53', material_type='steel')
        self.assertEqual(zone['haz_width_mm'], 5.0)
