"""
Генератор технологических карт радиографического контроля.

Реализует два режима работы:
1. На основе шаблона (DOCX) — заполняет оригинальный бланк данными.
2. Программная генерация — создаёт документ с нуля если шаблон не найден.

Нормативная база: ГОСТ Р 50.05.07-2018, НП-104-18, НП-105-18.
"""

import io
import os
import re
import uuid
import copy
import tempfile
import logging
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Pt, Mm, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from common.pdf_fonts import register_cyrillic_fonts, FONT_REGULAR, FONT_BOLD

logger = logging.getLogger(__name__)

from normative.gost_50_05_07 import (
    get_sensitivity, get_sensitivity_mm, get_suitable_sources,
    calc_geometric_unsharpness, calc_min_sfd,
    SCREEN_REQUIREMENTS, FILM_CLASSES, MAX_GEOMETRIC_UNSHARPNESS,
    OPTICAL_DENSITY, PERSONNEL_REQUIREMENTS, SAFETY_REQUIREMENTS,
    FILM_PROCESSING, IQI_TYPES, DOCUMENT_CODE, DOCUMENT_FULL_NAME,
    parse_film_size,
    select_film_size_for_length,
    RADIATION_SOURCES,
)
from normative.gost_59023_2 import (
    resolve_material_type,
    get_material_display_name,
    resolve_welding_material,
    format_dimension_with_tolerance,
)
from normative.np_104_18 import WELD_CATEGORIES
from normative.np_105_18 import DOCUMENT_CODE as NP105_CODE
from normative.calculations import (
    calc_exposure_parameters, recommend_scheme,
    calc_geometric_unsharpness_full, SCHEME_INFO, clamp_f_mm,
)


# ---------------------------------------------------------------
# Вспомогательные функции для работы с таблицами DOCX
# ---------------------------------------------------------------

def _unique_cells(row):
    """
    Возвращает список уникальных ячеек строки (без дублей от слияния).
    В python-docx слитые ячейки возвращаются несколько раз подряд.
    """
    seen = []
    for cell in row.cells:
        if not seen or seen[-1]._tc is not cell._tc:
            seen.append(cell)
    return seen


def _format_date_ddmmyyyy(value) -> str:
    """Форматирует дату для техкарты: дд.мм.гггг (в т.ч. из ISO YYYY-MM-DD)."""
    if value is None or value == '':
        return datetime.now().strftime('%d.%m.%Y')
    if hasattr(value, 'strftime'):
        return value.strftime('%d.%m.%Y')
    s = str(value).strip()
    iso = re.match(r'^(\d{4})-(\d{2})-(\d{2})', s)
    if iso:
        return f'{iso.group(3)}.{iso.group(2)}.{iso.group(1)}'
    return s


def _label_matches_value_key(label_text: str, key: str) -> bool:
    """
    Сопоставляет метку строки шаблона с ключом value_map.
    «1.1» не должно совпадать с «1.10», «1.9» и т.п.
    """
    if not label_text or not key:
        return False
    label_lower = label_text.lower()
    key_lower = key.lower()
    if key_lower not in label_lower:
        return False
    if not key[0].isdigit():
        return True
    pos = label_lower.find(key_lower)
    tail = label_lower[pos + len(key_lower):]
    if not tail:
        return True
    return tail[0] in '.\t \xa0'


def _match_value_for_label(label_text: str, value_map: dict):
    """Возвращает значение для метки (приоритет у более длинных ключей)."""
    for key in sorted(value_map.keys(), key=len, reverse=True):
        if not _label_matches_value_key(label_text, key):
            continue
        if key.startswith('4.2.') and key not in ('4.2.3',):
            if any(x in label_text.lower() for x in (
                'внешний диаметр', 'длинна', 'длина', 'наружной поверхности',
                'околошовной', '4.2.6',
            )):
                continue
        return value_map[key]
    return None


def _reference_run_in_cell(cell):
    """Первый непустой run ячейки — эталон шрифта шаблона."""
    for para in cell.paragraphs:
        for run in para.runs:
            if (run.text or '').strip():
                return run
    for para in cell.paragraphs:
        if para.runs:
            return para.runs[0]
    return None


def _reference_run_in_paragraph(para):
    """Первый непустой run параграфа — эталон шрифта шаблона."""
    for run in para.runs:
        if (run.text or '').strip():
            return run
    return para.runs[0] if para.runs else None


def _copy_run_font(source, target):
    """Копирует оформление run без изменения текста."""
    if source is None or target is None:
        return
    target.bold = source.bold
    target.italic = source.italic
    target.underline = source.underline
    if source.font.size:
        target.font.size = source.font.size
    if source.font.name:
        target.font.name = source.font.name
    for attr in ('name_ascii', 'name_hansi', 'name_cs', 'name_east_asia'):
        value = getattr(source.font, attr, None)
        if value:
            setattr(target.font, attr, value)


BODY_TABLE_FONT_PT = 12


def _set_cell_text(
    cell,
    text: str,
    bold: bool | None = None,
    font_size: int | None = None,
):
    """
    Устанавливает текст в ячейке, сохраняя шрифт и отступы шаблона.
    По умолчанию — 12 pt (как в эталонной техкарте), а не 9 pt.
    """
    ref = _reference_run_in_cell(cell)
    para = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
    if para.runs:
        run = para.runs[0]
        run.text = str(text) if text is not None else ''
        for extra in para.runs[1:]:
            extra.text = ''
    else:
        run = para.add_run(str(text) if text is not None else '')
    for extra_para in cell.paragraphs[1:]:
        for extra_run in extra_para.runs:
            extra_run.text = ''
    if bold is not None:
        run.bold = bold
    elif ref is not None:
        run.bold = ref.bold
    if font_size is not None:
        run.font.size = Pt(font_size)
    elif ref is not None and ref.font.size:
        run.font.size = ref.font.size
    else:
        run.font.size = Pt(12)
    if ref is not None:
        _copy_run_font(ref, run)
        if bold is not None:
            run.bold = bold
        if font_size is not None:
            run.font.size = Pt(font_size)
    if font_size is None and (run.font.size is None or run.font.size.pt < BODY_TABLE_FONT_PT):
        run.font.size = Pt(BODY_TABLE_FONT_PT)


def _fill_row_value(table, row_idx: int, value: str):
    """
    Заполняет значение в строке таблицы.
    Предполагает структуру: [метка_ячейки | значение_ячейки].
    Значение записывается в последнюю уникальную ячейку строки.
    """
    if row_idx >= len(table.rows):
        return
    row = table.rows[row_idx]
    ucells = _unique_cells(row)
    if len(ucells) >= 2:
        _set_cell_text(ucells[-1], value)
    elif len(ucells) == 1:
        # Однострочная таблица — добавляем после метки
        pass


def _find_row_by_label(table, label_fragment: str) -> int:
    """Находит индекс строки по фрагменту текста метки."""
    for i, row in enumerate(table.rows):
        ucells = _unique_cells(row)
        if ucells and label_fragment.lower() in ucells[0].text.lower():
            return i
    return -1


def _format_sensitivity_desc(
    display_k_mm: float,
    sk_desc: str,
    weld_category: str,
    *,
    norm_k_mm: float | None = None,
    film_side: bool = False,
) -> str:
    """
    Текст для п. 6.3 техкарты «Требуемая чувствительность K, не более, мм».

    При ИКИ со стороны плёнки указывается K на одну ступень жёстче
    нормативного значения (диаметр проволоки ИКИ).
    """
    if film_side and norm_k_mm is not None:
        return (
            f'K ≤ {display_k_mm:.3f} мм '
            f'(ИКИ со стороны плёнки, на 1 ступень жёстче нормативного '
            f'K ≤ {norm_k_mm:.3f} мм; НП-105-18, Табл. 4.8: {sk_desc}, '
            f'кат. {weld_category})'
        )
    return (
        f'K ≤ {display_k_mm:.3f} мм '
        f'(НП-105-18, Табл. 4.8: {sk_desc}, кат. {weld_category})'
    )


# ---------------------------------------------------------------
# Расчётное ядро (без изменений)
# ---------------------------------------------------------------

