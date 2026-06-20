"""
Генератор технологических карт радиографического контроля.

Реализует два режима работы:
1. На основе шаблона (DOCX) — заполняет оригинальный бланк данными.
2. Программная генерация — создаёт документ с нуля если шаблон не найден.

Нормативная база: ГОСТ Р 50.05.07-2018, НП-104-18, НП-105-18.
"""

import io
import os
import uuid
import copy
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

from normative.gost_50_05_07 import (
    get_sensitivity, get_sensitivity_mm, get_suitable_sources,
    calc_geometric_unsharpness, calc_min_sfd,
    SCREEN_REQUIREMENTS, FILM_CLASSES, MAX_GEOMETRIC_UNSHARPNESS,
    OPTICAL_DENSITY, PERSONNEL_REQUIREMENTS, SAFETY_REQUIREMENTS,
    FILM_PROCESSING, IQI_TYPES, DOCUMENT_CODE, DOCUMENT_FULL_NAME,
)
from normative.np_104_18 import get_rt_sensitivity_class, WELD_CATEGORIES
from normative.np_105_18 import DOCUMENT_CODE as NP105_CODE
from normative.calculations import (
    calc_exposure_parameters, recommend_scheme,
    calc_geometric_unsharpness_full, SCHEME_INFO,
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


def _set_cell_text(cell, text: str, bold: bool = False, font_size: int = 9):
    """Устанавливает текст в ячейке таблицы, сохраняя стиль."""
    for para in cell.paragraphs:
        for run in para.runs:
            run.text = ''
    if not cell.paragraphs:
        cell.add_paragraph('')
    para = cell.paragraphs[0]
    # Очищаем параграф
    for run in para.runs:
        run.clear()
    para.clear()
    run = para.add_run(str(text) if text is not None else '')
    run.bold = bold
    run.font.size = Pt(font_size)


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
        self._calc_sensitivity_class()
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
        self.params.update({
            'organization': d.get('organization', ''),
            'object_name': d.get('object_name', ''),
            'drawing_number': d.get('drawing_number', ''),
            'weld_number': d.get('weld_number', ''),
            'card_number': d.get('card_number', ''),
            'object_type': d.get('object_type', 'pipe'),
            'material': d.get('material', ''),
            'wall_thickness': float(d.get('wall_thickness', 10)),
            'outer_diameter': float(d.get('outer_diameter', 0) or 0),
            # Условное обозначение (ГОСТ Р 59023.2-2020)
            'joint_designation': d.get('joint_designation', ''),
            'welding_process': d.get('welding_process', '30'),
            'weld_category': d.get('weld_category', 'II'),
            'source_code': d.get('source_code', ''),
            'source_focal_spot_mm': float(d.get('focal_spot_mm', 2.0) or 2.0),
            'source_activity': d.get('source_activity', ''),
            'sfd_mm': float(d.get('sfd_mm', 0) or 0),
            'ofd_mm': float(d.get('ofd_mm', 5) or 5),
            'film_name': d.get('film_name', ''),
            'inspector_name': d.get('inspector_name', ''),
            'develop_date': d.get('develop_date', datetime.now().strftime('%d.%m.%Y')),
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

        zone = get_inspection_zone(joint_code, S, method)
        joint_info = get_joint_info(joint_code)

        self.params['weld_bead_width_mm'] = zone.get('bead_width_mm', '')
        self.params['weld_bead_height_mm'] = zone.get('bead_height_mm', '')
        # g_min и g_max для расчёта радиационной толщины (используются в _calc_sensitivity_value)
        self.params['g_min_mm'] = zone.get('g_min_mm', 0.5)
        self.params['g_max_mm'] = zone.get('g_max_mm', 3.5)
        self.params['haz_width_mm'] = zone.get('haz_width_mm', 5.0)
        self.params['zone_width_mm'] = zone.get('zone_width_mm', '')
        self.params['film_width_min_mm'] = zone.get('film_width_min_mm', '')
        self.params['zone_note'] = zone.get('weld_note', '')
        self.params['joint_groove'] = joint_info.get('groove', '')
        self.params['joint_name'] = joint_info.get('name', joint_code)
        self.params['joint_sketch'] = joint_info.get('sketch', '')

    def _calc_sensitivity_class(self):
        weld_cat = self.params['weld_category']
        cls = get_rt_sensitivity_class(weld_cat)
        self.params['control_class'] = cls
        self.params['control_class_name'] = {
            'A': 'А (высокий)', 'B': 'В (стандартный)', 'C': 'С (основной)'
        }.get(cls, cls)

    def _calc_sensitivity_value(self):
        """
        Рассчитывает требуемое значение чувствительности K по НП-105-18.

        По НП-105-18, Таблица N 4.8, заголовок: «Номинальная толщина
        сваренных деталей в месте сварки, мм».

        «Номинальная толщина в месте сварки» — это толщина стенки
        ВМЕСТЕ с минимальным усилением шва:
            S_K = S_ном + g_min

        Для схем ЧЕРЕЗ ОБЕ СТЕНКИ K ищется по одной стенке (S + g_min),
        а не по двойной радиационной толщине (2S + 2g_min).

        Для расчёта расстояния f используется наибольшая толщина:
            S_рад(f) = S + g_max       (1 стенка)
            S_рад(f) = 2S + 2×g_max   (2 стенки)
        """
        from normative.calculations import calc_radiation_thickness

        S = self.params['wall_thickness']
        cls = self.params['control_class']
        scheme = self.data.get('scheme_type', '4_6')
        g_min = self.params.get('g_min_mm', 0.5)
        g_max = self.params.get('g_max_mm', 3.5)

        # Радиационные толщины
        rad = calc_radiation_thickness(S, g_min, g_max, scheme)
        self.params['rad_thickness'] = rad

        # K ищем по S + g_min — «номинальная толщина в месте сварки»
        # (одна стенка + минимальное усиление, независимо от числа стенок)
        s_k = round(S + g_min, 1)
        K = get_sensitivity(s_k, cls)
        mm_val = get_sensitivity_mm(s_k, cls)

        self.params['required_sensitivity_pct'] = K
        self.params['required_sensitivity_mm'] = mm_val
        self.params['s_k_mm'] = s_k            # S + g_min (для поиска K)
        self.params['s_rad_f_mm'] = rad['s_rad_f_mm']  # для расчёта f
        self.params['sensitivity_desc'] = (
            f'K ≤ {mm_val:.3f} мм '
            f'(НП-105-18, Табл. 4.8: Sном+g_min = {S}+{g_min} = {s_k} мм, '
            f'кат. {self.params.get("weld_category","")})'
        )

    def _select_sources(self):
        S = self.params['wall_thickness']
        suitable = get_suitable_sources(S)
        self.params['suitable_sources'] = suitable
        chosen_code = self.params['source_code']
        if chosen_code:
            match = next((s for s in suitable if s['code'] == chosen_code), None)
            if match:
                self.params['selected_source'] = match
                if not match['is_optimal']:
                    self.warnings.append(
                        f'Источник {match["name"]} применим, но не оптимален '
                        f'для толщины {S} мм.'
                    )
            else:
                self.warnings.append(f'Источник {chosen_code} не рекомендован для {S} мм.')
                self.params['selected_source'] = suitable[0] if suitable else {}
        else:
            optimal = [s for s in suitable if s.get('is_optimal')]
            self.params['selected_source'] = optimal[0] if optimal else (suitable[0] if suitable else {})

    def _calc_geometric_params(self):
        """
        Рассчитывает геометрическую нерезкость.
        Если f (SFD) не задан пользователем — использует f_min из расчёта схемы.
        """
        focal = self.params['source_focal_spot_mm']
        ofd = self.params['ofd_mm']
        cls = self.params['control_class']
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

        max_ug = MAX_GEOMETRIC_UNSHARPNESS.get(cls, 0.5)
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
        film_length = float(self.data.get('film_length_mm', 350) or 350)

        # Схема просвечивания — выбор пользователя или авторекомендация
        scheme = self.data.get('scheme_type', '').strip()
        if not scheme:
            recommended = recommend_scheme(D, d_inner)
            scheme = recommended[0] if recommended else '4_6'
            self.params['scheme_auto_selected'] = True

        # Точный расчёт параметров по выбранной схеме
        calc_result = calc_exposure_parameters(
            scheme=scheme,
            focal_spot_mm=focal,
            sensitivity_mm=sensitivity_mm if sensitivity_mm > 0 else 0.5,
            thickness_mm=S,          # для схемы 4.6
            d_outer_mm=D or 0,
            d_inner_mm=d_inner,
            film_length_mm=film_length,
        )

        if calc_result.get('error'):
            self.warnings.append(f'Схема {scheme}: {calc_result["error"]}')

        # Информация о схеме (описание, изображение)
        scheme_info = SCHEME_INFO.get(scheme, {})

        # Сохраняем рассчитанные параметры
        self.params['scheme_type'] = scheme
        self.params['exposure_scheme'] = calc_result
        self.params['scheme_info'] = scheme_info
        self.params['f_calculated_mm'] = calc_result.get('f_min_mm', '')
        self.params['N_calculated'] = calc_result.get('N', '')
        self.params['L_calculated_mm'] = calc_result.get('L_mm', '')
        self.params['scheme_formula'] = calc_result.get('formula', '')
        self.params['scheme_notes'] = calc_result.get('notes', '')
        self.params['scheme_image'] = scheme_info.get('image', '')
        self.params['C_coeff'] = calc_result.get('C', '')
        self.params['film_length_mm'] = film_length

    def _select_film(self):
        cls = self.params['control_class']
        recommended = [f for f in FILM_CLASSES if cls in f['allowed_for']]
        self.params['recommended_film_classes'] = recommended
        self.params['film_class_info'] = recommended[0] if recommended else {}
        od = OPTICAL_DENSITY[cls]
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
        cls = self.params['control_class']
        preferred = [iqi for iqi in IQI_TYPES if cls in iqi['preferred_for']]
        self.params['recommended_iqi'] = preferred[0] if preferred else IQI_TYPES[0]
        mm_val = self.params.get('required_sensitivity_mm', 0)
        wire_diameters = [
            0.063, 0.080, 0.10, 0.125, 0.160, 0.20, 0.25, 0.32,
            0.40, 0.50, 0.63, 0.80, 1.00, 1.25, 1.60, 2.00, 2.50, 3.20,
        ]
        wire = next((w for w in wire_diameters if w >= mm_val), wire_diameters[-1])
        self.params['iqi_wire_diameter_mm'] = wire

    def _fill_processing(self):
        self.params['film_processing'] = FILM_PROCESSING

    def _fill_personnel(self):
        cls = self.params['control_class']
        self.params['personnel_requirements'] = PERSONNEL_REQUIREMENTS.get(
            cls, PERSONNEL_REQUIREMENTS['C']
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
    'butt': 'Стыковое (С)', 'corner': 'Угловое (У)',
    'tee': 'Тавровое (Т)', 'lap': 'Нахлёсточное (Н)',
}

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

    # Формирование строк для полей техкарты
    f_str = f'{f_val} мм' if f_val else '— мм'
    N_str = str(N_val) if N_val else '—'
    L_str = f'{L_val} мм' if L_val else '—'

    # Поле 6.5: расстояние источника с обоснованием
    if f_val:
        f_field = (
            f'f = {f_val} мм '
            f'(расчёт: {params.get("scheme_formula", "")})'
        )
    else:
        f_field = f'{sfd_used} мм'

    # Поле 6.8: размер участка
    if L_val:
        l_field = (
            f'{L_val} мм = π × {D} / {N_val}'
            if D and N_val else f'{L_val} мм'
        )
    else:
        l_field = '350 × (длина шва / N) мм'

    # Поле 6.9: схема просвечивания
    scheme_name = scheme_info.get('name', params.get('scheme_type', ''))
    scheme_desc = scheme_info.get('description', '')
    scheme_notes = params.get('scheme_notes', '')
    scheme_formula = params.get('scheme_formula', '')
    scheme_field = '\n'.join(filter(None, [scheme_name, scheme_desc, scheme_formula, scheme_notes]))

    # Угол просвечивания (для поля 6.4)
    angle = '0° (перпендикуляр к поверхности контроля)'
    if params.get('scheme_type') in ('5a', '5b', '5v', '5g', '5d', '5zh', '5z'):
        angle = 'По схеме просвечивания (90° к оси шва)'

    # Коэффициент C для поля 5.2
    focal_field = str(params.get('source_focal_spot_mm', ''))
    if C_val:
        focal_field += f' мм (C = {C_val:.2f})'

    return {
        # ---- Раздел 1: Объект контроля ----
        '1.1': params.get('organization', ''),
        '1.2': params.get('object_name', ''),
        '1.3': params.get('drawing_number', ''),
        '1.4': params.get('weld_number', ''),
        '1.5': params.get('drawing_number', ''),
        '1.6': (
            f'{params.get("joint_designation", "")} — {params.get("joint_name", "")}'
            if params.get('joint_designation') else
            _WELD_TYPE_NAMES.get(params.get('weld_type', ''), '')
        ),
        '1.7': params.get('weld_number', ''),
        '1.8': (
            f'Способ {params.get("welding_process", "")} — '
            + {
                '10': 'АДФ под флюсом', '11': 'АДФ с подваркой корня', '20': 'ЭШС',
                '30': 'РДС', '31': 'РДС с подваркой корня', '32': 'РДС на подкладке',
                '40': 'Комбинированная (корень АДС)', '42': 'Комбинированная на подкладке',
                '51': 'АДС без присадки', '52': 'АДС с присадкой', '53': 'АДС плавящимся',
                '60': 'ЭЛС',
            }.get(params.get('welding_process', ''), '')
            if params.get('welding_process') else ''
        ),
        '1.9': params.get('material', ''),
        '1.10': params.get('weld_material', ''),

        # ---- Раздел 2: Документация ----
        '2.1': DOCUMENT_CODE,
        '2.2': NP105_CODE,

        # ---- Раздел 3: Требования ----
        '3.1': params.get('weld_category', ''),
        '3.2': str(params.get('control_volume_pct', 100)) + ' %',

        # ---- Раздел 4: Тип и размеры (поля 4.2.2, 4.2.4, 4.2.5 по ГОСТ Р 59023.2-2020) ----
        '4.1': _OBJECT_TYPE_NAMES.get(params.get('object_type', ''), ''),
        '4.2.1': f'Dн = {D} мм' if D else 'плоская деталь',
        'толщина': f'S = {S} мм',
        '4.2.2': (
            f'e = {params.get("weld_bead_width_mm", "—")} мм, '
            f'g = {params.get("weld_bead_height_mm", "—")} мм '
            f'({params.get("joint_designation", "—")}, S={S}мм, сп.{params.get("welding_process","—")})'
            if params.get('weld_bead_width_mm') else 'по замеру на объекте'
        ),
        '4.2.3': 'не снят',
        '4.2.4': f'{params.get("haz_width_mm", 5.0):.1f} мм (с каждой стороны от краёв шва)',
        '4.2.5': (
            f'{params.get("zone_width_mm", "—")} мм '
            f'= e({params.get("weld_bead_width_mm","—")})+2×{params.get("haz_width_mm",5.0):.1f}'
            if params.get('zone_width_mm') else 'ширина шва + 2×5 мм'
        ),

        # ---- Раздел 5: Средства контроля ----
        '5.1': src.get('name', ''),
        '5.2': focal_field,
        '5.3': (
            f"{iqi.get('name', '')} по {iqi.get('standard', '')} "
            f"/ Ø проволоки {params.get('iqi_wire_diameter_mm', '')} мм"
        ),
        '5.4': params.get('film_name', film_info.get('examples', '')),
        '5.5': 'в светонепроницаемую плёночную (гибкую) кассету',
        '5.6': 'свинцовые буквы и цифры по ГОСТ',
        '5.7': f'{params.get("film_length_mm", 350):.0f} × 100 мм',
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
            f'Sном+g_min = {S}+{params.get("g_min_mm",0.5)} = {params.get("s_k_mm", S+0.5):.1f} мм → '
            f'K ≤ {params.get("required_sensitivity_mm","—"):.3f} мм '
            f'(НП-105-18, Табл. 4.8, кат. {params.get("weld_category","")});  '
            f'Sрад(f) = {params.get("rad_thickness", {}).get("formula_f", "—")}'
        ),
        '6.3': params.get('sensitivity_desc', ''),
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
    value_map = _build_value_map(params)

    # --- Замена в таблицах ---
    for table in doc.tables:
        for row in table.rows:
            ucells = _unique_cells(row)
            if not ucells:
                continue

            label_text = ucells[0].text.strip()
            value_cell = ucells[-1] if len(ucells) >= 2 else None

            # Ищем совпадение по фрагменту метки
            matched_value = None
            for key, val in value_map.items():
                if key.lower() in label_text.lower() and label_text != '':
                    matched_value = val
                    break

            if matched_value is not None and value_cell is not None:
                # Не перезаписываем, если ячейка та же что и метка
                if value_cell._tc is not ucells[0]._tc:
                    _set_cell_text(value_cell, matched_value)

            # Отдельная обработка: шапка — замена «ОАО «ХХХХ»»
            if 'ОАО «ХХ' in label_text or label_text.startswith('ОАО') or label_text.startswith('ОД'):
                org = params.get('organization', '')
                if org:
                    _set_cell_text(ucells[0], org)

    # --- Замена номера карты в шапке ---
    card_num = params.get('card_number', '___')
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if '02/11-РГК' in para.text:
                        for run in para.runs:
                            run.text = run.text.replace('02/11-РГК', card_num)

    # --- Замена даты в подписях ---
    dev_date = params.get('develop_date', datetime.now().strftime('%d.%m.%Y'))
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if '2012г' in para.text or '_01___2012' in para.text:
                        for run in para.runs:
                            run.text = run.text.replace('_21_»_01___2012г.', f'«{dev_date}»')
                            run.text = run.text.replace('«_21_»_01___2012_г.', f'«{dev_date}»')

    # --- Добавление предупреждений в конец документа ---
    if params.get('warnings'):
        doc.add_paragraph()
        para = doc.add_paragraph()
        run = para.add_run('Предупреждения при генерации:')
        run.bold = True
        run.font.size = Pt(9)
        for w in params['warnings']:
            p = doc.add_paragraph(f'⚠ {w}', style='Normal')
            p.runs[0].font.size = Pt(8)
            p.runs[0].font.color.rgb = RGBColor(0xFF, 0x80, 0x00)

    # --- Вставка изображения схемы просвечивания в поле 6.9 ---
    _insert_scheme_image_into_docx(doc, params, static_root)

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
                        s_rad_k = params.get('s_rad_k_mm', '')
                        s_rad_f = params.get('s_rad_f_mm', '')
                        rad_run = rad_para.add_run(
                            f'{rad_note}. '
                            f'Sрад(К) = {s_rad_k} мм; Sрад(f) = {s_rad_f} мм'
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

def generate_radiographic_pdf(params: dict, output_path: str) -> str:
    """
    Создаёт PDF-версию технологической карты.
    Используется как дополнение к DOCX или если шаблон недоступен.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc_pdf = SimpleDocTemplate(
        output_path, pagesize=A4,
        rightMargin=15*mm, leftMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()
    title_s = ParagraphStyle('T', parent=styles['Title'], fontSize=13,
                              spaceAfter=4, alignment=TA_CENTER)
    head_s = ParagraphStyle('H', parent=styles['Normal'], fontSize=10,
                             spaceAfter=3, spaceBefore=5,
                             backColor=colors.Color(0.84, 0.89, 0.94),
                             leftIndent=4, fontName='Helvetica-Bold')
    norm_s = ParagraphStyle('N', parent=styles['Normal'], fontSize=9, spaceAfter=2)
    label_s = ParagraphStyle('L', parent=styles['Normal'], fontSize=9,
                              textColor=colors.Color(0.2, 0.2, 0.6))

    story = []
    card_num = params.get('card_number', '___')
    dev_date = params.get('develop_date', datetime.now().strftime('%d.%m.%Y'))

    story.append(Paragraph('ТЕХНОЛОГИЧЕСКАЯ КАРТА', title_s))
    story.append(Paragraph('РАДИОГРАФИЧЕСКОГО КОНТРОЛЯ', title_s))
    story.append(Paragraph(
        f'№ {card_num}     Дата: {dev_date}     '
        f'Нормативный документ: {DOCUMENT_CODE}', norm_s))
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
        ('1.9 Основной металл', params.get('material')),
        ('2.1 Методическая документация', DOCUMENT_CODE),
        ('2.2 Нормативная документация', NP105_CODE),
        ('3.1 Категория сварного соединения', params.get('weld_category')),
        ('3.2 Объём контроля', str(params.get('control_volume_pct', 100)) + ' %'),
    ])

    section('4. ТИП И РАЗМЕРЫ', [
        ('4.1 Тип контролируемого элемента', _OBJECT_TYPE_NAMES.get(params.get('object_type', ''), '')),
        ('4.2.1 Наружный диаметр, мм', params.get('outer_diameter') or '—'),
        ('Толщина стенки (S), мм', params.get('wall_thickness')),
        ('Класс контроля', params.get('control_class_name')),
        ('Требуемая чувствительность (К)', params.get('sensitivity_desc')),
    ])

    section('5. СРЕДСТВА КОНТРОЛЯ', [
        ('5.1 Источник излучения', src.get('name')),
        ('Энергия излучения', src.get('energy_display')),
        ('5.2 Размер фокусного пятна (d), мм', params.get('source_focal_spot_mm')),
        ('Активность / мощность', params.get('source_activity') or 'по паспорту источника'),
        ('5.3 Тип и номер ИКИ', iqi.get('name') + ' / ' + iqi.get('standard', '')),
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
        ('9. Нормативный документ оценки', params.get('quality_normative')),
        ('10. Критерии качества', params.get('quality_criteria_summary')),
        ('Специалист НК', params.get('inspector_name') or '___________________'),
    ])

    if params.get('warnings'):
        story.append(Paragraph('ПРЕДУПРЕЖДЕНИЯ:', head_s))
        for w in params['warnings']:
            story.append(Paragraph(f'⚠ {w}', norm_s))

    doc_pdf.build(story)
    return output_path


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
    4. В обоих случаях создаёт PDF.

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

    # PDF всегда создаём программно
    generate_radiographic_pdf(params, pdf_abs)

    return {
        'params': params,
        'docx_path': docx_rel,
        'pdf_path': pdf_rel,
        'errors': calc.errors,
        'warnings': calc.warnings,
    }


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

    doc.save(output_path)
    return output_path
