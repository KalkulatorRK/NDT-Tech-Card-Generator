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


class Scheme5gFormulaTests(SimpleTestCase):
    """Схема 3г: формула f и выбор N по табл. Г.4 (условие f/D)."""

    def test_f_matches_gost_g1_formula(self):
        from normative.calculations import calc_scheme_5g, _get_C
        from normative.gost_50_05_07 import dist_l_scheme_3g

        phi, k, d_out, d_in = 2.5, 0.3, 108.0, 98.0
        c = _get_C(phi, k)
        result = calc_scheme_5g(phi, d_out, d_in, k)
        expected = dist_l_scheme_3g(d_out, d_in, 0, c)
        self.assertAlmostEqual(result['f_min_mm'], expected, places=1)
        self.assertAlmostEqual(result['C'], c, places=3)

    def test_n_selected_by_f_over_d_not_min_key(self):
        """
        Для m≈0.87 и f/D>0.6 нельзя брать N=3 (порог ≤0.6), нужно N=4.
        Ранее calc_scheme_5g ошибочно брал min(keys)=3.
        """
        from normative.calculations import calc_scheme_5g

        # D_eff=113, d=98, K=0.3, Φ=2.5 → f≈131, f/D≈1.16 → N=4
        result = calc_scheme_5g(2.5, 113.0, 98.0, 0.3)
        self.assertGreater(result['f_over_d'], 0.6)
        self.assertEqual(result['N'], 4)
        self.assertAlmostEqual(result['L_mm'], 3.1416 * 113.0 / 4, delta=1.0)

    def test_nikimt_geometry_with_k_01_gives_n4(self):
        """При K=0,1 (как в эталоне) f_min≈321, N=4, L≈πD/4."""
        from normative.calculations import calc_scheme_5g
        import math

        result = calc_scheme_5g(2.5, 108.0, 98.0, 0.1)
        self.assertAlmostEqual(result['f_min_mm'], 321.0, places=0)
        self.assertEqual(result['N'], 4)
        self.assertAlmostEqual(result['L_mm'], math.pi * 108.0 / 4, delta=1.0)


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
        from normative.gost_59023_2 import get_inspection_zone, get_weld_width

        weld = get_weld_width('С-1', 3.0)
        zone = get_inspection_zone('С-1', 3.0, '53', material_type='titanium')
        self.assertEqual(zone['haz_width_mm'], 20.0)
        self.assertEqual(
            zone['zone_width_mm'],
            weld['e_max_mm'] + 2 * zone['haz_width_mm'],
        )
        self.assertIn('НП-104-18', zone['ref'])

    def test_steel_thin_wall_keeps_default_haz(self):
        from normative.gost_59023_2 import get_inspection_zone

        zone = get_inspection_zone('С-1', 3.0, '53', material_type='steel')
        self.assertEqual(zone['haz_width_mm'], 5.0)


