"""
Генератор технологических карт радиографического контроля.

Реализует логику автоматического расчёта параметров контроля
согласно ГОСТ Р 50.05.07-2018, НП-104-18 и ГОСТ Р 59023.2-2020.
Создаёт готовый документ в формате DOCX и конвертирует в PDF.
"""

import io
import os
import uuid
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Pt, Mm, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import reportlab
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from normative.gost_50_05_07 import (
    get_sensitivity, get_sensitivity_mm, get_suitable_sources,
    calc_geometric_unsharpness, calc_min_sfd, get_exposure_scheme,
    SCREEN_REQUIREMENTS, FILM_CLASSES, MAX_GEOMETRIC_UNSHARPNESS,
    OPTICAL_DENSITY, PERSONNEL_REQUIREMENTS, SAFETY_REQUIREMENTS,
    FILM_PROCESSING, IQI_TYPES, DOCUMENT_CODE, DOCUMENT_FULL_NAME,
)
from normative.np_104_18 import get_rt_sensitivity_class
from normative.np_105_18 import DOCUMENT_CODE as NP105_CODE


class RadiographicTechCardCalculator:
    """
    Вычислительное ядро генератора технологических карт радиографического
    контроля по ГОСТ Р 50.05.07-2018.

    Принимает исходные данные от пользователя и рассчитывает все необходимые
    параметры контроля. Результаты хранятся в словаре `params`.
    """

    def __init__(self, input_data: dict):
        """
        :param input_data: словарь с исходными данными из формы
        """
        self.data = input_data
        self.params = {}
        self.errors = []
        self.warnings = []

    def calculate(self) -> dict:
        """
        Выполняет все расчёты и возвращает полный словарь параметров техкарты.
        """
        self._extract_inputs()
        self._calc_sensitivity_class()
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
        return self.params

    def _extract_inputs(self):
        """Извлекает и нормализует входные данные."""
        d = self.data
        self.params.update({
            # Идентификационные данные
            'organization': d.get('organization', ''),
            'object_name': d.get('object_name', ''),
            'drawing_number': d.get('drawing_number', ''),
            'weld_number': d.get('weld_number', ''),
            # Характеристики объекта
            'object_type': d.get('object_type', 'pipe'),
            'material': d.get('material', ''),
            'wall_thickness': float(d.get('wall_thickness', 10)),
            'outer_diameter': float(d.get('outer_diameter', 0) or 0),
            'weld_type': d.get('weld_type', 'butt'),
            'weld_category': d.get('weld_category', 'II'),
            # Параметры источника (выбор пользователя)
            'source_code': d.get('source_code', ''),
            'source_focal_spot_mm': float(d.get('focal_spot_mm', 2.0) or 2.0),
            'source_activity': d.get('source_activity', ''),
            # Геометрия просвечивания (пользователь может ввести или рассчитывается)
            'sfd_mm': float(d.get('sfd_mm', 700) or 700),
            'ofd_mm': float(d.get('ofd_mm', 5) or 5),
            # Плёнка
            'film_name': d.get('film_name', ''),
            # Дополнительно
            'inspector_name': d.get('inspector_name', ''),
            'card_number': d.get('card_number', ''),
            'develop_date': d.get('develop_date', datetime.now().strftime('%d.%m.%Y')),
        })

    def _calc_sensitivity_class(self):
        """Определяет класс чувствительности по категории сварного шва (НП-104-18)."""
        weld_cat = self.params['weld_category']
        cls = get_rt_sensitivity_class(weld_cat)
        self.params['control_class'] = cls
        self.params['control_class_name'] = {
            'A': 'Класс А (высокий)',
            'B': 'Класс В (стандартный)',
            'C': 'Класс С (основной)',
        }.get(cls, cls)

    def _calc_sensitivity_value(self):
        """Рассчитывает требуемое значение чувствительности."""
        S = self.params['wall_thickness']
        cls = self.params['control_class']
        pct = get_sensitivity(S, cls)
        mm_val = get_sensitivity_mm(S, cls)
        self.params['required_sensitivity_pct'] = pct
        self.params['required_sensitivity_mm'] = mm_val
        self.params['sensitivity_desc'] = (
            f'{pct}% от толщины ({mm_val:.3f} мм) — по ГОСТ Р 50.05.07-2018, Таблица А.1'
        )

    def _select_sources(self):
        """Подбирает подходящие источники излучения для заданной толщины."""
        S = self.params['wall_thickness']
        suitable = get_suitable_sources(S)
        self.params['suitable_sources'] = suitable

        # Если пользователь выбрал источник — проверяем
        chosen_code = self.params['source_code']
        if chosen_code:
            match = next((s for s in suitable if s['code'] == chosen_code), None)
            if match:
                self.params['selected_source'] = match
                if not match['is_optimal']:
                    self.warnings.append(
                        f'Источник {match["name"]} применим, но не оптимален '
                        f'для толщины {S} мм. Оптимальный диапазон: '
                        f'{match["optimal_min"]}–{match["optimal_max"]} мм.'
                    )
            else:
                self.warnings.append(
                    f'Выбранный источник ({chosen_code}) не рекомендован для '
                    f'толщины {S} мм. Проверьте выбор.'
                )
                # Берём первый подходящий как рекомендацию
                self.params['selected_source'] = suitable[0] if suitable else {}
        else:
            # Берём оптимальный или первый подходящий
            optimal = [s for s in suitable if s.get('is_optimal')]
            self.params['selected_source'] = optimal[0] if optimal else (suitable[0] if suitable else {})

    def _calc_geometric_params(self):
        """Рассчитывает геометрические параметры и нерезкость."""
        d = self.params['source_focal_spot_mm']
        sfd = self.params['sfd_mm']
        ofd = self.params['ofd_mm']
        cls = self.params['control_class']

        try:
            ug = calc_geometric_unsharpness(d, sfd, ofd)
        except ValueError as e:
            ug = 0
            self.errors.append(str(e))

        max_ug = MAX_GEOMETRIC_UNSHARPNESS[cls]
        ug_ok = ug <= max_ug

        if not ug_ok:
            # Рассчитываем минимальное SFD
            min_sfd = calc_min_sfd(d, ofd, cls)
            self.warnings.append(
                f'Геометрическая нерезкость Ug={ug:.3f} мм превышает допустимую '
                f'{max_ug} мм для класса {cls}. '
                f'Рекомендуется увеличить SFD до ≥ {min_sfd:.0f} мм.'
            )
            self.params['min_sfd_recommended'] = min_sfd
        else:
            self.params['min_sfd_recommended'] = sfd

        self.params['geometric_unsharpness_mm'] = round(ug, 3)
        self.params['max_geometric_unsharpness_mm'] = max_ug
        self.params['geometric_unsharpness_ok'] = ug_ok
        self.params['ug_calculation'] = (
            f'Ug = d × b / (f - b) = {d} × {ofd} / ({sfd} - {ofd}) = {ug:.3f} мм'
            f' (допуск: ≤ {max_ug} мм)'
        )

    def _calc_exposure_scheme(self):
        """Определяет схему просвечивания."""
        joint_type = self.params['object_type']
        d_outer = self.params['outer_diameter']
        wall_t = self.params['wall_thickness']
        scheme = get_exposure_scheme(joint_type, d_outer, wall_t)
        self.params['exposure_scheme'] = scheme

    def _select_film(self):
        """Выбирает класс плёнки по классу контроля."""
        cls = self.params['control_class']
        recommended_films = [f for f in FILM_CLASSES if cls in f['allowed_for']]
        self.params['recommended_film_classes'] = recommended_films
        self.params['film_class_info'] = recommended_films[0] if recommended_films else {}

        # Оптическая плотность
        od = OPTICAL_DENSITY[cls]
        self.params['optical_density_min'] = od['min']
        self.params['optical_density_max'] = od['max']

    def _calc_screens(self):
        """Подбирает параметры усиливающих экранов."""
        source_code = (self.params.get('selected_source') or {}).get('code', '')
        screens = SCREEN_REQUIREMENTS.get(source_code, {
            'front_mm': '0,10', 'back_mm': '0,20', 'material': 'Свинцовые (Pb)', 'note': '',
        })
        self.params['screens'] = screens

    def _calc_iqi(self):
        """Подбирает тип эталона чувствительности."""
        cls = self.params['control_class']
        # Для класса А — предпочтительно проволочные или дуплекс
        preferred = [iqi for iqi in IQI_TYPES if cls in iqi['preferred_for']]
        self.params['recommended_iqi'] = preferred[0] if preferred else IQI_TYPES[0]

        # Расчёт номинального размера проволоки / канавки для проволочного эталона
        mm_val = self.params.get('required_sensitivity_mm', 0)
        # Ближайший стандартный диаметр проволоки (ГОСТ 7512, Приложение)
        wire_diameters = [0.063, 0.080, 0.10, 0.125, 0.160, 0.20, 0.25, 0.32, 0.40,
                          0.50, 0.63, 0.80, 1.00, 1.25, 1.60, 2.00, 2.50, 3.20]
        wire = next((w for w in wire_diameters if w >= mm_val), wire_diameters[-1])
        self.params['iqi_wire_diameter_mm'] = wire

    def _fill_processing(self):
        """Заполняет условия химической обработки плёнки."""
        self.params['film_processing'] = FILM_PROCESSING

    def _fill_personnel(self):
        """Заполняет требования к персоналу."""
        cls = self.params['control_class']
        self.params['personnel_requirements'] = PERSONNEL_REQUIREMENTS.get(cls, PERSONNEL_REQUIREMENTS['C'])

    def _fill_safety(self):
        """Заполняет требования по технике безопасности."""
        self.params['safety_requirements'] = SAFETY_REQUIREMENTS

    def _fill_acceptance_criteria(self):
        """Заполняет критерии оценки качества (ссылка на НП-105-18)."""
        weld_cat = self.params['weld_category']
        self.params['quality_normative'] = NP105_CODE
        self.params['quality_criteria_summary'] = (
            f'Оценка качества — по {NP105_CODE} для категории {weld_cat}. '
            f'Трещины, несплавления и непровары не допускаются. '
            f'Поры и шлаковые включения — по Таблице 1 {NP105_CODE}.'
        )


