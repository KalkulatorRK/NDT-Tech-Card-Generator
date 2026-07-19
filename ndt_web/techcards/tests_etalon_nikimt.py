"""
Эталонный сценарий: параметры техкарты НИКИМТ №3-РК (Ø108×5, схема 3г).

Локальная проверка сопоставимости генерации с образцом.
"""

import os
import tempfile

from django.conf import settings
from django.test import SimpleTestCase
from docx import Document

from normative.np_105_18 import lookup_root_acceptance_limits
from techcards.generator import (
    RadiographicTechCardCalculator,
    _build_value_map,
    _find_section_row,
    generate_from_template,
    get_default_template_path,
)


def _nikimt_etalon_input():
    return {
        'organization': (
            'Филиал АО «НИКИМТ – Атомстрой» Дирекция на Курской АЭС'
        ),
        'department': (
            'Управление строительного контроля. Группа контроля качества'
        ),
        'object_name': (
            'КП РАО Курской АЭС, Курская АЭС-2 Энергоблоки №1 и 2'
        ),
        'weld_number': 'Ø108x5',
        'card_number': '3-РК',
        'object_type': 'pipe',
        'material': '12Х18Н10Т',
        'wall_thickness': '5',
        'assessment_thickness_mm': '3.5',
        'outer_diameter': '108',
        'joint_designation': 'С-42',
        'welding_process': '52',
        'weld_category': 'III',
        'control_volume_pct': '100',
        'joint_mobility': 'rotating',
        'source_code': 'X-200kV',
        'source_name_override': 'ПАМИР-300 или аналог',
        'tube_voltage_kv': '180',
        'focal_spot_mm': '2.5',
        'ofd_mm': '5',
        'scheme_type': '5g',
        'iqi_side': 'source',
        'film_name': 'D4 "Структурикс"',
        'control_location': 'Участок монтажа трубопровода',
        'temperature_range': '+5 ÷ +30',
        'developed_by_position': 'Дефектоскопист РГК 6 р.',
        'developed_by_name': 'В.Н. Болотов',
        'developed_by_certificate': 'САП.01-00386',
        'checked_by_position': 'Руководитель группы НК',
        'checked_by_name': 'А.И. Тарасов',
        'gmo_checked_by_position': '__custom__',
        'gmo_checked_by_position_custom': (
            'Главный инженер-технолог «Эксперт-центр»'
        ),
        'gmo_checked_by_name': 'В.Д. Дмитриев',
        'develop_date': '2020-01-23',
        'check_date': '2020-01-23',
    }


class NikimtEtalonRootLimitsTests(SimpleTestCase):
    databases = []

    def test_root_limits_match_nikimt_9_4_and_9_5(self):
        """
        Выпуклость ≤2,0 (табл. 4.5), вогнутость 0,8 (табл. 4.3)
        при S=5 мм, Ду=108, поворотный стык.
        """
        limits = lookup_root_acceptance_limits(
            5.0, 108.0, joint_mobility='rotating',
        )
        self.assertTrue(limits['applicable'])
        self.assertEqual(limits['convexity_mm'], 2.0)
        self.assertEqual(limits['concavity_mm'], 0.8)
        self.assertEqual(limits['convexity_table'], '4.5')
        self.assertEqual(limits['concavity_table'], '4.3')


class IqiSide611Tests(SimpleTestCase):
    """ГОСТ Р 50.05.07 п. 6.1.11 — ступень ИКИ влияет на K для геометрии."""

    databases = []

    def test_film_side_tightens_k_and_increases_f(self):
        base = {
            'object_type': 'pipe',
            'material': '12Х18Н10Т',
            'wall_thickness': '5',
            'outer_diameter': '108',
            'joint_designation': 'С-42',
            'welding_process': '52',
            'weld_category': 'III',
            'joint_mobility': 'rotating',
            'source_code': 'X-200kV',
            'focal_spot_mm': '2.5',
            'ofd_mm': '5',
            'scheme_type': '5g',
            'control_volume_pct': '100',
        }
        src = RadiographicTechCardCalculator(
            dict(base, iqi_side='source'),
        ).calculate()
        film = RadiographicTechCardCalculator(
            dict(base, iqi_side='film'),
        ).calculate()
        self.assertEqual(src['required_sensitivity_norm_mm'], 0.3)
        self.assertEqual(film['required_sensitivity_norm_mm'], 0.3)
        # Ступень ГОСТ 7512: 0,25 → 0,20 мм (эталон 12)
        self.assertEqual(src['iqi_wire_diameter_mm'], 0.25)
        self.assertEqual(film['iqi_wire_diameter_mm'], 0.2)
        self.assertEqual(film['sensitivity_k_display_mm'], 0.2)
        self.assertEqual(film['required_sensitivity_mm'], 0.2)
        self.assertGreater(film['C_coeff'], src['C_coeff'])
        self.assertGreater(film['f_calculated_mm'], src['f_calculated_mm'])
        self.assertIn('6.1.11', film['iqi_placement']['note'])