class GostJointCatalogTests(SimpleTestCase):
    """Каталог типов сварных соединений ГОСТ Р 59023.2-2020."""

    def test_catalog_includes_supplement_joint_types(self):
        from normative.gost_59023_2 import JOINT_TYPES, ALL_JOINT_CODES

        self.assertGreaterEqual(len(JOINT_TYPES), 96)
        self.assertIn('С-2', JOINT_TYPES)
        self.assertIn('С-10', JOINT_TYPES)
        self.assertIn('У-11', JOINT_TYPES)
        self.assertIn('ТС-1', JOINT_TYPES)
        self.assertEqual(len(ALL_JOINT_CODES), len(JOINT_TYPES))

    def test_joint_codes_sorted_by_material_and_table(self):
        from normative.gost_59023_2 import ALL_JOINT_CODES, _joint_sort_key

        sort_keys = [_joint_sort_key(code) for code in ALL_JOINT_CODES]
        self.assertEqual(sort_keys, sorted(sort_keys))

    def test_joint_choices_include_all_types_with_applicability(self):
        from normative.gost_59023_2 import (
            JOINT_TYPES, get_joint_type_choices, get_joint_applicability_text,
        )

        all_codes = [c for c, _ in get_joint_type_choices() if c and not c.startswith('__group_')]
        self.assertEqual(len(all_codes), len(JOINT_TYPES))
        self.assertIn('С-1', all_codes)
        self.assertIn('С-42', all_codes)

        labels = dict(get_joint_type_choices())
        self.assertIn('п. 5', labels['С-1'])
        self.assertIn('п. 6', labels['С-1'])
        self.assertIn('п. 7', get_joint_applicability_text('С-1'))
        self.assertIn('п. 8', get_joint_applicability_text('С-1'))
        self.assertIn('9.85', labels['ТС-1'])
        self.assertIn('трубные', labels['ТС-1'])
        self.assertIn('листовые', labels['У-15'])
        self.assertIn('9.111', labels['Т-3'])
        self.assertIn('угловые, тавровые', labels['Т-3'])

        perlit_only = [c for c, _ in get_joint_type_choices('perlit')]
        self.assertIn('С-1', perlit_only)
        self.assertNotIn('С-42', perlit_only)

    def test_dual_bead_row_parsing(self):
        from normative.gost_59023_2 import (
            _parse_dimension_row, get_weld_width, get_inspection_zone,
        )

        parsed = _parse_dimension_row((10.0, 20.0, 15.0, 12.0, 2.0, 0.5, 3.5), 'dual')
        self.assertEqual(parsed['e_mm'], 15.0)
        self.assertEqual(parsed['e1_mm'], 12.0)

        weld = get_weld_width('С-22-1', 3.0)
        zone = get_inspection_zone('С-22-1', 3.0, '40')
        self.assertEqual(zone['effective_e_max_mm'], weld['effective_e_max_mm'])
        self.assertEqual(zone['zone_width_mm'], weld['effective_e_max_mm'] + 2 * zone['haz_width_mm'])

    def test_sketch_inner_bead_for_dual_steel_joints(self):
        from normative.gost_59023_2 import get_weld_width, get_inspection_zone

        c12 = get_weld_width('С-1-2', 3.0)
        self.assertEqual(c12['bead_mode'], 'dual')
        self.assertEqual(c12['e1_mm'], 4.0)
        self.assertEqual(c12['g1_nom'], 1.5)
        self.assertEqual(c12['effective_e_max_mm'], 12.0)

        c2 = get_weld_width('С-2', 20.0)
        self.assertEqual(c2['e1_mm'], 18.0)
        self.assertEqual(c2['g1_nom'], 2.0)

        c3 = get_weld_width('С-3', 10.0)
        self.assertEqual(c3['e1_mm'], 10.0)
        self.assertEqual(c3['g1_nom'], 1.5)

        zone = get_inspection_zone('С-2', 20.0, '10')
        self.assertEqual(zone['bead_width_inner_mm'], 18.0)
        self.assertIsNotNone(zone.get('g1_display'))

    def test_rtf_dimensions_for_titanium_aluminum(self):
        from normative.gost_59023_2 import JOINT_TYPES, get_weld_width
        from normative.gost_59023_extended_joints import JOINT_TYPES_EXT

        for code in JOINT_TYPES_EXT:
            self.assertTrue(
                JOINT_TYPES[code].get('dimensions'),
                f'{code} должен иметь dimensions',
            )

        ts3 = get_weld_width('ТС-3', 7.0, 'titanium')
        self.assertEqual(ts3['e_mm'], 10.0)

        t3 = get_weld_width('Т-3', 9.0, 'aluminum')
        self.assertEqual(t3['e_mm'], 12.0)

    def test_sketch_inner_bead_for_c5_c34_group(self):
        from normative.gost_59023_2 import get_weld_width, get_inspection_zone
        from normative.gost_59023_sketch_beads import SKETCH_INNER_BEAD

        expected_codes = [
            'С-5', 'С-5-1', 'С-12', 'С-13', 'С-14', 'С-15', 'С-17',
            'С-21', 'С-22', 'С-23', 'С-24', 'С-25', 'С-34',
        ]
        for code in expected_codes:
            self.assertIn(code, SKETCH_INNER_BEAD, f'{code} должен быть в SKETCH_INNER_BEAD')

        c5 = get_weld_width('С-5', 32.0)
        self.assertEqual(c5['bead_mode'], 'dual')
        self.assertEqual(c5['e1_mm'], 18.0)
        self.assertEqual(c5['effective_e_max_mm'], max(c5['e_max_mm'], 22.0))

        c14 = get_weld_width('С-14', 3.0)
        self.assertEqual(c14['e1_mm'], 7.0)

        c34 = get_weld_width('С-34', 100.0)
        self.assertEqual(c34['e1_mm'], 13.0)
        self.assertEqual(c34['g1_nom'], 3.0)

        zone = get_inspection_zone('С-13', 70.0, '11')
        self.assertEqual(zone['bead_width_inner_mm'], 25.0)
        self.assertGreater(zone['effective_e_max_mm'], zone['bead_width_mm'])

    def test_joint_applicable_material_classes_dual_section(self):
        from normative.gost_59023_2 import get_joint_applicable_material_classes

        c12 = get_joint_applicable_material_classes('С-1-2')
        self.assertIn('perlit', c12)
        self.assertIn('austenite', c12)

        c1 = get_joint_applicable_material_classes('С-1')
        self.assertIn('perlit', c1)
        self.assertIn('austenite', c1)
        self.assertIn('titanium', c1)
        self.assertIn('aluminum', c1)

    def test_joint_image_path_resolves_gost_sketches(self):
        from pathlib import Path
        from normative.gost_59023_2 import (
            get_joint_image_path, iter_joint_codes, _welds_static_dir,
        )

        base = _welds_static_dir()
        self.assertTrue((base / get_joint_image_path('С-1-2')).exists())
        self.assertTrue((base / get_joint_image_path('С-2')).exists())
        self.assertTrue((base / get_joint_image_path('ТС-1')).exists())

        for code in ('С-32', 'У-15', 'У-16', 'У-19', 'Т-6', 'Т-7', 'Т-8'):
            path = get_joint_image_path(code)
            self.assertTrue(path, msg=f'{code}: путь не задан')
            self.assertTrue((base / path).exists(), msg=f'{code}: файл {path}')

        missing = [c for c in iter_joint_codes() if not get_joint_image_path(c)]
        self.assertEqual(missing, [], msg=f'нет эскизов: {missing}')


