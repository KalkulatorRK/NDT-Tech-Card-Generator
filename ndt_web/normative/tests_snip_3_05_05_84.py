"""Тесты СНиП 3.05.05-84: баллы, объём, чувствительность, браковка."""

from django.test import SimpleTestCase

from normative.snip_3_05_05_84 import (
    DOCUMENT_CODE,
    get_default_control_volume_pct,
    get_reject_score_min,
    get_required_sensitivity_mm,
    get_sensitivity_class,
    lookup_score_limits,
    score_inclusions,
    evaluate_joint_score,
    build_acceptance_criteria_docx_data,
    undercut_limit_mm,
    surface_ndt_before_rt_required,
    is_snip_quality_norm,
    normalize_control_volume_pct,
)


class SnipCategoryTests(SimpleTestCase):
    def test_volumes_by_category(self):
        self.assertEqual(get_default_control_volume_pct('HIGH'), 100)
        self.assertEqual(get_default_control_volume_pct('I'), 20)
        self.assertEqual(get_default_control_volume_pct('II'), 10)
        self.assertEqual(get_default_control_volume_pct('III'), 2)
        self.assertEqual(get_default_control_volume_pct('IV'), 1)

    def test_reject_thresholds(self):
        self.assertEqual(get_reject_score_min('HIGH'), 2)
        self.assertEqual(get_reject_score_min('I'), 3)
        self.assertEqual(get_reject_score_min('II'), 3)
        self.assertEqual(get_reject_score_min('III'), 5)
        self.assertEqual(get_reject_score_min('IV'), 6)

    def test_sensitivity_class(self):
        self.assertEqual(get_sensitivity_class('HIGH'), 2)
        self.assertEqual(get_sensitivity_class('I'), 2)
        self.assertEqual(get_sensitivity_class('II'), 2)
        self.assertEqual(get_sensitivity_class('III'), 3)
        self.assertEqual(get_sensitivity_class('IV'), 3)

    def test_undercut_and_pre_rt(self):
        self.assertEqual(undercut_limit_mm('HIGH'), 0.0)
        self.assertTrue(surface_ndt_before_rt_required('HIGH'))
        self.assertEqual(undercut_limit_mm('III'), 0.5)
        self.assertFalse(surface_ndt_before_rt_required('III'))


class SnipScoreTableTests(SimpleTestCase):
    def test_row_for_thickness_up_to_3(self):
        lim = lookup_score_limits(1, 3.0)
        self.assertEqual(lim['width_mm'], 0.5)
        self.assertEqual(lim['length_mm'], 1.0)

    def test_row_for_thickness_over_3(self):
        lim = lookup_score_limits(1, 4.0)
        self.assertEqual(lim['width_mm'], 0.6)

    def test_score_1_fits(self):
        r = score_inclusions(10.0, width_mm=1.0, length_mm=2.0, sum_100_mm=6.0)
        self.assertEqual(r['score'], 1)

    def test_score_2_when_exceeds_1(self):
        # при t=10 (ряд >8–11): балл 1 — длина 2.0; балл 2 — 3.5
        r = score_inclusions(10.0, width_mm=1.0, length_mm=3.0)
        self.assertEqual(r['score'], 2)

    def test_score_6_when_exceeds_3(self):
        r = score_inclusions(10.0, width_mm=5.0, length_mm=20.0)
        self.assertEqual(r['score'], 6)

    def test_ignore_small_pores(self):
        r = score_inclusions(10.0, width_mm=0.1, length_mm=0.2)
        self.assertEqual(r['score'], 1)
        self.assertIn('0,2', r['verdict'].replace('.', ','))


class SnipEvaluateJointTests(SimpleTestCase):
    def test_cat_iii_score_4_doubles_no_repair(self):
        r = evaluate_joint_score('III', 4)
        self.assertFalse(r['is_reject'])
        self.assertFalse(r['repair_required'])
        self.assertTrue(r['double_volume'])

    def test_cat_iii_score_5_reject(self):
        r = evaluate_joint_score('III', 5)
        self.assertTrue(r['is_reject'])
        self.assertTrue(r['repair_required'])

    def test_cat_iv_score_5_doubles(self):
        r = evaluate_joint_score('IV', 5)
        self.assertFalse(r['is_reject'])
        self.assertTrue(r['double_volume'])
        self.assertFalse(r['repair_required'])

    def test_high_pressure_reject_at_2(self):
        r = evaluate_joint_score('HIGH', 2)
        self.assertTrue(r['is_reject'])


class SnipDocxAndHelpersTests(SimpleTestCase):
    def test_acceptance_docx_has_three_score_rows(self):
        data = build_acceptance_criteria_docx_data('steel', 'II', 12.0)
        self.assertTrue(data['score_system'])
        self.assertEqual(len(data['row_values']), 3)
        self.assertEqual(data['standard'], DOCUMENT_CODE)
        self.assertEqual(data['reject_score_min'], 3)

    def test_k_mm_positive(self):
        k = get_required_sensitivity_mm(20.0, 'I')
        self.assertGreater(k, 0)
        k3 = get_required_sensitivity_mm(20.0, 'III')
        self.assertGreater(k3, k)

    def test_is_snip_detector(self):
        self.assertTrue(is_snip_quality_norm('СНиП 3.05.05-84'))
        self.assertFalse(is_snip_quality_norm('НП-105-18'))

    def test_normalize_volume(self):
        self.assertEqual(normalize_control_volume_pct(20), 20)
        self.assertEqual(normalize_control_volume_pct(15), 10)
        self.assertEqual(normalize_control_volume_pct(50), 20)