class NikimtEtalonGenerationTests(SimpleTestCase):
    databases = []

    def setUp(self):
        self.input_data = _nikimt_etalon_input()
        self.calc = RadiographicTechCardCalculator(self.input_data)
        self.params = self.calc.calculate()
        self.vmap = _build_value_map(self.params)

    def test_acceptance_uses_assessment_thickness_3_5(self):
        self.assertEqual(self.params['assessment_thickness_used_mm'], 3.5)
        docx = self.params['acceptance_criteria_docx']
        self.assertIn('3,5', docx.get('intro', '').replace('.', ','))
        # Кат. III, S=3.5 → табл. 4.8: вкл 0.8, скоп 1.2, n=12, Sпр=3.5
        values = docx.get('row_values') or []
        joined = ' '.join(str(v) for v in values)
        self.assertIn('0,8', joined.replace('.', ','))
        self.assertIn('1,2', joined.replace('.', ','))

    def test_value_map_equipment_and_voltage(self):
        self.assertIn('ПАМИР-300', self.vmap['5.1'])
        self.assertEqual(self.vmap['6.1'], '180 кВ (не более)')
        self.assertIn('НП-104-18', self.vmap['2.2'])
        self.assertIn('ГОСТ 7512-82', self.vmap['2.2'])
        self.assertIn('монтажа', self.vmap['8.1'])
        self.assertEqual(self.vmap['8.4'], '+5 ÷ +30')
        self.assertIn('негатоскоп', self.vmap['5.8'].lower())
        self.assertIn('маркер', self.vmap['5.9'].lower())
        self.assertIn('Проявитель', self.vmap['5.11'])

    def test_scheme_is_5g_drawing_3g(self):
        self.assertEqual(self.params['scheme_type'], '5g')
        info = self.params.get('scheme_info') or {}
        name = (info.get('name') or '') + (self.vmap.get('6.9') or '')
        self.assertTrue(
            '3г' in name.lower() or '3 г' in name.lower() or '5g' in name.lower()
            or 'чертёж 3' in name.lower() or 'чертеж 3' in name.lower(),
            msg=f'scheme text={name!r}',
        )

    def test_docx_contains_section_105_and_docs(self):
        template = get_default_template_path()
        self.assertTrue(template and os.path.exists(template))
        static_root = str(settings.STATICFILES_DIRS[0])
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, 'etalon_3rk.docx')
            generate_from_template(
                self.params, template, out, static_root=static_root,
            )
            doc = Document(out)
            table, ri = _find_section_row(doc, '10.5')
            self.assertIsNotNone(table)
            text_105 = table.rows[ri].cells[0].text
            self.assertIn('2', text_105)
            self.assertIn('0,8', text_105.replace('.', ','))
            self.assertIn('4.5', text_105)
            self.assertIn('4.3', text_105)

            # НД в разделе 2
            found_docs = False
            for t in doc.tables:
                for row in t.rows:
                    label = row.cells[0].text.strip().replace('\xa0', ' ')
                    if label.startswith('2.2'):
                        val = row.cells[-1].text
                        self.assertIn('НП-105-18', val)
                        self.assertIn('7512', val)
                        found_docs = True
            self.assertTrue(found_docs)

            # Сохранить копию для ручного сравнения
            media_dir = os.path.join(settings.MEDIA_ROOT, 'techcards')
            os.makedirs(media_dir, exist_ok=True)
            dest = os.path.join(media_dir, 'etalon_nikimt_3rk.docx')
            import shutil
            shutil.copy2(out, dest)


class JointWallSVsS1GeneratorTests(SimpleTestCase):
    """
    Два сценария генератора НК:
    - без расточки (С-42, S = S1);
    - с расточкой (С-23-2, табл. 9.30, S ≠ S1).
    """

    databases = []

    def _base(self, **overrides):
        data = {
            'object_type': 'pipe',
            'material': '12Х18Н10Т',
            'welding_process': '52',
            'weld_category': 'III',
            'joint_mobility': 'rotating',
            'source_code': 'X-200kV',
            'focal_spot_mm': '2.5',
            'ofd_mm': '5',
            'scheme_type': '5g',
            'iqi_side': 'source',
            'control_volume_pct': '100',
        }
        data.update(overrides)
        return data

    def test_generator_without_boring_c42_s_equals_s1(self):
        params = RadiographicTechCardCalculator(self._base(
            wall_thickness='5',
            outer_diameter='108',
            joint_designation='С-42',
        )).calculate()

        self.assertTrue(params['s_equals_s1'])
        self.assertFalse(params['has_internal_boring'])
        self.assertEqual(params['s_mm'], 5.0)
        self.assertEqual(params['s1_mm'], 5.0)
        self.assertEqual(params['s_eff_mm'], 5.0)
        # Схема 5г — две стенки: S_K = 2×S = 10
        self.assertEqual(params['s_k_mm'], 10.0)
        self.assertIn('S = S1', params['wall_summary'])
        self.assertIn('S + S', params['sk_desc'])

    def test_generator_with_boring_c23_2_s_ne_s1(self):
        params = RadiographicTechCardCalculator(self._base(
            wall_thickness='4',
            outer_diameter='108',
            joint_designation='С-23-2',
        )).calculate()

        self.assertFalse(params['s_equals_s1'])
        self.assertTrue(params['has_internal_boring'])
        self.assertEqual(params['s_mm'], 4.0)
        self.assertEqual(params['s1_mm'], 2.4)
        self.assertEqual(params['s_eff_mm'], 2.4)
        self.assertEqual(params['dp_mm'], 102.0)
        # S_K = 2×S1 = 4.8
        self.assertEqual(params['s_k_mm'], 4.8)
        self.assertIn('S1', params['sk_desc'])
        self.assertIn('S = 4', params['wall_summary'])
        self.assertIn('S1 = 2.4', params['wall_summary'])
        self.assertEqual(params['weld_bead_width_mm'], 9.0)
        self.assertEqual(params['d_inner_mm'], 102.0)

        vmap = _build_value_map(params)
        self.assertIn('S1', vmap['1.7'] + vmap['4.2.1 S'])