class ControlVolumeTests(SimpleTestCase):
    """Объём выборочного контроля (НП-105-18, п. 70–72)."""

    def test_scale_exposure_examples_from_spec(self):
        from normative.calculations import apply_control_volume_adjustment

        n, n_seg, _ = apply_control_volume_adjustment(
            N_full=2, N_segments_full=4, volume_pct=50,
            apply_sample_scaling=True,
        )
        self.assertEqual(n, 1)
        self.assertEqual(n_seg, 2)

        n, n_seg, _ = apply_control_volume_adjustment(
            N_full=2, N_segments_full=4, volume_pct=25,
            apply_sample_scaling=True,
        )
        self.assertEqual(n, 1)
        self.assertEqual(n_seg, 1)

    def test_ring_d250_no_scaling(self):
        from normative.calculations import (
            requires_full_length_ring_control,
            apply_control_volume_adjustment,
        )

        self.assertTrue(requires_full_length_ring_control('pipe', 219))
        self.assertFalse(requires_full_length_ring_control('pipe', 300))
        self.assertFalse(requires_full_length_ring_control('flat', 100))

        n, n_seg, _ = apply_control_volume_adjustment(
            N_full=2, N_segments_full=4, volume_pct=50,
            apply_sample_scaling=False,
        )
        self.assertEqual(n, 2)
        self.assertEqual(n_seg, 4)

    def test_straight_seam_controlled_length(self):
        from normative.calculations import apply_control_volume_adjustment

        n, n_seg, controlled = apply_control_volume_adjustment(
            N_full=5,
            N_segments_full=5,
            volume_pct=50,
            apply_sample_scaling=True,
            seam_length_mm=1500,
            segment_length_mm=350,
        )
        self.assertGreaterEqual(n, 3)
        self.assertGreaterEqual(controlled, 750)

    def test_normalize_control_volume(self):
        from normative.calculations import normalize_control_volume_pct

        self.assertEqual(normalize_control_volume_pct(50), 50)
        self.assertEqual(normalize_control_volume_pct('25'), 25)
        self.assertEqual(normalize_control_volume_pct(33), 100)


