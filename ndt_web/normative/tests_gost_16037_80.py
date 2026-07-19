"""Тесты ГОСТ 16037-80: каталог соединений, эскизы, зона контроля."""

from pathlib import Path

from django.test import SimpleTestCase

from normative.gost_16037_80 import (
    DOCUMENT_CODE,
    JOINT_TYPES,
    WELDING_PROCESSES,
    format_joint_thickness_ranges,
    get_inspection_zone,
    get_joint_group_labels_for_ui,
    get_joint_image_abs_path,
    get_joint_image_path,
    get_joint_info,
    get_joint_type_choices,
    get_welding_process_choices,
    get_welding_process_choices_for_joint,
    is_gost_16037_joint,
    is_joint_thickness_allowed,
    iter_joint_codes,
    lookup_dimensions,
)


class Gost16037CatalogTests(SimpleTestCase):
    def test_document_code(self):
        self.assertEqual(DOCUMENT_CODE, 'ГОСТ 16037-80')

    def test_joint_count_32(self):
        self.assertEqual(len(JOINT_TYPES), 32)
        codes = iter_joint_codes()
        self.assertEqual(len(codes), 32)

    def test_c17_exists(self):
        self.assertTrue(is_gost_16037_joint('С17'))
        info = get_joint_info('С17')
        self.assertEqual(info['code'], 'С17')
        self.assertIn('group_key', info)
        self.assertEqual(info['group_key'], 'steel_pipeline|butt')
        self.assertNotIn('sketch_source', info)

    def test_choices_include_32_joints(self):
        choices = get_joint_type_choices()
        joint_codes = [c for c, _ in choices if c and not str(c).startswith('__group_')]
        self.assertEqual(len(joint_codes), 32)
        self.assertIn('С17', joint_codes)

    def test_sort_order_c_u_n(self):
        codes = iter_joint_codes()
        self.assertTrue(codes[0].startswith('С'))
        prefixes = [c[0] for c in codes]
        # все С, затем У, затем Н
        first_u = next(i for i, p in enumerate(prefixes) if p == 'У')
        first_n = next(i for i, p in enumerate(prefixes) if p == 'Н')
        self.assertTrue(all(p == 'С' for p in prefixes[:first_u]))
        self.assertTrue(all(p == 'У' for p in prefixes[first_u:first_n]))
        self.assertTrue(all(p == 'Н' for p in prefixes[first_n:]))

    def test_group_labels(self):
        labels = get_joint_group_labels_for_ui()
        self.assertIn('steel_pipeline|butt', labels)
        self.assertIn('ГОСТ 16037-80', labels['steel_pipeline|butt'])
        self.assertIn('Угловые', labels['steel_pipeline|corner'])
        self.assertIn('Нахлёсточные', labels['steel_pipeline|lap'])

    def test_welding_processes(self):
        self.assertEqual(set(WELDING_PROCESSES.keys()), {'ЗП', 'ЗН', 'Р', 'Ф', 'Г'})
        choices = get_welding_process_choices()
        self.assertEqual(len(choices), 5)
        for_joint = get_welding_process_choices_for_joint('С17')
        codes = [c for c, _ in for_joint if c]
        self.assertIn('Р', codes)
        self.assertNotIn('Ф', codes)  # С17 без Ф


class Gost16037ImageTests(SimpleTestCase):
    def test_image_path_relative(self):
        path = get_joint_image_path('С17')
        self.assertEqual(path, 'techcards/joints/gost_16037/С17.png')

    def test_image_exists_on_disk(self):
        abs_path = get_joint_image_abs_path('С17')
        self.assertIsNotNone(abs_path)
        self.assertTrue(Path(abs_path).is_file())
        for code in ('С2', 'У5', 'Н1'):
            p = get_joint_image_abs_path(code)
            self.assertIsNotNone(p, msg=f'нет файла для {code}')
            self.assertTrue(p.is_file())


class Gost16037DimensionsTests(SimpleTestCase):
    def test_thickness_allowed_c2(self):
        self.assertTrue(is_joint_thickness_allowed('С2', 3.0, method='Р'))
        self.assertFalse(is_joint_thickness_allowed('С2', 10.0, method='Р'))
        self.assertFalse(is_joint_thickness_allowed('С2', 3.0, method='Р', dn_mm=10))

    def test_lookup_exact_row(self):
        dims = lookup_dimensions('С2', 2.0, 'Р')
        self.assertFalse(dims['approximate'])
        self.assertEqual(dims['e_nom'], 4)
        self.assertIsNotNone(dims.get('b_nom'))

    def test_lookup_approximate_when_no_row(self):
        dims = lookup_dimensions('С17', 8.0, 'Р')
        self.assertTrue(dims['approximate'])
        self.assertGreaterEqual(dims['e_nom'], 4)
        self.assertGreater(dims['g_nom'], 0)

    def test_format_ranges(self):
        text = format_joint_thickness_ranges('С2')
        self.assertIn('мм', text)


class Gost16037InspectionZoneTests(SimpleTestCase):
    def test_returns_e_and_g(self):
        zone = get_inspection_zone('С2', 3.0, 'Р')
        self.assertIn('bead_width_mm', zone)
        self.assertIn('bead_height_mm', zone)
        self.assertGreater(zone['bead_width_mm'], 0)
        self.assertGreater(zone['bead_height_mm'], 0)
        self.assertEqual(zone['bead_mode'], 'equal')
        self.assertIn('e_display', zone)
        self.assertIn('g_display', zone)
        self.assertIn('haz_width_mm', zone)
        self.assertIn('zone_width_mm', zone)
        self.assertIn('film_width_min_mm', zone)
        self.assertIn('weld_note', zone)
        self.assertIn('s_mm', zone)
        self.assertTrue(zone['s_equals_s1'])
        self.assertEqual(zone['s_mm'], 3.0)

    def test_c17_approximate_zone(self):
        zone = get_inspection_zone('С17', 10.0, welding_method='Р')
        self.assertGreater(zone['bead_width_mm'], 0)
        self.assertGreater(zone['bead_height_mm'], 0)
        self.assertTrue(zone.get('dimensions_approximate'))
        self.assertIn('ГОСТ 16037-80', zone['ref'])

    def test_backing_detected(self):
        zone = get_inspection_zone('С5', 4.0, 'Р')
        self.assertTrue(zone['has_backing'])
        self.assertGreater(zone['backing_thickness_mm'], 0)