class RadiographicTechCardCalculator:
    """
    Вычислительное ядро: рассчитывает все параметры техкарты
    по ГОСТ Р 50.05.07-2018 на основе введённых пользователем данных.
    """

    def __init__(self, input_data: dict):
        self.data = input_data
        self.params = {}
        self.errors = []
        self.warnings = []

    def calculate(self) -> dict:
        """Выполняет все расчёты и возвращает словарь параметров."""
        self._extract_inputs()
        # Сначала получаем g_min/g_max из таблиц сварных соединений
        self._calc_inspection_zones()
        # Затем рассчитываем K с правильной радиационной толщиной S_рад
        self._calc_sensitivity_value()
        self._select_sources()
        self._calc_geometric_params()
        self._calc_exposure_scheme()
        self._select_film()
        self._calc_screens()
        self._calc_iqi()
        self._fill_processing()
        self._fill_personnel()
        self._fill_safety()
        self._fill_acceptance_criteria()
        self._calc_control_volume()
        return self.params

    def _extract_inputs(self):
        d = self.data
        source_code = d.get('source_code', '')
        src_info = next((s for s in RADIATION_SOURCES if s['code'] == source_code), None)
        src_type = src_info.get('type', 'isotope') if src_info else 'isotope'
        focal_raw = d.get('focal_spot_mm')
        if focal_raw in (None, ''):
            focal_spot = 3.0 if src_type == 'isotope' else 2.0
        else:
            focal_spot = float(focal_raw)

        develop_date = _format_date_ddmmyyyy(d.get('develop_date', ''))
        raw_check = d.get('check_date', '')
        if (
            raw_check is None
            or raw_check == ''
            or (isinstance(raw_check, str) and not raw_check.strip())
        ):
            check_date = develop_date
        else:
            check_date = _format_date_ddmmyyyy(raw_check)

        material_display = get_material_display_name(
            d.get('material', ''),
            d.get('material_custom', ''),
        )

        self.params.update({
            'organization': d.get('organization', ''),
            'object_name': d.get('object_name', ''),
            'drawing_number': d.get('drawing_number', ''),
            'weld_number': d.get('weld_number', ''),
            'card_number': d.get('card_number', ''),
            'object_type': d.get('object_type', 'pipe'),
            'material': d.get('material', ''),
            'material_grade': (d.get('material_custom') or '').strip(),
            'material_display': material_display,
            'material_type': resolve_material_type(d.get('material', '')),
            'wall_thickness': float(d.get('wall_thickness', 10)),
            'outer_diameter': float(d.get('outer_diameter', 0) or 0),
            'flat_length_mm': float(d.get('flat_length_mm', 0) or 0),
            'joint_designation': d.get('joint_designation', ''),
            'joint_mobility': d.get('joint_mobility', 'non_rotating'),
            'welding_process': d.get('welding_process', '30'),
            'weld_category': d.get('weld_category', 'II'),
            'reinforcement_removed': bool(d.get('reinforcement_removed')),
            'has_backing_ring': bool(d.get('has_backing_ring')),
            'backing_ring_thickness_mm': float(d.get('backing_ring_thickness_mm', 0) or 0),
            'weld_material': resolve_welding_material(
                d.get('welding_material', ''),
                d.get('welding_material_custom', ''),
                material_display,
            ),
            'source_code': source_code,
            'source_focal_spot_mm': focal_spot,
            'source_activity': d.get('source_activity', ''),
            'sfd_mm': float(d.get('sfd_mm', 0) or 0),
            'ofd_mm': float(d.get('ofd_mm', 5) or 5),
            'film_name': d.get('film_name', ''),
            'iqi_side': d.get('iqi_side', 'source') or 'source',
            'inspector_name': d.get('inspector_name', ''),
            'develop_date': develop_date,
            'check_date': check_date,
            'developed_by_position': (
                d.get('developed_by_position_resolved')
                or (d.get('developed_by_position_custom', '').strip()
                    if d.get('developed_by_position') == '__custom__'
                    else d.get('developed_by_position', ''))
            ),
            'developed_by_name': d.get('developed_by_name', ''),
            'developed_by_certificate': d.get('developed_by_certificate', ''),
            'checked_by_position': (
                d.get('checked_by_position_resolved')
                or (d.get('checked_by_position_custom', '').strip()
                    if d.get('checked_by_position') == '__custom__'
                    else d.get('checked_by_position', ''))
            ),
            'checked_by_name': d.get('checked_by_name', ''),
            'checked_by_certificate': d.get('checked_by_certificate', ''),
        })

    def _calc_inspection_zones(self):
        """
        Рассчитывает ширину валика шва, ОШЗ и контролируемую зону
        по ГОСТ Р 59023.2-2020 и НП-105-18.
        Сохраняет g_min, g_max для расчёта радиационной толщины в схеме.
        Заполняет поля техкарты 4.2.2, 4.2.4, 4.2.5.
        """
        from normative.gost_59023_2 import get_inspection_zone, get_joint_info

        joint_code = self.params.get('joint_designation', '')
        S = self.params['wall_thickness']
        method = self.params.get('welding_process', '30')

        zone = get_inspection_zone(
            joint_code, S, method,
            reinforcement_removed=self.params.get('reinforcement_removed', False),
            has_backing_ring=self.params.get('has_backing_ring', False),
            backing_ring_thickness_mm=self.params.get('backing_ring_thickness_mm') or None,
        )
        joint_info = get_joint_info(joint_code)

        self.params['weld_bead_width_mm'] = zone.get('bead_width_mm', '')
        self.params['weld_bead_width_inner_mm'] = zone.get('bead_width_inner_mm', '')
        self.params['e_display'] = zone.get('e_display', '')
        self.params['e1_display'] = zone.get('e1_display', '')
        self.params['g_display'] = zone.get('g_display', '')
        self.params['weld_bead_height_mm'] = zone.get('bead_height_mm', '')
        self.params['reinforcement_status'] = (
            'снят' if self.params.get('reinforcement_removed') else 'не снят'
        )
        self.params['g_min_mm'] = zone.get('g_min_mm', 0.5)
        self.params['g_max_mm'] = zone.get('g_max_mm', 3.5)
        self.params['backing_thickness_mm'] = zone.get('backing_thickness_mm', 0.0)
        self.params['has_backing'] = zone.get('has_backing', False)
        self.params['haz_width_mm'] = zone.get('haz_width_mm', 5.0)
        self.params['zone_width_mm'] = zone.get('zone_width_mm', '')
        self.params['film_width_min_mm'] = zone.get('film_width_min_mm', '')
        self.params['zone_note'] = zone.get('weld_note', '')
        self.params['joint_groove'] = joint_info.get('groove', '')
        self.params['joint_name'] = joint_info.get('name', joint_code)
        self.params['joint_sketch'] = joint_info.get('sketch', '')
        from normative.gost_59023_2 import get_joint_image_path
        self.params['joint_image'] = get_joint_image_path(joint_code)

    def _calc_sensitivity_value(self):
        """
        Рассчитывает требуемое значение чувствительности K по НП-105-18.

        По НП-105-18, п. 46 / Табл. 4.8:
            S_K = S + g_min + Sпк  (одна просвечиваемая стенка)
            S_K = S + S            (две стенки)

        Для расчёта расстояния f:
            S_рад(f) = S + g_max       (1 стенка)
            S_рад(f) = 2S + 2×g_max   (2 стенки)
        """
        from normative.calculations import calc_radiation_thickness

        S = self.params['wall_thickness']
        weld_cat = self.params['weld_category']
        scheme = self.data.get('scheme_type', '4_6')
        g_min = self.params.get('g_min_mm', 0.5)
        g_max = self.params.get('g_max_mm', 3.5)
        s_pk = self.params.get('backing_thickness_mm', 0.0)

        rad = calc_radiation_thickness(S, g_min, g_max, scheme, s_pk)
        self.params['rad_thickness'] = rad

        s_k = rad['s_rad_k_mm']
        K = get_sensitivity(s_k, weld_cat)
        mm_val = get_sensitivity_mm(s_k, weld_cat)

        self.params['required_sensitivity_pct'] = K
        self.params['required_sensitivity_mm'] = mm_val
        self.params['required_sensitivity_norm_mm'] = mm_val
        self.params['s_k_mm'] = s_k
        self.params['s_rad_f_mm'] = rad['s_rad_f_mm']

        if rad['wall_count'] == 2:
            sk_desc = f'S_K = S + S = {S} + {S} = {s_k} мм'
        elif s_pk > 0:
            sk_desc = f'S_K = S + g_min + Sпк = {S} + {g_min} + {s_pk} = {s_k} мм'
        else:
            sk_desc = f'S_K = S + g_min = {S} + {g_min} = {s_k} мм'

        self.params['sk_desc'] = sk_desc
        self.params['sensitivity_k_display_mm'] = mm_val
        self.params['sensitivity_desc'] = _format_sensitivity_desc(
            mm_val, sk_desc, self.params.get('weld_category', ''),
        )

    def _select_sources(self):
        S = self.params['wall_thickness']
        material_type = self.params.get('material_type', 'steel')
        rad = self.params.get('rad_thickness') or {}
        table_b_thickness = rad.get('s_rad_f_mm', S)
        suitable = get_suitable_sources(table_b_thickness, material_type)
        self.params['suitable_sources'] = suitable
        chosen_code = self.params['source_code']
        if chosen_code:
            match = next((s for s in suitable if s['code'] == chosen_code), None)
            if match:
                self.params['selected_source'] = match
            else:
                self.warnings.append(
                    f'Источник {chosen_code} не допускается табл. '
                    f'Б.{ {"steel": "1", "aluminum": "2", "titanium": "3"}.get(material_type, "1") } '
                    f'для радиационной толщины {table_b_thickness} мм и выбранного материала.'
                )
                self.params['selected_source'] = suitable[0] if suitable else {}
        else:
            self.params['selected_source'] = suitable[0] if suitable else {}

    def _calc_geometric_params(self):
        """
        Рассчитывает геометрическую нерезкость.
        Если f (SFD) не задан пользователем — использует f_min из расчёта схемы.
        """
        focal = self.params['source_focal_spot_mm']
        ofd = self.params['ofd_mm']
        weld_cat = self.params['weld_category']
        sensitivity_mm = self.params.get('required_sensitivity_mm', 0)

        # Если SFD не задан вручную — используем рассчитанное f_min
        sfd = self.params.get('sfd_mm') or 0
        scheme_result = self.params.get('exposure_scheme') or {}
        f_min = scheme_result.get('f_min_mm') or 0

        # Итоговое SFD — максимум из введённого и рассчитанного минимума
        sfd_used = max(sfd, f_min) if f_min else (sfd or 700)
        self.params['sfd_used_mm'] = round(sfd_used, 1)

        # Расчёт Ug через модуль calculations (с проверкой ГОСТ)
        ug_result = calc_geometric_unsharpness_full(focal, ofd, sfd_used, sensitivity_mm)

        if ug_result.get('error'):
            self.errors.append(ug_result['error'])
            ug = 0
            ug_ok = False
        else:
            ug = ug_result['ug_mm']
            ug_ok = ug_result.get('gost_ok', True)
            if ug_ok is False:
                max_allowed = ug_result.get('max_allowed_mm', '')
                self.warnings.append(
                    f'Геометрическая нерезкость Ug = {ug:.3f} мм '
                    f'превышает допустимую {max_allowed} мм для K = {sensitivity_mm:.3f} мм.'
                )

        max_ug = ug_result.get('max_allowed_mm') or MAX_GEOMETRIC_UNSHARPNESS.get(weld_cat, 0.5)
        self.params['geometric_unsharpness_mm'] = ug
        self.params['max_geometric_unsharpness_mm'] = max_ug
        self.params['geometric_unsharpness_ok'] = ug <= max_ug
        self.params['ug_calculation'] = ug_result.get('formula', f'Ug = {ug:.3f} мм')

    def _calc_exposure_scheme(self):
        """
        Вычисляет точные параметры просвечивания (f, N, L) по выбранной схеме.
        Использует алгоритмы из normative.calculations (порт из KalkulatorRK2).
        """
        S = self.params['wall_thickness']
        D = self.params['outer_diameter']
        # Внутренний диаметр: D - 2×S
        d_inner = D - 2 * S if D else 0
        self.params['d_inner_mm'] = round(d_inner, 1)

        focal = self.params['source_focal_spot_mm']
        sensitivity_mm = self.params.get('required_sensitivity_mm', 0.5)

        # Схема просвечивания — выбор пользователя или авторекомендация
        scheme = self.data.get('scheme_type', '').strip()
        if not scheme:
            recommended = recommend_scheme(D, d_inner)
            scheme = recommended[0] if recommended else '4_6'
            self.params['scheme_auto_selected'] = True

        sens = sensitivity_mm if sensitivity_mm > 0 else 0.5
        calc_kwargs = dict(
            scheme=scheme,
            focal_spot_mm=focal,
            sensitivity_mm=sens,
            thickness_mm=S,
            d_outer_mm=D or 0,
            d_inner_mm=d_inner,
        )

        if scheme == '5b':
            # Длина плёнки — вход 5б; сначала оценка L с максимальным типовым размером
            initial_length = float(parse_film_size('480x100')['length_mm'])
            calc_result = calc_exposure_parameters(
                **calc_kwargs, film_length_mm=initial_length,
            )
            film_size = select_film_size_for_length(calc_result.get('L_mm'))
            film_length = float(film_size['length_mm'])
            if film_length != initial_length:
                calc_result = calc_exposure_parameters(
                    **calc_kwargs, film_length_mm=film_length,
                )
                film_size = select_film_size_for_length(calc_result.get('L_mm'))
                film_length = float(film_size['length_mm'])
        else:
            calc_result = calc_exposure_parameters(**calc_kwargs)
            film_size = select_film_size_for_length(calc_result.get('L_mm'))

        film_length = float(film_size['length_mm'])
        film_width = float(film_size['width_mm'])

        if calc_result.get('error'):
            self.warnings.append(f'Схема {scheme}: {calc_result["error"]}')

        # Информация о схеме (описание, изображение)
        scheme_info = SCHEME_INFO.get(scheme, {})

        # Флаг «опытным путём» по ГОСТ Р 50.05.07-2018 п. Г.5
        is_empirical = calc_result.get('is_empirical', False)
        empirical_reason = calc_result.get('empirical_reason', '')

        self.params['scheme_type'] = scheme
        self.params['exposure_scheme'] = calc_result
        self.params['scheme_info'] = scheme_info
        self.params['is_empirical'] = is_empirical
        self.params['empirical_reason'] = empirical_reason

        if is_empirical:
            # Расчётные значения для справки (или None)
            self.params['f_calculated_mm'] = clamp_f_mm(calc_result.get('f_min_mm'))
            self.params['N_calculated'] = calc_result.get('N', '')
            self.params['L_calculated_mm'] = calc_result.get('L_mm', '')
        else:
            self.params['f_calculated_mm'] = clamp_f_mm(calc_result.get('f_min_mm'))
            self.params['N_calculated'] = calc_result.get('N', '')
            self.params['L_calculated_mm'] = calc_result.get('L_mm', '')

        self.params['scheme_formula'] = calc_result.get('formula', '')
        self.params['scheme_notes'] = calc_result.get('notes', '')
        self.params['scheme_image'] = scheme_info.get('image', '')
        self.params['C_coeff'] = calc_result.get('C', '')
        self.params['film_size_code'] = film_size['code']
        self.params['film_length_mm'] = film_length
        self.params['film_width_mm'] = film_width
        self.params['film_size_label'] = film_size['label']

    def _select_film(self):
        weld_cat = self.params['weld_category']
        recommended = [f for f in FILM_CLASSES if weld_cat in f['allowed_for']]
        self.params['recommended_film_classes'] = recommended
        self.params['film_class_info'] = recommended[0] if recommended else {}
        od = OPTICAL_DENSITY.get(weld_cat, OPTICAL_DENSITY['III'])
        self.params['optical_density_min'] = od['min']
        self.params['optical_density_max'] = od['max']

    def _calc_screens(self):
        source_code = (self.params.get('selected_source') or {}).get('code', '')
        screens = SCREEN_REQUIREMENTS.get(source_code, {
            'front_mm': '0,10', 'back_mm': '0,20',
            'material': 'Свинцовые (Pb)', 'note': '',
        })
        self.params['screens'] = screens

    def _calc_iqi(self):
        from normative.gost_7512 import get_wire_iqi, resolve_iqi_placement, WIRE_IQI_TYPE

        self.params['recommended_iqi'] = dict(WIRE_IQI_TYPE)

        mm_val = self.params.get('required_sensitivity_mm', 0)
        scheme = self.params.get('scheme_type', self.data.get('scheme_type', '4_6'))
        material_type = self.params.get('material_type', 'steel')
        iqi_side = self.params.get('iqi_side', 'source')
        rad_f = self.params.get('s_rad_f_mm', self.params['wall_thickness'])

        placement = resolve_iqi_placement(scheme, wall_count=0, iqi_side=iqi_side)
        self.params['iqi_placement'] = placement
        self.params['iqi_side'] = iqi_side

        iqi_wire = get_wire_iqi(
            rad_f, mm_val,
            material_type=material_type,
            shift_steps=placement['shift_steps'],
        )
        self.params['iqi_wire'] = iqi_wire
        self.params['iqi_marking'] = iqi_wire['marking']
        self.params['iqi_material_code'] = iqi_wire['material_code']
        self.params['iqi_set_number'] = iqi_wire['set_number']
        self.params['iqi_wire_number'] = iqi_wire['wire_number']
        self.params['iqi_wire_diameter_mm'] = iqi_wire['wire_diameter_mm']
        self.params['iqi_label'] = iqi_wire['label']

        norm_k = self.params.get('required_sensitivity_norm_mm', mm_val)
        sk_desc = self.params.get('sk_desc', '')
        weld_cat = self.params.get('weld_category', '')
        film_side = bool(placement.get('shift_steps'))

        if film_side:
            display_k = iqi_wire['wire_diameter_mm']
            self.params['sensitivity_k_display_mm'] = display_k
            self.params['sensitivity_desc'] = _format_sensitivity_desc(
                display_k, sk_desc, weld_cat,
                norm_k_mm=norm_k, film_side=True,
            )
        else:
            self.params['sensitivity_k_display_mm'] = norm_k

    def _fill_processing(self):
        self.params['film_processing'] = FILM_PROCESSING

    def _fill_personnel(self):
        weld_cat = self.params['weld_category']
        self.params['personnel_requirements'] = PERSONNEL_REQUIREMENTS.get(
            weld_cat, PERSONNEL_REQUIREMENTS['III']
        )

    def _fill_safety(self):
        self.params['safety_requirements'] = SAFETY_REQUIREMENTS

    def _fill_acceptance_criteria(self):
        weld_cat = self.params['weld_category']
        self.params['quality_normative'] = NP105_CODE
        self.params['quality_criteria_summary'] = (
            f'По {NP105_CODE}, категория {weld_cat}. '
            f'Трещины, несплавления, непровары — не допускаются. '
            f'Поры и шлаковые включения — по Таблице 1 {NP105_CODE}.'
        )

    def _calc_control_volume(self):
        """Объём контроля по категории (НП-104-18)."""
        cat_info = WELD_CATEGORIES.get(self.params['weld_category'], {})
        self.params['control_volume_pct'] = cat_info.get('control_volume', 100)