# ------------------------------------------------------------------
# Генератор документа DOCX
# ------------------------------------------------------------------

def _set_cell_bg(cell, hex_color: str):
    """Устанавливает цвет фона ячейки таблицы."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:fill'), hex_color)
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:val'), 'clear')
    tcPr.append(shd)


def _add_header_row(table, text: str, col_span: int = 2):
    """Добавляет строку-заголовок раздела в таблицу."""
    row = table.add_row()
    cell = row.cells[0]
    cell.merge(row.cells[col_span - 1])
    cell.text = text
    run = cell.paragraphs[0].runs[0]
    run.bold = True
    run.font.size = Pt(10)
    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_cell_bg(cell, 'D6E4F0')
    return row


def _add_param_row(table, label: str, value: str):
    """Добавляет строку параметр/значение в таблицу."""
    row = table.add_row()
    label_cell = row.cells[0]
    value_cell = row.cells[1]
    label_cell.text = label
    value_cell.text = str(value)
    label_cell.paragraphs[0].runs[0].bold = True
    label_cell.paragraphs[0].runs[0].font.size = Pt(9)
    value_cell.paragraphs[0].runs[0].font.size = Pt(9)
    return row


def generate_radiographic_docx(params: dict, output_path: str) -> str:
    """
    Создаёт файл DOCX технологической карты радиографического контроля.

    :param params: словарь рассчитанных параметров
    :param output_path: путь для сохранения файла
    :return: путь к созданному файлу
    """
    doc = Document()

    # Настройка страницы (A4, поля 20мм)
    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.left_margin = Mm(20)
    section.right_margin = Mm(15)
    section.top_margin = Mm(20)
    section.bottom_margin = Mm(20)

    # ---- Заголовок -------------------------------------------------------
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title_para.add_run('ТЕХНОЛОГИЧЕСКАЯ КАРТА')
    run.bold = True
    run.font.size = Pt(14)

    subtitle_para = doc.add_paragraph()
    subtitle_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle_para.add_run('РАДИОГРАФИЧЕСКОГО КОНТРОЛЯ')
    run.bold = True
    run.font.size = Pt(12)

    # Номер карты и дата
    meta_para = doc.add_paragraph()
    meta_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    card_num = params.get('card_number', '____')
    dev_date = params.get('develop_date', datetime.now().strftime('%d.%m.%Y'))
    meta_para.add_run(f'№ {card_num}    Дата: {dev_date}').font.size = Pt(10)

    # Нормативный документ
    norm_para = doc.add_paragraph()
    norm_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    norm_run = norm_para.add_run(f'Нормативный документ: {DOCUMENT_CODE}')
    norm_run.font.size = Pt(9)
    norm_run.italic = True

    doc.add_paragraph()  # пустая строка

    # ---- Основная таблица параметров ------------------------------------
    table = doc.add_table(rows=0, cols=2)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Ширина столбцов
    for i, width in enumerate([Mm(80), Mm(95)]):
        for cell in table.columns[i].cells:
            cell.width = width

    # Раздел 1: Объект контроля
    _add_header_row(table, '1. ОБЪЕКТ КОНТРОЛЯ', 2)
    _add_param_row(table, 'Организация', params.get('organization', ''))
    _add_param_row(table, 'Наименование объекта', params.get('object_name', ''))
    _add_param_row(table, 'Номер чертежа', params.get('drawing_number', ''))
    _add_param_row(table, 'Номер сварного соединения', params.get('weld_number', ''))
    _add_param_row(table, 'Материал', params.get('material', ''))

    object_type_names = {
        'pipe': 'Трубопровод (кольцевой шов)',
        'flat': 'Плоская деталь / лист',
        'vessel': 'Сосуд давления',
    }
    _add_param_row(table, 'Тип объекта', object_type_names.get(params.get('object_type', ''), ''))

    wall_t = params.get('wall_thickness', '')
    diam = params.get('outer_diameter', 0)
    _add_param_row(table, 'Толщина стенки, мм', str(wall_t))
    if diam:
        _add_param_row(table, 'Наружный диаметр, мм', str(diam))

    weld_type_names = {
        'butt': 'Стыковое (С)',
        'corner': 'Угловое (У)',
        'tee': 'Тавровое (Т)',
    }
    _add_param_row(table, 'Тип сварного соединения', weld_type_names.get(params.get('weld_type', ''), ''))
    _add_param_row(table, 'Категория сварного соединения', params.get('weld_category', ''))

    # Раздел 2: Параметры контроля
    _add_header_row(table, '2. ПАРАМЕТРЫ РАДИОГРАФИЧЕСКОГО КОНТРОЛЯ', 2)
    _add_param_row(table, 'Класс контроля', params.get('control_class_name', ''))
    _add_param_row(table, 'Требуемая чувствительность', params.get('sensitivity_desc', ''))

    src = params.get('selected_source', {})
    _add_param_row(table, 'Источник излучения', src.get('name', ''))
    _add_param_row(table, 'Энергия излучения', src.get('energy_display', ''))
    _add_param_row(table, 'Размер фокусного пятна (d), мм', str(params.get('source_focal_spot_mm', '')))
    _add_param_row(table, 'Активность / мощность дозы', params.get('source_activity', 'Определяется по паспорту источника'))

    # Раздел 3: Геометрия просвечивания
    _add_header_row(table, '3. ГЕОМЕТРИЯ ПРОСВЕЧИВАНИЯ', 2)

    scheme = params.get('exposure_scheme', {})
    _add_param_row(table, 'Схема просвечивания', scheme.get('name', ''))
    _add_param_row(table, 'Описание схемы', scheme.get('description', ''))
    _add_param_row(table, 'Количество экспозиций (min)', str(scheme.get('n_exposures_min', '')))
    _add_param_row(table, 'Расстояние источник–детектор (SFD, f), мм', str(params.get('sfd_mm', '')))
    _add_param_row(table, 'Расстояние объект–детектор (OFD, b), мм', str(params.get('ofd_mm', '')))
    _add_param_row(table, 'Геометрическая нерезкость (Ug), мм', params.get('ug_calculation', ''))
    max_ug = params.get('max_geometric_unsharpness_mm', '')
    ug_ok = params.get('geometric_unsharpness_ok', True)
    ug_status = '✓ в норме' if ug_ok else '✗ ПРЕВЫШЕНО'
    _add_param_row(table, f'Допустимая нерезкость (Ug max), мм', f'{max_ug} мм — {ug_status}')

    # Раздел 4: Детектор
    _add_header_row(table, '4. РАДИОГРАФИЧЕСКИЙ ДЕТЕКТОР', 2)
    film_info = params.get('film_class_info', {})
    _add_param_row(table, 'Тип плёнки (наименование)', params.get('film_name', film_info.get('examples', '')))
    _add_param_row(table, 'Класс плёнки (ГОСТ ИСО 11699-1)', film_info.get('class', ''))
    _add_param_row(table, 'Описание плёнки', film_info.get('description', ''))
    _add_param_row(table, 'Минимальная оптическая плотность', str(params.get('optical_density_min', '')))
    _add_param_row(table, 'Максимальная оптическая плотность', str(params.get('optical_density_max', 4.5)))

    screens = params.get('screens', {})
    _add_param_row(table, 'Усиливающие экраны (материал)', screens.get('material', 'Свинцовые (Pb)'))
    _add_param_row(table, 'Передний экран, мм', screens.get('front_mm', '0,10'))
    _add_param_row(table, 'Задний экран, мм', screens.get('back_mm', '0,20'))
    if screens.get('note'):
        _add_param_row(table, 'Примечание по экранам', screens['note'])

    # Раздел 5: Эталон чувствительности
    _add_header_row(table, '5. ЭТАЛОН ЧУВСТВИТЕЛЬНОСТИ', 2)
    iqi = params.get('recommended_iqi', {})
    _add_param_row(table, 'Тип эталона', iqi.get('name', ''))
    _add_param_row(table, 'Стандарт на эталон', iqi.get('standard', ''))
    if iqi.get('code') == 'wire':
        _add_param_row(table, 'Диаметр контрольной проволоки, мм', str(params.get('iqi_wire_diameter_mm', '')))

    # Раздел 6: Обработка плёнки
    _add_header_row(table, '6. УСЛОВИЯ ОБРАБОТКИ ПЛЁНКИ', 2)
    fp = params.get('film_processing', {})
    dev = fp.get('developer', {})
    if dev.get('options'):
        d_opt = dev['options'][0]
        _add_param_row(table, 'Проявитель', d_opt.get('name', ''))
        _add_param_row(table, 'Время проявления, мин', d_opt.get('time_min', ''))
        _add_param_row(table, 'Температура проявления, °C', d_opt.get('temp_c', '20±1'))
    fix = fp.get('fixer', {})
    if fix.get('options'):
        f_opt = fix['options'][0]
        _add_param_row(table, 'Закрепитель', f_opt.get('name', ''))
        _add_param_row(table, 'Время фиксирования, мин', f_opt.get('time_min', ''))
    washing = fp.get('washing', {})
    _add_param_row(table, 'Промывка, мин', washing.get('time_min', '20–30'))
    drying = fp.get('drying', {})
    _add_param_row(table, 'Сушка, °C', drying.get('temp_c', '25–40'))

    # Раздел 7: Оценка качества
    _add_header_row(table, '7. ОЦЕНКА РЕЗУЛЬТАТОВ КОНТРОЛЯ', 2)
    _add_param_row(table, 'Нормативный документ по оценке качества', params.get('quality_normative', NP105_CODE))
    _add_param_row(table, 'Критерии приёмки', params.get('quality_criteria_summary', ''))

    # Раздел 8: Требования к персоналу
    _add_header_row(table, '8. ТРЕБОВАНИЯ К ПЕРСОНАЛУ', 2)
    pers = params.get('personnel_requirements', {})
    _add_param_row(table, 'Квалификация специалиста НК', pers.get('level', ''))
    _add_param_row(table, 'Нормативный документ по квалификации', pers.get('standard', ''))
    if pers.get('additional'):
        _add_param_row(table, 'Примечание', pers['additional'])
    if params.get('inspector_name'):
        _add_param_row(table, 'Специалист НК (ФИО)', params['inspector_name'])

    # Раздел 9: Безопасность
    _add_header_row(table, '9. ТРЕБОВАНИЯ ПО БЕЗОПАСНОСТИ', 2)
    safety_list = params.get('safety_requirements', [])
    for i, req in enumerate(safety_list[:5], 1):  # Первые 5 требований
        _add_param_row(table, f'{i}.', req)

    # ---- Предупреждения --------------------------------------------------
    if params.get('warnings') or params.get('errors'):
        doc.add_paragraph()
        warn_para = doc.add_paragraph()
        if params.get('errors'):
            warn_run = warn_para.add_run('⚠ ОШИБКИ РАСЧЁТА: ' + '; '.join(params['errors']))
            warn_run.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
        if params.get('warnings'):
            for w in params['warnings']:
                p = doc.add_paragraph()
                r = p.add_run(f'⚠ {w}')
                r.font.color.rgb = RGBColor(0xFF, 0x80, 0x00)
                r.font.size = Pt(9)

    # ---- Подписи ---------------------------------------------------------
    doc.add_paragraph()
    sign_table = doc.add_table(rows=3, cols=3)
    sign_table.style = 'Table Grid'

    headers = ['Разработал', 'Проверил', 'Утвердил']
    for i, h in enumerate(headers):
        cell = sign_table.rows[0].cells[i]
        cell.text = h
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(9)

    for row in sign_table.rows[1:]:
        for cell in row.cells:
            cell.text = ''

    # Пустые строки для подписи
    for cell in sign_table.rows[2].cells:
        para = cell.paragraphs[0]
        para.add_run('___________________ / ___________________')
        para.runs[0].font.size = Pt(8)

    # Нижний колонтитул
    doc.add_paragraph()
    footer_para = doc.add_paragraph()
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_run = footer_para.add_run(
        f'Разработано с помощью ПО «НК-Карта» | '
        f'ГОСТ Р 50.05.07-2018 | Дата: {dev_date}'
    )
    footer_run.font.size = Pt(8)
    footer_run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)

    # Сохранение
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    return output_path


def generate_radiographic_pdf(params: dict, output_path: str) -> str:
    """
    Создаёт файл PDF технологической карты радиографического контроля.

    :param params: словарь рассчитанных параметров
    :param output_path: путь для сохранения файла
    :return: путь к созданному файлу
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc_pdf = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    # Стили для PDF с поддержкой кириллицы через встроенный шрифт
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=14,
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=10,
        spaceAfter=4,
        spaceBefore=6,
        backColor=colors.Color(0.84, 0.89, 0.94),  # Светло-синий
        leftIndent=4,
    )
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=2,
    )
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.Color(0.2, 0.2, 0.6),
    )

    story = []

    # Заголовок
    story.append(Paragraph('ТЕХНОЛОГИЧЕСКАЯ КАРТА', title_style))
    story.append(Paragraph('РАДИОГРАФИЧЕСКОГО КОНТРОЛЯ', title_style))
    card_num = params.get('card_number', '____')
    dev_date = params.get('develop_date', datetime.now().strftime('%d.%m.%Y'))
    story.append(Paragraph(f'№ {card_num}    Дата: {dev_date}', normal_style))
    story.append(Paragraph(f'Нормативный документ: {DOCUMENT_CODE}', normal_style))
    story.append(Spacer(1, 8 * mm))

    # Функция для создания раздела с данными
    def add_section(title_text, rows):
        story.append(Paragraph(title_text, heading_style))
        table_data = []
        for label, value in rows:
            table_data.append([
                Paragraph(f'<b>{label}</b>', label_style),
                Paragraph(str(value or '—'), normal_style),
            ])
        if table_data:
            t = Table(table_data, colWidths=[80 * mm, 95 * mm])
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
            story.append(Spacer(1, 3 * mm))

    # Объект контроля
    object_type_names = {
        'pipe': 'Трубопровод (кольцевой шов)',
        'flat': 'Плоская деталь / лист',
        'vessel': 'Сосуд давления',
    }
    weld_type_names = {
        'butt': 'Стыковое (С)',
        'corner': 'Угловое (У)',
        'tee': 'Тавровое (Т)',
    }

    add_section('1. ОБЪЕКТ КОНТРОЛЯ', [
        ('Организация', params.get('organization')),
        ('Наименование объекта', params.get('object_name')),
        ('Номер чертежа', params.get('drawing_number')),
        ('Номер сварного соединения', params.get('weld_number')),
        ('Материал', params.get('material')),
        ('Тип объекта', object_type_names.get(params.get('object_type', ''), '')),
        ('Толщина стенки, мм', params.get('wall_thickness')),
        ('Наружный диаметр, мм', params.get('outer_diameter') or '—'),
        ('Тип сварного соединения', weld_type_names.get(params.get('weld_type', ''), '')),
        ('Категория сварного соединения', params.get('weld_category')),
    ])

    src = params.get('selected_source', {})
    add_section('2. ПАРАМЕТРЫ КОНТРОЛЯ', [
        ('Класс контроля', params.get('control_class_name')),
        ('Требуемая чувствительность', params.get('sensitivity_desc')),
        ('Источник излучения', src.get('name')),
        ('Энергия излучения', src.get('energy_display')),
        ('Размер фокусного пятна (d), мм', params.get('source_focal_spot_mm')),
        ('Активность / мощность', params.get('source_activity', 'По паспорту')),
    ])

    scheme = params.get('exposure_scheme', {})
    add_section('3. ГЕОМЕТРИЯ ПРОСВЕЧИВАНИЯ', [
        ('Схема просвечивания', scheme.get('name')),
        ('Количество экспозиций (min)', scheme.get('n_exposures_min')),
        ('SFD (расстояние источник–детектор), мм', params.get('sfd_mm')),
        ('OFD (расстояние объект–детектор), мм', params.get('ofd_mm')),
        ('Геометрическая нерезкость (Ug)', params.get('ug_calculation')),
        ('Допустимая нерезкость (Ug max), мм', params.get('max_geometric_unsharpness_mm')),
    ])

    film_info = params.get('film_class_info', {})
    screens = params.get('screens', {})
    add_section('4. ДЕТЕКТОР И ЭКРАНЫ', [
        ('Тип плёнки', params.get('film_name', film_info.get('examples', ''))),
        ('Класс плёнки (ГОСТ ИСО 11699-1)', film_info.get('class')),
        ('Мин. оптическая плотность', params.get('optical_density_min')),
        ('Макс. оптическая плотность', params.get('optical_density_max', 4.5)),
        ('Экраны — материал', screens.get('material')),
        ('Передний экран, мм', screens.get('front_mm')),
        ('Задний экран, мм', screens.get('back_mm')),
    ])

    iqi = params.get('recommended_iqi', {})
    add_section('5. ЭТАЛОН ЧУВСТВИТЕЛЬНОСТИ', [
        ('Тип эталона', iqi.get('name')),
        ('Стандарт', iqi.get('standard')),
        ('Диаметр контрольной проволоки, мм', params.get('iqi_wire_diameter_mm')),
    ])

    pers = params.get('personnel_requirements', {})
    add_section('6. ПЕРСОНАЛ И БЕЗОПАСНОСТЬ', [
        ('Квалификация специалиста НК', pers.get('level')),
        ('Стандарт на квалификацию', pers.get('standard')),
        ('Специалист НК (ФИО)', params.get('inspector_name', '___________________')),
        ('Нормативный документ по оценке', params.get('quality_normative')),
    ])

    # Сохранение
    doc_pdf.build(story)
    return output_path