class Gost59023WallThicknessTests(SimpleTestCase):
    """S = S1 vs расточка S ≠ S1 (ГОСТ Р 59023.2-2020)."""

    databases = []

    def test_all_joints_have_wall_meta(self):
        from normative.gost_59023_2 import JOINT_TYPES, get_joint_info

        for code in JOINT_TYPES:
            info = get_joint_info(code)
            self.assertIn(info['wall_thickness_mode'], ('s_equals_s1', 'bored'))
            self.assertIsInstance(info['s_equals_s1'], bool)
            self.assertIsInstance(info['has_internal_boring'], bool)
            self.assertEqual(info['s_equals_s1'], not info['has_internal_boring'])

    def test_c42_s_equals_s1_no_boring(self):
        from normative.gost_59023_wall import resolve_joint_wall_thickness

        wall = resolve_joint_wall_thickness('С-42', 5.0, outer_diameter_mm=108.0)
        self.assertTrue(wall['s_equals_s1'])
        self.assertFalse(wall['has_internal_boring'])
        self.assertEqual(wall['s_mm'], 5.0)
        self.assertEqual(wall['s1_mm'], 5.0)
        self.assertEqual(wall['s_eff_mm'], 5.0)
        self.assertTrue(wall['s_equals_s1_actual'])

    def test_c22_2_same_table_but_no_boring(self):
        """Табл. 9.30 общая с С-23-2, но на чертеже С-22-2 без расточки."""
        from normative.gost_59023_wall import (
            GOST_BORED_JOINT_CODES,
            resolve_joint_wall_thickness,
        )
        from normative.gost_59023_2 import get_joint_info

        self.assertNotIn('С-22-2', GOST_BORED_JOINT_CODES)
        info = get_joint_info('С-22-2')
        self.assertTrue(info['s_equals_s1'])
        self.assertFalse(info['has_internal_boring'])
        self.assertEqual(info.get('boring_rows') or [], [])

        wall = resolve_joint_wall_thickness('С-22-2', 2.5, outer_diameter_mm=18.0)
        self.assertEqual(wall['s_eff_mm'], 2.5)
        self.assertEqual(wall['s1_mm'], 2.5)
        self.assertIsNone(wall['dp_mm'])
        self.assertIn('без расточки', wall['wall_note'])

    def test_c23_2_bored_s_ne_s1(self):
        from normative.gost_59023_wall import resolve_joint_wall_thickness
        from normative.gost_59023_2 import get_weld_width, get_inspection_zone

        wall = resolve_joint_wall_thickness('С-23-2', 4.0, outer_diameter_mm=108.0)
        self.assertFalse(wall['s_equals_s1'])
        self.assertTrue(wall['has_internal_boring'])
        self.assertEqual(wall['s_mm'], 4.0)
        self.assertEqual(wall['s1_mm'], 2.4)
        self.assertEqual(wall['s_eff_mm'], 2.4)
        self.assertEqual(wall['dp_mm'], 102.0)
        self.assertFalse(wall['s_equals_s1_actual'])

        weld = get_weld_width('С-23-2', 4.0, outer_diameter_mm=108.0)
        self.assertEqual(weld['e_mm'], 9.0)
        self.assertIn('S1', weld['note'])

        zone = get_inspection_zone(
            'С-23-2', 4.0, '40', outer_diameter_mm=108.0,
        )
        self.assertEqual(zone['s_eff_mm'], 2.4)
        self.assertTrue(zone['has_internal_boring'])