# ---------------------------------------------------------------
# Заполнение шаблона
# ---------------------------------------------------------------

_WELD_TYPE_NAMES = {
    'butt': 'Стыковое', 'corner': 'Угловое (У)',
    'tee': 'Тавровое (Т)', 'lap': 'Нахлёсточное (Н)',
}

_JOINT_MOBILITY_LABELS = {
    'rotating': 'поворотное',
    'non_rotating': 'неповоротное',
}


def _fmt_mm(value, decimals: int = 1) -> str:
    """Форматирует размер в мм с запятой для техкарты."""
    if value is None or value == '' or value == '—':
        return '—'
    try:
        return f'{float(value):.{decimals}f}'.replace('.', ',')
    except (TypeError, ValueError):
        return str(value)


def _format_signature_block(
    position: str,
    name: str,
    certificate: str,
    date_str: str,
    default_position: str = '',
) -> str:
    """Блок подписи для нижнего колонтитула."""
    lines = [position or default_position]
    if name:
        lines.append(name)
    if certificate:
        lines.append(f'Удостоверение № {certificate}')
    lines.append(f'«{date_str}» ___________')
    return '\n'.join(filter(None, lines))

_OBJECT_TYPE_NAMES = {
    'pipe': 'Трубопровод (кольцевой сварной шов)',
    'flat': 'Плоская деталь / пластина',
    'vessel': 'Сосуд давления / обечайка',
}