def generate_tech_card(input_data: dict, media_root: str) -> dict:
    """
    Главная функция генерации технологической карты.

    Выполняет расчёты, создаёт файлы DOCX и PDF, возвращает словарь с результатами.

    :param input_data: данные из формы
    :param media_root: корневой путь медиа-директории
    :return: словарь {'params', 'docx_path', 'pdf_path', 'errors', 'warnings'}
    """
    calc = RadiographicTechCardCalculator(input_data)
    params = calc.calculate()
    params['errors'] = calc.errors
    params['warnings'] = calc.warnings

    # Генерируем уникальное имя файла
    uid = uuid.uuid4().hex[:10]
    card_num = input_data.get('card_number', uid).replace('/', '-').replace(' ', '_')

    docx_rel = f'techcards/docx/{datetime.now().strftime("%Y/%m")}/TC_{card_num}_{uid}.docx'
    pdf_rel = f'techcards/pdf/{datetime.now().strftime("%Y/%m")}/TC_{card_num}_{uid}.pdf'

    docx_abs = os.path.join(media_root, docx_rel)
    pdf_abs = os.path.join(media_root, pdf_rel)

    generate_radiographic_docx(params, docx_abs)
    generate_radiographic_pdf(params, pdf_abs)

    return {
        'params': params,
        'docx_path': docx_rel,
        'pdf_path': pdf_rel,
        'errors': calc.errors,
        'warnings': calc.warnings,
    }