def _build_value_map(params: dict) -> dict:
    """
    Строит словарь: фрагмент метки → точное значение для заполнения ячейки шаблона.

    Использует рассчитанные значения из normative.calculations:
    f (расстояние), N (число экспозиций), L (длина участка), C (коэффициент).
    """
    src = params.get('selected_source') or {}
    scheme_result = params.get('exposure_scheme') or {}
    scheme_info = params.get('scheme_info') or {}
    iqi = params.get('recommended_iqi') or {}
    placement = params.get('iqi_placement') or {}
    screens = params.get('screens') or {}
    film_info = params.get('film_class_info') or {}
    pers = params.get('personnel_requirements') or {}
    fp = params.get('film_processing') or {}
    dev_opts = (fp.get('developer') or {}).get('options') or [{}]
    fix_opts = (fp.get('fixer') or {}).get('options') or [{}]
    d_opt = dev_opts[0]
    f_opt = fix_opts[0]

    S = params.get('wall_thickness', 0)
    D = params.get('outer_diameter', 0)
    d_inner = params.get('d_inner_mm', 0)

    # ---- Рассчитанные параметры просвечивания ----
    f_val = params.get('f_calculated_mm', '')
    N_val = params.get('N_calculated', '')
    L_val = params.get('L_calculated_mm', '')
    C_val = params.get('C_coeff', '')
    sfd_used = params.get('sfd_used_mm', params.get('sfd_mm', ''))
    is_empirical = params.get('is_empirical', False)
    empirical_reason = params.get('empirical_reason', '')

    # --- Формирование полей 6.5, 6.6, 6.7, 6.8 ---
    EMPIRICAL_TEXT = (
        'Определяется опытным путём в соответствии с требованиями '
        'ГОСТ Р 50.05.07-2018, п. Г.5'
    )

    if is_empirical:
        # Схемы 3б (l < d_вн) и 3ж: f и N — опытным путём
        f_field = EMPIRICAL_TEXT
        N_str = 'Определяется опытным путём (ГОСТ Р 50.05.07-2018, п. Г.5)'
        l_field = 'Определяется опытным путём (ГОСТ Р 50.05.07-2018, п. Г.5)'
        if f_val is not None and f_val != '':
            f_field += f'\n(справочно: f_расч ≥ {f_val} мм)'
        if N_val:
            N_str += f'\n(справочно: N_расч ≥ {N_val})'
    else:
        # Обычные схемы: показываем рассчитанные значения
        if f_val is not None and f_val != '':
            f_field = (
                f'f = {f_val} мм '
                f'(расчёт: {params.get("scheme_formula", "")})'
            )
        else:
            f_field = f'{sfd_used} мм'

        N_str = str(N_val) if N_val else '—'

        if L_val:
            l_field = (
                f'{L_val} мм = π × {D} / {N_val}'
                if D and N_val else f'{L_val} мм'
            )
        else:
            l_field = '350 × (длина шва / N) мм'

    # Поле 6.9: схема просвечивания
    scheme_code = params.get('scheme_type', '')
    scheme_name = scheme_info.get('name') or scheme_code
    scheme_desc = scheme_info.get('description', '')
    scheme_notes = params.get('scheme_notes', '')
    if is_empirical and empirical_reason:
        scheme_notes = empirical_reason
    scheme_formula = params.get('scheme_formula', '') if not is_empirical else ''
    scheme_field = '\n'.join(filter(None, [scheme_name, scheme_desc, scheme_formula, scheme_notes]))

    # Угол просвечивания (для поля 6.4)
    angle = '0° (перпендикуляр к поверхности контроля)'
    if params.get('scheme_type') in ('5a', '5b', '5v', '5g', '5d', '5zh', '5z'):
        angle = 'По схеме просвечивания (90° к оси шва)'

    # Коэффициент C для поля 5.2
    focal_field = _fmt_mm(params.get('source_focal_spot_mm', ''))
    if C_val:
        focal_field += f' (C = {C_val:.2f})'

    object_type = params.get('object_type', 'pipe')
    joint_code = params.get('joint_designation', '')
    from normative.gost_59023_2 import get_joint_info
    joint_info = get_joint_info(joint_code) if joint_code else {}
    joint_type = joint_info.get('joint_type', 'butt')
    mobility = _JOINT_MOBILITY_LABELS.get(
        params.get('joint_mobility', 'non_rotating'), 'неповоротное',
    )
    weld_cat = params.get('weld_category', '')

    if object_type == 'pipe':
        outer_d_display = _fmt_mm(D) if D else '—'
        flat_length_display = '—'
    elif object_type == 'flat':
        outer_d_display = '—'
        flat_length_display = _fmt_mm(params.get('flat_length_mm')) if params.get('flat_length_mm') else '—'
    else:
        outer_d_display = _fmt_mm(D) if D else '—'
        flat_length_display = '—'

    backing_label = 'Есть' if params.get('has_backing') else 'Нет'
    backing_thickness_display = (
        f'{_fmt_mm(params.get("backing_thickness_mm"))} мм (учитывать в K, f)'
        if params.get('has_backing') and params.get('backing_thickness_mm')
        else '—'
    )

    return {
        # ---- Раздел 1: Объект контроля ----
        '1.1': params.get('organization', ''),
        '1.2': params.get('object_name', ''),
        '1.3': params.get('drawing_number', ''),
        '1.4': params.get('weld_number', ''),
        '1.5': params.get('drawing_number', ''),
        '1.6': f'{_WELD_TYPE_NAMES.get(joint_type, "Стыковое")} ({mobility})',
        '1.7': (
            f'{joint_code}, по ГОСТ Р 59023.2-2020'
            if joint_code else ''
        ),
        '1.8': (
            f'{params.get("welding_process", "")} — '
            + {
                '10': 'АДФ под флюсом', '11': 'АДФ с подваркой корня', '20': 'ЭШС',
                '30': 'РДС', '31': 'РДС с подваркой корня', '32': 'РДС на подкладке',
                '40': 'Комбинированная (корень АДС)', '42': 'Комбинированная на подкладке',
                '51': 'АДС без присадки', '52': 'АДС с присадкой', '53': 'АДС плавящимся',
                '60': 'ЭЛС',
            }.get(params.get('welding_process', ''), '')
            + ', по ГОСТ Р 59023.2-2020'
            if params.get('welding_process') else ''
        ),
        '1.9': params.get('material_display', params.get('material', '')),
        '1.10': params.get('weld_material', ''),

        # ---- Раздел 2: Документация ----
        '2.1': DOCUMENT_CODE,
        '2.2': NP105_CODE,

        # ---- Раздел 3: Требования ----
        '3.1': f'{weld_cat} (по НП-105-18)',
        '3.2': f'{params.get("control_volume_pct", 100)} %',

        # ---- Раздел 4: Тип и размеры ----
        '4.1': _OBJECT_TYPE_NAMES.get(object_type, ''),
        '4.2.1': outer_d_display,
        'толщина': _fmt_mm(S),
        '4.2.2 длин': flat_length_display,
        '4.2.2': params.get('e_display', ''),
        '4.2.2 e1': params.get('e1_display', ''),
        '4.2.3': params.get('g_display', params.get('reinforcement_status', 'не снят')),
        '4.2.4': f'{_fmt_mm(params.get("haz_width_mm", 5.0))} мм (с каждой стороны от краёв шва)',
        '4.2.5': _fmt_mm(params.get('zone_width_mm', '')),
        '4.2.6': backing_label,
        '4.2.7': backing_thickness_display,

        # ---- Раздел 5: Средства контроля ----
        '5.1': src.get('name', ''),
        '5.2': focal_field,
        '5.3': (
            f"Проволочный / №{params.get('iqi_marking', '')} по ГОСТ 7512 "
            f"({placement.get('side_label', 'со стороны источника')})"
        ),
        '5.4': params.get('film_name', film_info.get('examples', '')),
        '5.5': 'в светонепроницаемую плёночную (гибкую) кассету',
        '5.6': 'свинцовые буквы и цифры по ГОСТ',
        '5.7': f'{params.get("film_length_mm", 240):.0f} × {params.get("film_width_mm", 100):.0f} мм',
        '5.9': 'негатоскоп с яркостью ≥ 10 000 кд/м², ГОСТ Р 8.763',
        '5.11': 'денситометр фотометрический',
        '5.12': 'лупа 10× измерительная',
        '5.14': (
            f'Проявитель: {d_opt.get("name","стандартный")}, '
            f't = {d_opt.get("temp_c","20±1")}°C, '
            f'τ = {d_opt.get("time_min","5–8")} мин; '
            f'Закрепитель: {f_opt.get("name","")}, '
            f'τ = {f_opt.get("time_min","10–15")} мин'
        ),

        # ---- Раздел 6: Параметры и схема контроля (РАССЧИТАННЫЕ) ----
        '6.1': src.get('energy_display', ''),
        '6.2': (
            f'S_K = {params.get("s_k_mm", "—")} мм → '
            f'K ≤ {params.get("required_sensitivity_norm_mm", params.get("required_sensitivity_mm", "—")):.3f} мм '
            f'(НП-105-18, Табл. 4.8, кат. {params.get("weld_category", "")});  '
            f'Sрад(f) = {params.get("rad_thickness", {}).get("formula_f", "—")}'
        ),
        '6.3': (
            f'K ≤ {params.get("sensitivity_k_display_mm", params.get("required_sensitivity_mm", "—")):.3f} мм'
            if params.get('sensitivity_k_display_mm') is not None
            else params.get('sensitivity_desc', '')
        ),
        '6.4': angle,
        '6.5': f_field,    # ← РАССЧИТАННОЕ расстояние f
        '6.6': N_str,      # ← РАССЧИТАННОЕ число экспозиций N
        '6.7': N_str,      # ← Число контролируемых участков = N
        '6.8': l_field,    # ← РАССЧИТАННАЯ длина участка L
        '6.9': scheme_field,   # ← Схема просвечивания с описанием

        # ---- Разделы 7–8: Подготовка и условия ----
        '7.1': (
            f'Dн = {D} мм, Dвн = {d_inner:.1f} мм, S = {S} мм'
            if D else f'S = {S} мм'
        ),
        '8.3': pers.get('level', ''),
        '8.4': '+5 ÷ +40',
    }


def _set_paragraph_text(
    para,
    text: str,
    *,
    font_size: int | None = None,
    bold: bool | None = None,
):
    """Заменяет текст параграфа, сохраняя оформление шаблона."""
    ref = _reference_run_in_paragraph(para)
    if para.runs:
        run = para.runs[0]
        run.text = str(text) if text is not None else ''
        for extra in para.runs[1:]:
            extra.text = ''
    else:
        run = para.add_run(str(text) if text is not None else '')
    if bold is not None:
        run.bold = bold
    elif ref is not None:
        run.bold = ref.bold
    if font_size is not None:
        run.font.size = Pt(font_size)
    elif ref is not None and ref.font.size:
        run.font.size = ref.font.size
    else:
        run.font.size = Pt(12)
    if ref is not None:
        _copy_run_font(ref, run)
        if bold is not None:
            run.bold = bold
        if font_size is not None:
            run.font.size = Pt(font_size)


def _paragraph_has_drawing(para) -> bool:
    wp_ns = '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}'
    el = para._element
    return bool(el.findall(f'.//{wp_ns}inline') or el.findall(f'.//{wp_ns}anchor'))


def _clear_paragraph_content(para):
    """Удаляет все run-элементы параграфа (в т.ч. встроенные рисунки)."""
    p_el = para._element
    for child in list(p_el):
        if child.tag.endswith('}r'):
            p_el.remove(child)


def _resolve_static_image_path(static_root: str, image_rel: str) -> str | None:
    """Ищет файл изображения относительно каталога static/."""
    if not image_rel or not static_root:
        return None
    rel = image_rel.replace('\\', '/').lstrip('/')
    if rel.startswith('img/'):
        candidates = [os.path.join(static_root, rel)]
    else:
        candidates = [
            os.path.join(static_root, 'img', 'welds', rel),
            os.path.join(static_root, rel),
            os.path.join(static_root, 'img', rel),
        ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _picture_source_for_docx(image_path: str):
    """Возвращает путь или BytesIO для add_picture (в т.ч. SVG → PNG)."""
    if image_path.lower().endswith('.svg'):
        try:
            import cairosvg
            return io.BytesIO(cairosvg.svg2png(url=image_path))
        except Exception:
            logger.warning('Не удалось конвертировать SVG для DOCX: %s', image_path)
            return None
    return image_path


def _insert_picture_in_paragraph(para, image_path: str, width_mm: float = 40):
    """Вставляет изображение в параграф DOCX."""
    source = _picture_source_for_docx(image_path)
    if source is None:
        return False
    _clear_paragraph_content(para)
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run()
    run.add_picture(source, width=Mm(width_mm))
    return True


def _find_paragraph_index(doc: Document, fragment: str) -> int:
    needle = fragment.lower()
    for idx, para in enumerate(doc.paragraphs):
        if needle in para.text.lower():
            return idx
    return -1


def _insert_joint_sketch_into_docx(doc: Document, params: dict, static_root: str):
    """
    Вставляет эскиз сварного соединения в п. 4.3 шаблона техкарты.

    Используется то же изображение, что на шаге 3 (get_joint_image_path).
    """
    from normative.gost_59023_2 import get_joint_image_path

    idx = _find_paragraph_index(doc, '4.3')
    if idx < 0 or 'эскиз' not in doc.paragraphs[idx].text.lower():
        return

    joint_code = params.get('joint_designation', '')
    image_rel = params.get('joint_image') or get_joint_image_path(joint_code)
    image_path = _resolve_static_image_path(static_root, image_rel)
    if not image_path:
        logger.warning('Эскиз шва не найден: %s', image_rel)
        return

    if idx + 1 < len(doc.paragraphs):
        _insert_picture_in_paragraph(doc.paragraphs[idx + 1], image_path, width_mm=42)

    if idx + 2 < len(doc.paragraphs):
        caption = doc.paragraphs[idx + 2]
        if joint_code:
            _set_paragraph_text(
                caption,
                f'Сварное соединение {joint_code} по ГОСТ Р 59023.2-2020',
                font_size=9,
            )


def _insert_scheme_section_into_docx(doc: Document, params: dict, static_root: str):
    """
    Вставляет изображение схемы просвечивания в п. 6.9 (параграфы шаблона).
    """
    scheme_info = params.get('scheme_info') or {}
    image_rel = scheme_info.get('image', '')
    if not image_rel:
        return

    image_path = _resolve_static_image_path(static_root, image_rel)
    if not image_path:
        return

    idx = _find_paragraph_index(doc, '6.9')
    if idx < 0:
        return

    scheme_name = scheme_info.get('name') or params.get('scheme_type', '')
    scheme_desc = scheme_info.get('description', '')
    caption_text = ' '.join(filter(None, [scheme_name, scheme_desc])).strip()

    image_paras = []
    caption_para = None
    for para in doc.paragraphs[idx + 1: idx + 8]:
        text = para.text.strip()
        if _paragraph_has_drawing(para):
            image_paras.append(para)
        elif text and 'черт' in text.lower():
            caption_para = para
            break

    if image_paras:
        _insert_picture_in_paragraph(image_paras[0], image_path, width_mm=45)
        for extra in image_paras[1:]:
            _clear_paragraph_content(extra)

    if caption_para and caption_text:
        _set_paragraph_text(caption_para, caption_text, font_size=9)
    elif caption_text and idx + 4 < len(doc.paragraphs):
        _set_paragraph_text(doc.paragraphs[idx + 4], caption_text, font_size=9)


def _fill_dimension_rows(doc: Document, value_map: dict):
    """Заполняет многоячеечные строки раздела 4.2 шаблона техкарты."""
    for table in doc.tables:
        for row in table.rows:
            ucells = _unique_cells(row)
            if not ucells:
                continue
            label = ucells[0].text.strip().lower()

            if '4.2.1' in label and 'внешний' in label and len(ucells) >= 4:
                _set_cell_text(ucells[1], value_map.get('4.2.1', '—'))
                _set_cell_text(ucells[3], value_map.get('толщина', ''))
                continue

            if ('длинна' in label or 'длина' in label) and '4.2.2' in label:
                if len(ucells) >= 2:
                    _set_cell_text(ucells[1], value_map.get('4.2.2 длин', '—'))
                continue

            if 'наружной поверхности' in label and len(ucells) >= 4:
                _set_cell_text(ucells[1], value_map.get('4.2.2', ''))
                _set_cell_text(ucells[3], value_map.get('4.2.2 e1', ''))
                continue

            if '4.2.3' in label and 'высота' in label:
                if len(ucells) >= 2:
                    _set_cell_text(ucells[-1], value_map.get('4.2.3', ''))
                continue

            if '4.2.4' in label and 'околошовной' in label and len(ucells) >= 4:
                _set_cell_text(ucells[1], value_map.get('4.2.4', ''))
                _set_cell_text(ucells[3], value_map.get('4.2.5', ''))
                continue

            if '4.2.6' in label and len(ucells) >= 4:
                _set_cell_text(ucells[1], value_map.get('4.2.6', ''))
                _set_cell_text(ucells[3], value_map.get('4.2.7', ''))


def generate_from_template(params: dict, template_path: str, output_path: str,
                           static_root: str = '') -> str:
    """
    Заполняет шаблон DOCX технологической карты расчётными данными.

    Стратегия:
    1. Открывает оригинальный шаблон как копию.
    2. Для каждой таблицы, для каждой строки находит ячейку-метку
       и записывает значение в ячейку-значение (последнюю уникальную ячейку строки).
    3. Заменяет плейсхолдер организации в шапке.
    4. Сохраняет результат.

    :param params: рассчитанные параметры техкарты
    :param template_path: путь к файлу шаблона
    :param output_path: путь для сохранения результата
    :return: путь к созданному файлу
    """
    doc = Document(template_path)
    _remove_docx_comments(doc)
    value_map = _build_value_map(params)

    # --- Замена в таблицах ---
    for table in doc.tables:
        for row in table.rows:
            ucells = _unique_cells(row)
            if not ucells:
                continue

            label_text = ucells[0].text.strip()
            value_cell = ucells[-1] if len(ucells) >= 2 else None

            matched_value = _match_value_for_label(label_text, value_map)

            if matched_value is not None and value_cell is not None:
                # Не перезаписываем, если ячейка та же что и метка
                if value_cell._tc is not ucells[0]._tc:
                    _set_cell_text(value_cell, matched_value)

    _fill_dimension_rows(doc, value_map)

    _insert_joint_sketch_into_docx(doc, params, static_root)
    _insert_scheme_section_into_docx(doc, params, static_root)

    # Титульный лист и колонтитулы — по структуре шаблона normative_docs
    _fill_body_title_page(doc, params)
    _fill_template_headers_footers(doc, params)

    # --- Раздел 10 «Оценка качества» на отдельном листе ---
    _insert_page_break_before_section10(doc)

    # --- Компактизация документа ---
    _compact_document(doc)

    # Титул — только обложка; таблицы техкарты со 2-й страницы
    _insert_page_break_before_first_table(doc)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    return output_path


def _insert_scheme_image_into_docx(doc: Document, params: dict, static_root: str):
    """
    Вставляет изображение схемы просвечивания в поле 6.9 техкарты.

    Добавляет картинку и текстовое описание прямо в найденную ячейку
    (строка с меткой '6.9'). Поддерживает как однояченные (слитые),
    так и многоячеечные строки.

    :param doc: объект DOCX документа
    :param params: параметры техкарты (должен содержать scheme_info)
    :param static_root: путь к статическим файлам Django
    """
    scheme_info = params.get('scheme_info') or {}
    image_rel = scheme_info.get('image', '')

    if not image_rel:
        return

    # Схемы хранятся в static/img/ (не img/welds/)
    image_path = os.path.join(static_root, image_rel)
    if not os.path.exists(image_path):
        # Попробуем без поддиректории
        alt_path = os.path.join(static_root, os.path.basename(image_rel))
        if os.path.exists(alt_path):
            image_path = alt_path
        else:
            return   # Файл не найден — пропускаем без ошибки

    scheme_result = params.get('exposure_scheme') or {}
    scheme_name = scheme_info.get('name', '')
    scheme_desc = scheme_info.get('description', '')
    n_exp = scheme_result.get('n_exposures_min', '')
    rad_note = params.get('rad_thickness', {}).get('wall_desc', '')

    # Ищем ячейку с меткой "6.9"
    for table in doc.tables:
        for row in table.rows:
            ucells = _unique_cells(row)
            if not ucells:
                continue
            label_text = ucells[0].text.strip()
            if '6.9' in label_text:
                # Всегда вставляем в последнюю уникальную ячейку
                # (при слитой строке — это та же единственная ячейка)
                target_cell = ucells[-1]
                try:
                    # Добавляем изображение в новом параграфе ячейки
                    img_para = target_cell.add_paragraph()
                    img_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run_img = img_para.add_run()
                    run_img.add_picture(image_path, width=Mm(75))

                    # Добавляем подпись к схеме
                    desc_para = target_cell.add_paragraph()
                    desc_run = desc_para.add_run(
                        f'{scheme_name}. {scheme_desc}'
                    )
                    desc_run.font.size = Pt(8)
                    desc_run.italic = True

                    # Добавляем информацию о радиационной толщине
                    if rad_note:
                        rad_para = target_cell.add_paragraph()
                        s_rad_f = params.get('s_rad_f_mm', '')
                        rad_run = rad_para.add_run(
                            f'{rad_note}. '
                            f'S_K = {params.get("s_k_mm", "")} мм (для K); '
                            f'Sрад(f) = {s_rad_f} мм'
                        )
                        rad_run.font.size = Pt(8)

                    return   # Успешно вставили — выходим
                except Exception as exc:
                    # Логируем ошибку, но не падаем
                    import traceback
                    traceback.print_exc()
                    return


# ---------------------------------------------------------------
# Генерация PDF
# ---------------------------------------------------------------

def _insert_page_number_field(para):
    """
    Вставляет в параграф нумерацию «Страница N    M страниц».
    Используется для колонтитулов Word (поля PAGE / NUMPAGES).
    """
    def _field_run(instr_text: str):
        run = para.add_run()
        fc_begin = OxmlElement('w:fldChar')
        fc_begin.set(qn('w:fldCharType'), 'begin')
        instr = OxmlElement('w:instrText')
        instr.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        instr.text = instr_text
        fc_end = OxmlElement('w:fldChar')
        fc_end.set(qn('w:fldCharType'), 'end')
        run._r.append(fc_begin)
        run._r.append(instr)
        run._r.append(fc_end)

    para.add_run('Страница ')
    _field_run(' PAGE ')
    para.add_run(' ')
    _field_run(' NUMPAGES ')
    para.add_run(' страниц')


def _remove_docx_comments(doc: Document):
    """Удаляет комментарии Word из документа (служебные пометки шаблона)."""
    w_ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    comment_tags = (
        f'{{{w_ns}commentRangeStart',
        f'{{{w_ns}commentRangeEnd',
        f'{{{w_ns}commentReference',
    )
    roots = [doc.element.body]
    for section in doc.sections:
        roots.extend([
            section.header._element,
            section.footer._element,
            section.first_page_header._element,
            section.first_page_footer._element,
        ])
    for root in roots:
        for tag in comment_tags:
            for el in list(root.iter(tag)):
                parent = el.getparent()
                if parent is not None:
                    parent.remove(el)


def _clear_header_footer_part(part):
    """Удаляет все параграфы и таблицы из верхнего/нижнего колонтитула Word."""
    element = part._element
    for child in list(element):
        tag = child.tag.split('}')[-1]
        if tag in ('p', 'tbl'):
            element.remove(child)


def _clear_section_headers_footers(section):
    """
    Очищает все колонтитулы секции, включая отдельные для первой страницы.
    Шаблон DOCX использует different_first_page — без очистки first_page_*
    остаются старые «ФГУП МАРКС» / «Иванов» поверх новых колонтитулов.
    """
    for attr in (
        'header', 'footer',
        'first_page_header', 'first_page_footer',
    ):
        part = getattr(section, attr, None)
        if part is not None:
            _clear_header_footer_part(part)


def _replace_in_paragraph_runs(para, mapping: dict[str, str]):
    """Точечная замена текста в run-элементах без сброса вёрстки параграфа."""
    for run in para.runs:
        text = run.text
        for old, new in mapping.items():
            if old and old in text:
                text = text.replace(old, new)
        run.text = text


def _replace_in_cell(cell, mapping: dict[str, str]):
    for para in cell.paragraphs:
        _replace_in_paragraph_runs(para, mapping)


def _replace_in_table(table, mapping: dict[str, str]):
    for row in table.rows:
        for cell in row.cells:
            _replace_in_cell(cell, mapping)


def _replace_in_document_part(part, mapping: dict[str, str]):
    """Заменяет плейсхолдеры в колонтитуле, сохраняя форматирование шаблона."""
    for para in part.paragraphs:
        _replace_in_paragraph_runs(para, mapping)
    for table in part.tables:
        _replace_in_table(table, mapping)


def _replace_certificate_in_cell(cell, certificate: str):
    """Подставляет номер удостоверения, сохраняя строку шаблона с точками."""
    if not certificate:
        return
    for para in cell.paragraphs:
        for run in para.runs:
            if 'Удостоверение' in run.text:
                run.text = re.sub(
                    r'Удостоверение №[.\s…]+',
                    f'Удостоверение № {certificate}',
                    run.text,
                )


def _fill_header_card_number_cell(cell, card_num: str):
    """Заполняет ячейку «№» в шапке, не пересобирая параграф."""
    display = f'№ {card_num}'.strip() if card_num else '№'
    if not cell.paragraphs:
        cell.add_paragraph(display)
        return
    para = cell.paragraphs[0]
    if para.runs:
        para.runs[0].text = display
        for run in para.runs[1:]:
            run.text = ''
    else:
        para.add_run(display)
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _fill_body_title_page(doc: Document, params: dict):
    """
    Титульный лист в теле документа оставляем как в шаблоне:
    крупный заголовок и отдельная строка «№» (номер — в шапке).
    """
    card_num = (params.get('card_number') or '').strip()
    if not card_num:
        return
    for para in doc.paragraphs:
        stripped = para.text.strip()
        if stripped not in ('№', '№ '):
            continue
        if len(para.runs) >= 2:
            para.runs[1].text = f' {card_num}'
        elif para.runs:
            para.runs[0].text = f'№ {card_num}'
        else:
            para.add_run(f'№ {card_num}')
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        return


def _short_position_for_title_page(position: str) -> str:
    """Краткая должность для нижнего колонтитула титульного листа."""
    lower = (position or '').lower()
    if 'инженер' in lower:
        return 'Ведущий инженер'
    if 'начальник' in lower and 'лаборатор' in lower:
        return 'Начальник лаборатории'
    return position or ''


def _add_table_borders(table):
    """Добавляет границы таблице через XML (работает в headers/footers)."""
    tbl = table._tbl
    tblPr = tbl.find(qn('w:tblPr'))
    if tblPr is None:
        tblPr = OxmlElement('w:tblPr')
        tbl.insert(0, tblPr)
    tblBorders = OxmlElement('w:tblBorders')
    for border_name in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        border = OxmlElement(f'w:{border_name}')
        border.set(qn('w:val'), 'single')
        border.set(qn('w:sz'), '4')
        border.set(qn('w:space'), '0')
        border.set(qn('w:color'), '000000')
        tblBorders.append(border)
    tblPr.append(tblBorders)


def _fill_default_footer_table(table, params: dict):
    """Нижний колонтитул со 2-й и далее страниц (3×2, без дат)."""
    dev_pos = params.get('developed_by_position', '') or 'Ведущий инженер технолог'
    chk_pos = params.get('checked_by_position', '') or 'Начальник лаборатории НК'
    dev_name = params.get('developed_by_name', '') or params.get('inspector_name', '')
    chk_name = params.get('checked_by_name', '')
    dev_cert = params.get('developed_by_certificate', '')

    mapping = {
        'Ведущий инженер технолог': dev_pos,
        'Начальник лаборатории НК': chk_pos,
        'Иванов Н.Н.': dev_name,
        'Сидоров И.Н.': chk_name,
    }
    _replace_in_table(table, mapping)
    if dev_cert and len(table.rows) >= 3:
        _replace_certificate_in_cell(table.rows[2].cells[0], dev_cert)


def _fill_first_page_footer_table(table, params: dict):
    """Нижний колонтитул титульного листа — точечная замена в вёрстке шаблона."""
    dev_date = params.get('develop_date', datetime.now().strftime('%d.%m.%Y'))
    check_date = params.get('check_date', dev_date)
    dev_pos = _short_position_for_title_page(
        params.get('developed_by_position', '') or 'Ведущий инженер технолог',
    )
    chk_pos = _short_position_for_title_page(
        params.get('checked_by_position', '') or 'Начальник лаборатории НК',
    )
    dev_name = params.get('developed_by_name', '') or params.get('inspector_name', '')
    chk_name = params.get('checked_by_name', '')
    dev_cert = params.get('developed_by_certificate', '')

    if len(table.rows) < 3:
        return

    _replace_in_cell(table.rows[1].cells[0], {'Ведущий инженер': dev_pos})
    _replace_in_cell(table.rows[1].cells[1], {'Начальник лаборатории': chk_pos})
    _replace_in_cell(table.rows[2].cells[0], {
        'Иванов Н.Н.': dev_name,
        '21.06.2026': dev_date,
    })
    _replace_in_cell(table.rows[2].cells[1], {
        'Сидоров И.Н.': chk_name,
        '21.06.2026': check_date,
    })
    if dev_cert:
        _replace_certificate_in_cell(table.rows[2].cells[0], dev_cert)


def _fill_template_headers_footers(doc: Document, params: dict):
    """
    Заполняет колонтитулы шаблона техкарты данными пользователя.

    Шаблон normative_docs использует:
    - одинаковую шапку на всех страницах (header + first_page_header);
    - разные нижние колонтитулы: титул (3×3, даты/подписи) и остальные (3×2).
    """
    for section in doc.sections:
        section.different_first_page_header_footer = True
        sect_pr = section._sectPr
        if sect_pr.find(qn('w:titlePg')) is None:
            sect_pr.insert(0, OxmlElement('w:titlePg'))

        for header_part in (section.header, section.first_page_header):
            header_table = _find_header_table(header_part)
            if header_table is not None:
                _fill_template_header_table(header_table, params)

        default_footer = _find_footer_table(section.footer)
        if default_footer is not None:
            _fill_default_footer_table(default_footer, params)

        first_footer = _find_footer_table(section.first_page_footer)
        if first_footer is not None:
            _fill_first_page_footer_table(first_footer, params)


def _find_header_table(part):
    """Находит таблицу шапки в колонтитуле (2×3, «Технологическая карта»)."""
    for table in part.tables:
        if len(table.rows) >= 2 and len(table.columns) >= 3:
            text = ' '.join(cell.text for row in table.rows for cell in row.cells)
            if 'Технологическая карта' in text:
                return table
    return part.tables[0] if part.tables else None


def _find_footer_table(part):
    """Находит таблицу подписей в нижнем колонтитуле."""
    for table in part.tables:
        text = ' '.join(cell.text for row in table.rows for cell in row.cells)
        if 'Разработал' in text and 'Проверил' in text:
            return table
    return part.tables[0] if part.tables else None


def _fill_page_number_cell(cell):
    """Заменяет статичную нумерацию шаблона полями PAGE / NUMPAGES."""
    para = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
    ref = _reference_run_in_paragraph(para)
    for extra in cell.paragraphs[1:]:
        _clear_paragraph_content(extra)
    _clear_paragraph_content(para)
    _insert_page_number_field(para)
    for run in para.runs:
        if ref is not None:
            _copy_run_font(ref, run)
        elif not run.font.size:
            run.font.size = Pt(12)


def _insert_page_break_before_first_table(doc: Document):
    """
    Вставляет разрыв страницы перед первой таблицей тела документа.
    Титульный лист остаётся без таблиц техкарты (как обложка).
    """
    body = doc.element.body
    for child in list(body):
        if child.tag.split('}')[-1] != 'tbl':
            continue
        p_el = OxmlElement('w:p')
        r_el = OxmlElement('w:r')
        br_el = OxmlElement('w:br')
        br_el.set(qn('w:type'), 'page')
        r_el.append(br_el)
        p_el.append(r_el)
        body.insert(list(body).index(child), p_el)
        return


def _fill_template_header_table(table, params: dict):
    """Заполняет шапку, сохраняя табличную вёрстку шаблона."""
    org = params.get('organization', '') or 'Наименование организации'
    card_num = params.get('card_number', '')
    r0 = table.rows[0]
    r1 = table.rows[1]
    _replace_in_cell(r0.cells[0], {
        'ФГУП МАРКС': org,
        'Наименование организации': org,
    })
    if len(r1.cells) > 1:
        _fill_header_card_number_cell(r1.cells[1], card_num)
    if len(r1.cells) > 2:
        _fill_page_number_cell(r1.cells[2])


def _build_headers_footers_scratch(doc: Document, params: dict):
    """
    Создаёт колонтитулы с нуля (только для fallback без шаблона DOCX).
    """
    org = params.get('organization', '')
    card_num = params.get('card_number', '___')
    dev_date = params.get('develop_date', datetime.now().strftime('%d.%m.%Y'))
    check_date = params.get('check_date', dev_date)

    section = doc.sections[0]
    section.header_distance = Mm(8)
    section.footer_distance = Mm(10)
    section.different_first_page_header_footer = False
    _clear_section_headers_footers(section)

    # ---- Верхний колонтитул ----
    header = section.header

    # Таблица 2 строки × 3 столбца
    ht = header.add_table(rows=2, cols=3, width=Mm(185))
    _add_table_borders(ht)
    for i, w in enumerate([Mm(55), Mm(100), Mm(30)]):
        for cell in ht.columns[i].cells:
            cell.width = w

    # Строка 1: организация | заголовок | пусто
    r0 = ht.rows[0]
    _set_cell_text(r0.cells[0], org or 'Наименование организации', font_size=8)
    _set_cell_text(
        r0.cells[1],
        'Технологическая карта радиографического контроля',
        bold=True, font_size=9,
    )
    r0.cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Строка 2: номер карты | номер карты | Лист X / Листов Y
    r1 = ht.rows[1]
    _set_cell_text(r1.cells[0], '', font_size=8)
    _set_cell_text(r1.cells[1], f'№ {card_num}', font_size=9)
    r1.cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Поле нумерации страниц в правой ячейке
    page_para = r1.cells[2].paragraphs[0]
    _insert_page_number_field(page_para)

    # ---- Нижний колонтитул ----
    footer = section.footer

    # Таблица 3 строки × 2 столбца (структура шаблона)
    ft = footer.add_table(rows=3, cols=2, width=Mm(185))
    _add_table_borders(ft)
    for cell in ft.columns[0].cells:
        cell.width = Mm(90)
    for cell in ft.columns[1].cells:
        cell.width = Mm(95)

    dev_pos = params.get('developed_by_position', '') or 'Ведущий инженер технолог'
    chk_pos = params.get('checked_by_position', '') or 'Начальник лаборатории НК'
    dev_name = params.get('developed_by_name', '') or params.get('inspector_name', '')
    chk_name = params.get('checked_by_name', '')
    dev_cert = params.get('developed_by_certificate', '')
    chk_cert = params.get('checked_by_certificate', '')

    dev_line3 = dev_name
    if dev_cert:
        dev_line3 += f'\nУдостоверение № {dev_cert}'
    dev_line3 += f'\n«{dev_date}» ___________'
    chk_line3 = chk_name
    if chk_cert:
        chk_line3 += f'\nУдостоверение № {chk_cert}'
    chk_line3 += f'\n«{check_date}» ___________'

    fr0 = ft.rows[0]
    _set_cell_text(fr0.cells[0], 'Разработал', bold=True, font_size=9)
    _set_cell_text(fr0.cells[1], 'Проверил', bold=True, font_size=9)

    fr1 = ft.rows[1]
    _set_cell_text(fr1.cells[0], dev_pos, font_size=9)
    _set_cell_text(fr1.cells[1], chk_pos, font_size=9)

    fr2 = ft.rows[2]
    _set_cell_text(fr2.cells[0], dev_line3.strip(), font_size=9)
    _set_cell_text(fr2.cells[1], chk_line3.strip(), font_size=9)


def _insert_page_break_before_section10(doc: Document):
    """
    Вставляет разрыв страницы перед разделом «10. Оценка качества»,
    чтобы он всегда начинался с нового листа.

    Ищет таблицу, содержащую текст '10.' или '10.Оценка', и вставляет
    перед ней параграф с разрывом страницы.
    """
    body = doc.element.body

    for table in doc.tables:
        # Ищем таблицу с разделом 10
        table_text = ' '.join(
            cell.text for row in table.rows for cell in row.cells
        )
        if '10.' in table_text and (
            'Оценка' in table_text or 'оценк' in table_text.lower()
        ):
            tbl_el = table._tbl
            parent = tbl_el.getparent()
            if parent is None:
                continue

            # Создаём параграф с разрывом страницы
            ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            p_el = OxmlElement('w:p')
            r_el = OxmlElement('w:r')
            br_el = OxmlElement('w:br')
            br_el.set(qn('w:type'), 'page')
            r_el.append(br_el)
            p_el.append(r_el)

            # Вставляем параграф прямо перед таблицей
            idx = list(parent).index(tbl_el)
            parent.insert(idx, p_el)
            return   # Достаточно одного разрыва


def _compact_document(doc: Document):
    """
    Минимальная подготовка документа без перезаписи вёрстки шаблона:
    1. Удаляет заголовок-образец «Пример технологической карты...»
    2. Убирает пустые параграфы между таблицами (титульные отступы сохраняются)
    """
    body = doc.element.body
    ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    paras_to_remove = []
    for para in doc.paragraphs:
        text = para.text.strip()
        style_name = para.style.name if para.style else ''
        if (
            'Пример технологической карты' in text
            or 'Heading' in style_name
        ):
            paras_to_remove.append(para._element)

    title_para_idx = next(
        (
            i for i, p in enumerate(doc.paragraphs)
            if p.text.strip().startswith('Технологическая карта')
        ),
        None,
    )
    title_spacing_ids = set()
    if title_para_idx is not None:
        for p in doc.paragraphs[:title_para_idx]:
            title_spacing_ids.add(p._element)

    wp_ns = '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}'
    for para_el in body.findall(f'{ns}p'):
        if para_el in paras_to_remove:
            continue
        if para_el in title_spacing_ids:
            continue
        has_drawing = bool(
            para_el.findall(f'.//{wp_ns}inline')
            or para_el.findall(f'.//{wp_ns}anchor')
        )
        text = ''.join(
            t.text or '' for t in para_el.findall(f'.//{ns}t')
        ).strip()
        if not text and not has_drawing:
            paras_to_remove.append(para_el)

    for el in paras_to_remove:
        parent = el.getparent()
        if parent is not None:
            parent.remove(el)


def generate_radiographic_pdf(params: dict, output_path: str) -> str:
    """
    Создаёт PDF-версию технологической карты.
    Используется как дополнение к DOCX или если шаблон недоступен.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    register_cyrillic_fonts()

    doc_pdf = SimpleDocTemplate(
        output_path, pagesize=A4,
        rightMargin=15*mm, leftMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()
    title_s = ParagraphStyle('T', parent=styles['Title'], fontSize=13,
                              spaceAfter=4, alignment=TA_CENTER, fontName=FONT_BOLD)
    head_s = ParagraphStyle('H', parent=styles['Normal'], fontSize=10,
                             spaceAfter=3, spaceBefore=5,
                             backColor=colors.Color(0.84, 0.89, 0.94),
                             leftIndent=4, fontName=FONT_BOLD)
    norm_s = ParagraphStyle('N', parent=styles['Normal'], fontSize=9,
                             spaceAfter=2, fontName=FONT_REGULAR)
    label_s = ParagraphStyle('L', parent=styles['Normal'], fontSize=9,
                              textColor=colors.Color(0.2, 0.2, 0.6),
                              fontName=FONT_REGULAR)

    story = []
    card_num = params.get('card_number', '___')
    dev_date = params.get('develop_date', datetime.now().strftime('%d.%m.%Y'))

    story.append(Paragraph('ТЕХНОЛОГИЧЕСКАЯ КАРТА', title_s))
    story.append(Paragraph('РАДИОГРАФИЧЕСКОГО КОНТРОЛЯ', title_s))
    story.append(Paragraph(
        f'№ {card_num}     Дата: {dev_date}     '
        f'Методический документ: {DOCUMENT_CODE}', norm_s))
    story.append(Spacer(1, 5*mm))

    src = params.get('selected_source') or {}
    scheme = params.get('exposure_scheme') or {}
    iqi = params.get('recommended_iqi') or {}
    screens = params.get('screens') or {}
    film_info = params.get('film_class_info') or {}
    pers = params.get('personnel_requirements') or {}

    def section(title, rows):
        story.append(Paragraph(title, head_s))
        tdata = []
        for lbl, val in rows:
            tdata.append([
                Paragraph(f'<b>{lbl}</b>', label_s),
                Paragraph(str(val or '—'), norm_s),
            ])
        if tdata:
            t = Table(tdata, colWidths=[80*mm, 95*mm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.97, 1.0)),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t)
            story.append(Spacer(1, 3*mm))

    section('1–3. ОБЪЕКТ И ТРЕБОВАНИЯ', [
        ('1.1 Предприятие-изготовитель', params.get('organization')),
        ('1.2 Наименование детали (объекта)', params.get('object_name')),
        ('1.3 № чертежа', params.get('drawing_number')),
        ('1.4 Контролируемый элемент', params.get('weld_number')),
        ('1.6 Тип сварного соединения', _WELD_TYPE_NAMES.get(params.get('weld_type', ''), '')),
        ('1.8 Способ сварки', params.get('welding_process')),
        ('1.9 Основной металл', params.get('material_display') or params.get('material')),
        ('2.1 Методическая документация', DOCUMENT_CODE),
        ('2.2 Нормативная документация', NP105_CODE),
        ('3.1 Категория сварного соединения', params.get('weld_category')),
        ('3.2 Объём контроля', str(params.get('control_volume_pct', 100)) + ' %'),
    ])

    section('4. ТИП И РАЗМЕРЫ', [
        ('4.1 Тип контролируемого элемента', _OBJECT_TYPE_NAMES.get(params.get('object_type', ''), '')),
        ('4.2.1 Наружный диаметр, мм', params.get('outer_diameter') or '—'),
        ('Толщина стенки (S), мм', params.get('wall_thickness')),
        ('Требуемая чувствительность (К)', params.get('sensitivity_desc')),
    ])

    section('5. СРЕДСТВА КОНТРОЛЯ', [
        ('5.1 Источник излучения', src.get('name')),
        ('Энергия излучения', src.get('energy_display')),
        ('5.2 Размер фокусного пятна (d), мм', params.get('source_focal_spot_mm')),
        ('Активность / мощность', params.get('source_activity') or 'по паспорту источника'),
        ('5.3 Тип и номер ИКИ', (
            f"Проволочный эталон {params.get('iqi_marking', '')} — "
            f"{params.get('iqi_label', '')} "
            f"({(params.get('iqi_placement') or {}).get('side_label', '')})"
        )),
        ('Диаметр контрольной проволоки, мм', params.get('iqi_wire_diameter_mm')),
        ('5.4 Тип плёнки', params.get('film_name') or film_info.get('examples', '')),
        ('Класс плёнки (ГОСТ ИСО 11699-1)', film_info.get('class')),
        ('Мин. оптическая плотность', params.get('optical_density_min')),
        ('Передний экран, мм', screens.get('front_mm')),
        ('Задний экран, мм', screens.get('back_mm')),
    ])

    section('6. ПАРАМЕТРЫ И СХЕМА КОНТРОЛЯ', [
        ('6.1 Энергия / напряжение', src.get('energy_display')),
        ('6.2 Толщина для расчёта (Sк), мм', params.get('wall_thickness')),
        ('6.3 Требуемая чувствительность (К)', params.get('sensitivity_desc')),
        ('6.5 Расстояние источник–детектор (SFD), мм', params.get('sfd_mm')),
        ('Расстояние объект–детектор (OFD), мм', params.get('ofd_mm')),
        ('Геометрическая нерезкость (Ug), мм', params.get('ug_calculation')),
        ('Доп. нерезкость (Ug max), мм', params.get('max_geometric_unsharpness_mm')),
        ('6.6 Число экспозиций, шт.', scheme.get('n_exposures_min')),
        ('6.9 Схема просвечивания', scheme.get('name')),
    ])

    section('7–10. ПОДГОТОВКА, УСЛОВИЯ, ОЦЕНКА', [
        ('8.3 Состав рабочего звена', pers.get('level')),
        ('8.4 Диапазон рабочих температур, °С', '+5 ÷ +40'),
        ('9. Нормативный документ оценки качества (НП-105-18)', params.get('quality_normative')),
        ('10. Критерии качества', params.get('quality_criteria_summary')),
        ('Специалист НК', params.get('inspector_name') or '___________________'),
    ])

    # Предупреждения не включаются в готовую техкарту
    # (они остаются в логах системы)

    doc_pdf.build(story)
    return output_path


def generate_pdf_for_techcard(
    params: dict,
    pdf_abs: str,
    docx_abs: str | None = None,
    *,
    template_path: str | None = None,
    static_root: str = '',
) -> str:
    """
    Создаёт PDF техкарты: DOCX → HTML → PDF (mammoth + xhtml2pdf).

    При ошибке конвертации использует ReportLab как резервный путь.
    """
    docx_for_pdf = docx_abs
    temp_docx: str | None = None

    try:
        if not docx_for_pdf or not os.path.isfile(docx_for_pdf):
            fd, temp_docx = tempfile.mkstemp(suffix='.docx')
            os.close(fd)
            docx_for_pdf = temp_docx
            if template_path and os.path.exists(template_path):
                generate_from_template(
                    params, template_path, docx_for_pdf, static_root=static_root,
                )
            else:
                _generate_docx_fallback(params, docx_for_pdf)

        from common.docx_to_pdf import convert_docx_to_pdf
        convert_docx_to_pdf(docx_for_pdf, pdf_abs)
        logger.info('PDF создан из DOCX: %s', pdf_abs)
        return pdf_abs
    except Exception as exc:
        logger.warning(
            'DOCX→PDF не удался (%s), используем ReportLab fallback', exc,
        )
        return generate_radiographic_pdf(params, pdf_abs)
    finally:
        if temp_docx and os.path.isfile(temp_docx):
            os.remove(temp_docx)


# ---------------------------------------------------------------
# Главная функция генерации
# ---------------------------------------------------------------

def generate_tech_card(input_data: dict, media_root: str,
                       template_path: str = None) -> dict:
    """
    Главная функция генерации технологической карты.

    1. Рассчитывает параметры.
    2. Если шаблон доступен — заполняет его данными (DOCX).
    3. Если шаблона нет — создаёт DOCX программно (fallback).
    4. В обоих случаях создаёт PDF из DOCX (mammoth + xhtml2pdf, fallback ReportLab).

    :param input_data: данные из формы пользователя
    :param media_root: путь к медиа-директории Django
    :param template_path: путь к шаблону DOCX (опционально)
    :return: словарь {'params', 'docx_path', 'pdf_path', 'errors', 'warnings'}
    """
    calc = RadiographicTechCardCalculator(input_data)
    params = calc.calculate()
    params['errors'] = calc.errors
    params['warnings'] = calc.warnings

    uid = uuid.uuid4().hex[:10]
    card_num = (input_data.get('card_number', uid) or uid).replace('/', '-').replace(' ', '_')
    date_dir = datetime.now().strftime('%Y/%m')

    docx_rel = f'techcards/docx/{date_dir}/TC_{card_num}_{uid}.docx'
    pdf_rel = f'techcards/pdf/{date_dir}/TC_{card_num}_{uid}.pdf'
    docx_abs = os.path.join(media_root, docx_rel)
    pdf_abs = os.path.join(media_root, pdf_rel)

    os.makedirs(os.path.dirname(docx_abs), exist_ok=True)
    os.makedirs(os.path.dirname(pdf_abs), exist_ok=True)

    # DOCX: используем шаблон если он есть
    from django.conf import settings as django_settings
    static_root = str(getattr(django_settings, 'STATICFILES_DIRS', [''])[0]) if getattr(django_settings, 'STATICFILES_DIRS', []) else ''

    if template_path and os.path.exists(template_path):
        generate_from_template(params, template_path, docx_abs, static_root=static_root)
    else:
        _generate_docx_fallback(params, docx_abs)

    # PDF из DOCX (mammoth + xhtml2pdf), при ошибке — ReportLab
    generate_pdf_for_techcard(
        params, pdf_abs, docx_abs,
        template_path=template_path, static_root=static_root,
    )

    return {
        'params': params,
        'docx_path': docx_rel,
        'pdf_path': pdf_rel,
        'errors': calc.errors,
        'warnings': calc.warnings,
    }


def get_default_template_path() -> str | None:
    """Путь к шаблону DOCX техкарты (эталон — normative_docs/)."""
    from django.conf import settings as django_settings
    candidates = [
        os.path.join(
            django_settings.BASE_DIR, 'normative_docs',
            'Пример_технологической_карты_радиографического_контроля  с комментариями.docx',
        ),
        os.path.join(
            django_settings.BASE_DIR, 'card_templates',
            'Пример технологической карты радиографического контроля.docx',
        ),
    ]
    for template_path in candidates:
        if os.path.exists(template_path):
            return template_path
    return None


def regenerate_techcard_files(
    techcard,
    media_root: str,
    template_path: str | None = None,
    *,
    docx: bool = True,
    pdf: bool = True,
) -> None:
    """
    Восстанавливает файлы техкарты из JSON в БД.

    На Render и других PaaS локальный media/ очищается при деплое — файлы
    нужно пересоздавать по запросу скачивания.
    """
    params = techcard.generated_data
    if not params:
        raise ValueError('Нет сохранённых параметров техкарты для восстановления файла.')

    if template_path is None:
        template_path = get_default_template_path()

    from django.conf import settings as django_settings
    static_root = ''
    if getattr(django_settings, 'STATICFILES_DIRS', []):
        static_root = str(django_settings.STATICFILES_DIRS[0])

    if docx:
        docx_rel = str(techcard.docx_file) if techcard.docx_file else ''
        if not docx_rel:
            uid = uuid.uuid4().hex[:10]
            card_num = (techcard.card_number or str(techcard.pk)).replace('/', '-').replace(' ', '_')
            date_dir = (
                techcard.created_at.strftime('%Y/%m')
                if getattr(techcard, 'created_at', None) else datetime.now().strftime('%Y/%m')
            )
            docx_rel = f'techcards/docx/{date_dir}/TC_{card_num}_{uid}.docx'
            techcard.docx_file = docx_rel
        docx_abs = os.path.join(media_root, docx_rel)
        os.makedirs(os.path.dirname(docx_abs), exist_ok=True)
        if template_path and os.path.exists(template_path):
            generate_from_template(params, template_path, docx_abs, static_root=static_root)
        else:
            _generate_docx_fallback(params, docx_abs)

    if pdf:
        pdf_rel = str(techcard.pdf_file) if techcard.pdf_file else ''
        if not pdf_rel:
            uid = uuid.uuid4().hex[:10]
            card_num = (techcard.card_number or str(techcard.pk)).replace('/', '-').replace(' ', '_')
            date_dir = (
                techcard.created_at.strftime('%Y/%m')
                if getattr(techcard, 'created_at', None) else datetime.now().strftime('%Y/%m')
            )
            pdf_rel = f'techcards/pdf/{date_dir}/TC_{card_num}_{uid}.pdf'
            techcard.pdf_file = pdf_rel
        pdf_abs = os.path.join(media_root, pdf_rel)
        os.makedirs(os.path.dirname(pdf_abs), exist_ok=True)
        docx_abs_for_pdf = None
        if docx:
            docx_abs_for_pdf = os.path.join(media_root, str(techcard.docx_file))
        elif techcard.docx_file:
            candidate = os.path.join(media_root, str(techcard.docx_file))
            if os.path.isfile(candidate):
                docx_abs_for_pdf = candidate
        generate_pdf_for_techcard(
            params, pdf_abs, docx_abs_for_pdf,
            template_path=template_path, static_root=static_root,
        )

    update_fields = []
    if docx and techcard.docx_file:
        update_fields.append('docx_file')
    if pdf and techcard.pdf_file:
        update_fields.append('pdf_file')
    if update_fields:
        techcard.save(update_fields=update_fields)


def _generate_docx_fallback(params: dict, output_path: str) -> str:
    """
    Резервная генерация DOCX без шаблона.
    Создаёт простой документ с двумя колонками (метка / значение).
    """
    doc = Document()
    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.left_margin = Mm(20)
    section.right_margin = Mm(15)
    section.top_margin = Mm(20)
    section.bottom_margin = Mm(20)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run('ТЕХНОЛОГИЧЕСКАЯ КАРТА РАДИОГРАФИЧЕСКОГО КОНТРОЛЯ')
    r.bold = True
    r.font.size = Pt(13)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.add_run(
        f'№ {params.get("card_number","___")}     '
        f'Дата: {params.get("develop_date","")}     '
        f'Документ: {DOCUMENT_CODE}'
    ).font.size = Pt(9)

    doc.add_paragraph()
    table = doc.add_table(rows=0, cols=2)
    table.style = 'Table Grid'

    vmap = _build_value_map(params)
    label_names = {
        '1.1': '1.1 Предприятие-изготовитель',
        '1.2': '1.2 Наименование объекта',
        '1.3': '1.3 № чертежа',
        '1.4': '1.4 Контролируемый элемент',
        '1.6': '1.6 Тип сварного соединения',
        '1.8': '1.8 Способ сварки',
        '1.9': '1.9 Основной металл',
        '2.1': '2.1 Методическая документация',
        '2.2': '2.2 Нормативная документация',
        '3.1': '3.1 Категория сварного соединения',
        '3.2': '3.2 Объём контроля',
        '4.1': '4.1 Тип контролируемого элемента',
        '4.2.1': '4.2.1 Наружный диаметр, мм',
        'толщина': 'Толщина стенки (S), мм',
        '5.1': '5.1 Источник излучения',
        '5.2': '5.2 Размер фокусного пятна, мм',
        '5.3': '5.3 Тип и номер ИКИ',
        '5.4': '5.4 Тип плёнки',
        '6.1': '6.1 Энергия / напряжение',
        '6.3': '6.3 Требуемая чувствительность (К)',
        '6.5': '6.5 Расстояние источник–детектор, мм',
        '6.6': '6.6 Число экспозиций, шт.',
        '6.9': '6.9 Схема просвечивания',
    }

    for key, label in label_names.items():
        row = table.add_row()
        row.cells[0].text = label
        row.cells[0].paragraphs[0].runs[0].bold = True
        row.cells[0].paragraphs[0].runs[0].font.size = Pt(9)
        row.cells[1].text = str(vmap.get(key, ''))
        row.cells[1].paragraphs[0].runs[0].font.size = Pt(9)

    # Настраиваем колонтитулы (fallback без шаблона)
    _build_headers_footers_scratch(doc, params)

    doc.save(output_path)
    return output_path
