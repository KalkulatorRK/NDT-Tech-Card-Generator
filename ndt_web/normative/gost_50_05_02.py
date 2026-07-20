"""
Данные ГОСТ Р 50.05.02-2022 «Система оценки соответствия в области использования
атомной энергии. Оценка соответствия в форме контроля. Унифицированные методики.
Ультразвуковой контроль сварных соединений и наплавленных поверхностей».

Модуль содержит структурированные требования для ИИ-консультанта и справочных
вызовов (tools) по ультразвуковому контролю сварных соединений и наплавок (УЗК):
- область применения и типы объектов контроля (п. 5.1);
- параметры НП и прямых ПЭП (табл. 1–5);
- уровни чувствительности и коэффициенты пересчёта (п. 7.4.2, табл. 6–7);
- подготовка поверхности, контроледоступность, схемы сканирования;
- требования к персоналу, аппаратуре, учётной документации.

Источник: ГОСТ Р 50.05.02-2022 (введён в действие 01.01.2024, заменяет 50.05.02-2018).

ВАЖНО: при изменении стандарта актуализировать этот модуль по тексту НД.
Нормы оценки качества (браковочные уровни по эквивалентной площади и т.п.)
задаются НП-105-18, КД и ТД — см. np_105_18, не дублируются здесь.
"""

from __future__ import annotations

import math
from typing import Optional

# ------------------------------------------------------------------
# Идентификатор документа
# ------------------------------------------------------------------
DOCUMENT_CODE = 'ГОСТ Р 50.05.02-2022'
DOCUMENT_SHORT = 'ГОСТ Р 50.05.02'
DOCUMENT_FULL_NAME = (
    'ГОСТ Р 50.05.02-2022 «Система оценки соответствия в области использования '
    'атомной энергии. Оценка соответствия в форме контроля. Унифицированные '
    'методики. Ультразвуковой контроль сварных соединений и наплавленных '
    'поверхностей»'
)
DOCUMENT_EFFECTIVE_FROM = '2024-01-01'
DOCUMENT_REPLACES = 'ГОСТ Р 50.05.02-2018'
METHOD_CODE = 'УЗК'
METHOD_NAME = 'ультразвуковой контроль сварных соединений и наплавок'
METHOD_NAME_EN = 'Ultrasonic testing of welded joints and cladded surfaces'

# ------------------------------------------------------------------
# Область применения (раздел 1, п. 5.1)
# ------------------------------------------------------------------
SCOPE = (
    'Оценка соответствия сварных соединений, наплавленных поверхностей и зоны '
    'сплавления наплавленных поверхностей продукции АЭУ при изготовлении, '
    'монтаже и эксплуатации. Нормы оценки качества — [2], [4], [10], документы по '
    'стандартизации, КД и ТД.'
)

SCOPE_OBJECTS = {
    'butt_angle_tee_welds': {
        'description': (
            'Стыковые, угловые и тавровые СС деталей из сталей перлитного класса '
            'и высокохромистых сталей, дуговая и ЭШС с полным проплавлением'
        ),
        'thickness_mm': (5.5, 400.0),
        'clause': '5.1.1',
    },
    'cladding_perlit': {
        'description': (
            'Металл наплавленных поверхностей (в т.ч. переходных) перлитного класса '
            'и высокохромистые материалы на кромках из перлитного класса; зона '
            'сплавления с аустенитным наплавом на основе ≥10 мм'
        ),
        'cladding_thickness_mm': (4, 40),
        'base_metal_min_mm': 10,
        'clause': '5.1.1',
    },
    'anticorrosion_fusion_zone': {
        'description': (
            'Зона сплавления АНП из сталей аустенитного класса толщиной ≥4 мм '
            'на деталях из сталей перлитного класса'
        ),
        'cladding_thickness_mm_min': 4,
        'clause': '5.1.1',
    },
}

# Радиусы кривизны (п. 5.1.2), мм
CURVATURE_RADIUS_MIN_MM = {
    'longitudinal_weld_outer': 150.0,
    'cladding_surface': 100.0,
    'circumferential_weld': 12.5,
    'inner_angle_tee': 50.0,
}

# ------------------------------------------------------------------
# Нормативные ссылки (раздел 2)
# ------------------------------------------------------------------
NORMATIVE_REFERENCES = (
    'ГОСТ 2789',
    'ГОСТ 8433',
    'ГОСТ 23829',
    'ГОСТ Р 50.04.03-2018',
    'ГОСТ Р 50.04.07',
    'ГОСТ Р 50.05.05-2018',
    'ГОСТ Р 50.05.11',
    'ГОСТ Р 50.05.14',
    'ГОСТ Р 50.05.15',
    'ГОСТ Р 50.05.16',
    'ГОСТ Р 55724-2013',
    'ГОСТ Р 55725',
    'ГОСТ Р 58904/ISO/TR 25901-1:2016',
    'ГОСТ Р ИСО 5577',
)

PERSONNEL_STANDARD = 'ГОСТ Р 50.05.11'
EQUIPMENT_STANDARD = 'ГОСТ Р 50.05.14'
PEP_STANDARD = 'ГОСТ Р 55725'

# ------------------------------------------------------------------
# Термины (раздел 3) — ключевые для УЗК
# ------------------------------------------------------------------
TERMS = {
    '3.1': {
        'term': 'браковочный уровень чувствительности',
        'definition': (
            'Уровень чувствительности, при превышении которого выявленная '
            'несплошность относится к дефекту.'
        ),
        'source': '[[6], приложение N 2]',
    },
    '3.5': {
        'term': 'контрольный уровень чувствительности (уровень фиксации)',
        'definition': (
            'Уровень чувствительности, при котором производят регистрацию '
            'несплошностей и оценку их допустимости по условным размерам и количеству.'
        ),
        'source': '[[6], приложение N 2]',
    },
    '3.9': {
        'term': 'поисковый уровень чувствительности',
        'definition': 'Уровень чувствительности, устанавливаемый при поиске несплошностей.',
        'source': 'ГОСТ Р 55724-2013, п. 3.1.26',
    },
    '3.10': {
        'term': 'схема прозвучивания',
        'definition': (
            'Документально оформленный порядок сканирования ОК выбранным(и) ПЭП '
            'с целью полного прозвучивания металла шва/наплавки.'
        ),
    },
    '3.12': {
        'term': 'технологическая карта контроля',
        'definition': (
            'Производственная контрольная документация, регламентирующая средства, '
            'параметры, последовательность и содержание операций НК.'
        ),
    },
    '3.15': {
        'term': 'эквивалентная площадь несплошности',
        'definition': (
            'Площадь плоскодонного искусственного отражателя, при которой сигнал '
            'равен сигналу от несплошности на том же расстоянии.'
        ),
        'source': 'ГОСТ Р 50.05.05-2018, п. 3.18',
    },
}

ABBREVIATIONS = {
    'АРК': 'кривая амплитуда - расстояние',
    'АСД': 'автоматический сигнализатор дефекта',
    'ВРЧ': 'временная регулировка чувствительности',
    'ГЦТ': 'главный циркуляционный трубопровод',
    'КД': 'конструкторская документация',
    'КО': 'калибровочный образец',
    'НП': 'наклонный преобразователь',
    'НО': 'настроечный образец',
    'ОК': 'объект контроля',
    'ПГВ': 'преобразователь головных волн',
    'ПС': 'прямой совмещенный',
    'ПРС': 'прямой раздельно-совмещенный',
    'ПЭ': 'пьезоэлемент',
    'ПЭП': 'пьезоэлектрический преобразователь',
    'РС': 'раздельно-совмещенный',
    'СС': 'сварное соединение',
    'ТД': 'техническая документация',
    'ТИ': 'технологическая инструкция',
    'ТКК': 'технологическая карта контроля',
    'УЗ': 'ультразвук (ультразвуковой)',
    'УЗК': 'ультразвуковой контроль',
}

# ------------------------------------------------------------------
# Условия проведения УЗК (п. 5.2, 5.10)
# ------------------------------------------------------------------
AMBIENT_TEMP_MIN_C = 5
AMBIENT_TEMP_MAX_C = 40
ILLUMINANCE_MIN_LX = 500
VIBRATION_FORBIDDEN_DISTANCE_M = 10
BRIGHT_LIGHT_SCREEN_DISTANCE_M = 15
MANUAL_UZK_FORBIDDEN_HOURS = (0, 6)  # местное время, без авто-записи
TEAM_SIZE_MIN = 2
PEP_ANGLE_DEVIATION_MAX_DEG = 2.0
SETUP_VERIFY_INTERVAL_H = 2
SCAN_SPEED_MAX_MM_S = 150.0
SURFACE_GAP_MAX_MM = 0.2
PRS_GAP_MAX_MM = 0.2  # п. 6.2.4.4

# Уровни чувствительности относительно браковочного (п. 7.4.2.2)
SENSITIVITY_LEVEL_OFFSET_DB = {
    'reject': 0,
    'control': 6,
    'search': 12,
}
TRANSVERSE_SEARCH_OFFSET_DB = 6  # п. 6.5.3 — от контрольного

# ------------------------------------------------------------------
# Подготовка поверхности (п. 6.8.7–6.8.9)
# ------------------------------------------------------------------
SURFACE_ROUGHNESS_RA_MAX = 6.3
SURFACE_ROUGHNESS_RZ_MAX = 40.0
BOTTOM_ROUGHNESS_RA_MAX = 20.0
BOTTOM_ROUGHNESS_RZ_MAX = 80.0
SURFACE_ROUGHNESS_STANDARD = 'ГОСТ 2789'

# ------------------------------------------------------------------
# Таблица 1 — параметры НП для стыковых СС (п. 6.2.1.3)
# ------------------------------------------------------------------
TABLE_1_NP_BUTT_WELDS = [
    {
        'thickness_mm': (5.5, 9.0),
        'frequency_mhz': (4.0, 6.0),
        'angle_direct_deg': (70, 72),
        'angle_reflected_deg': (65, 70),
        'reflected_allowed': True,
        'table': '1',
        'clause': '6.2.1.3',
    },
    {
        'thickness_mm': (9.0, 12.0),
        'frequency_mhz': (4.0, 6.0),
        'angle_direct_deg': (65, 70),
        'angle_reflected_deg': (65, 70),
        'reflected_allowed': True,
        'table': '1',
        'clause': '6.2.1.3',
    },
    {
        'thickness_mm': (12.0, 20.0),
        'frequency_mhz': (2.5, 5.0),
        'angle_direct_deg': (65, 70),
        'angle_reflected_deg': (65, 70),
        'reflected_allowed': True,
        'table': '1',
        'clause': '6.2.1.3',
    },
    {
        'thickness_mm': (20.0, 40.0),
        'frequency_mhz': (2.5, 4.0),
        'angle_direct_deg': (65, 70),
        'angle_reflected_deg': (45, 50),
        'reflected_allowed': True,
        'table': '1',
        'clause': '6.2.1.3',
    },
    {
        'thickness_mm': (40.0, 60.0),
        'frequency_mhz': (1.8, 4.0),
        'angle_direct_deg': (65, 70),
        'angle_reflected_deg': (45, 50),
        'reflected_allowed': True,
        'table': '1',
        'clause': '6.2.1.3',
    },
    {
        'thickness_mm': (60.0, 100.0),
        'frequency_mhz': (1.8, 2.5),
        'angle_direct_deg': (45, 50, 60, 65),
        'angle_reflected_deg': None,
        'reflected_allowed': False,
        'note': 'Углы 60°/65° — только прямой луч на глубину ≤60 мм; полная глубина — 45°/50°',
        'table': '1',
        'clause': '6.2.1.3, прим. 2',
    },
    {
        'thickness_mm': (100.0, 400.0),
        'frequency_mhz': (1.0, 2.0),
        'angle_direct_deg': (45, 50, 60, 65),
        'angle_reflected_deg': None,
        'reflected_allowed': False,
        'table': '1',
        'clause': '6.2.1.3',
    },
]

TABLE_1_NOTES = (
    'Для каждого диапазона выбирают один или несколько номинальных углов ввода. '
    'В ТИ/ТКК параметры УЗК указывают однозначно — диапазоны в ТКК не допускаются (прим. 3).'
)

# ------------------------------------------------------------------
# Таблица 2 — прямые ПЭП для стыковых СС (п. 6.2.1.4)
# ------------------------------------------------------------------
TABLE_2_STRAIGHT_PEP_BUTT = [
    {'thickness_mm': (5.5, 20.0), 'frequency_mhz': (4.0, 6.0), 'pep_type': 'ПРС', 'table': '2', 'clause': '6.2.1.4'},
    {'thickness_mm': (20.0, 40.0), 'frequency_mhz': (2.5, 4.0), 'pep_type': 'ПРС', 'table': '2', 'clause': '6.2.1.4'},
    {'thickness_mm': (40.0, 60.0), 'frequency_mhz': (1.8, 4.0), 'pep_type': 'ПС+ПРС', 'table': '2', 'clause': '6.2.1.4'},
    {'thickness_mm': (60.0, 400.0), 'frequency_mhz': (1.25, 2.50), 'pep_type': 'ПС+ПРС', 'table': '2', 'clause': '6.2.1.4'},
]

# ------------------------------------------------------------------
# Таблица 3 — прямые ПЭП для угловых/тавровых СС (п. 6.4.1)
# ------------------------------------------------------------------
TABLE_3_STRAIGHT_PEP_ANGLE_TEE = [
    {'thickness_mm': (5.5, 20.0), 'frequency_mhz': (2.5, 6.0), 'pep_type': 'ПРС', 'table': '3', 'clause': '6.4.1'},
    {'thickness_mm': (20.0, 40.0), 'frequency_mhz': (2.0, 4.0), 'pep_type': 'ПРС', 'table': '3', 'clause': '6.4.1'},
    {'thickness_mm': (40.0, 60.0), 'frequency_mhz': (1.8, 2.5), 'pep_type': 'ПС', 'table': '3', 'clause': '6.4.1'},
    {'thickness_mm': (60.0, 400.0), 'frequency_mhz': (1.0, 2.5), 'pep_type': 'ПС', 'table': '3', 'clause': '6.4.1'},
]

# ------------------------------------------------------------------
# Таблица 4 — НП для угловых/тавровых СС (п. 6.4.1)
# angle_from_main — углы в скобках таблицы 4 при вводе со стороны основной детали
# ------------------------------------------------------------------
TABLE_4_NP_ANGLE_TEE = [
    {
        'thickness_mm': (5.5, 20.0),
        'frequency_mhz': (2.5, 6.0),
        'angle_direct_deg': (65, 70, 72),
        'angle_from_main_deg': (40, 45, 50, 65, 70),
        'angle_reflected_deg': (65, 70),
        'reflected_allowed': True,
        'table': '4',
        'clause': '6.4.1',
    },
    {
        'thickness_mm': (20.0, 40.0),
        'frequency_mhz': (2.0, 4.0),
        'angle_direct_deg': (65, 70),
        'angle_from_main_deg': (40, 45, 50),
        'angle_reflected_deg': (65, 70),
        'reflected_allowed': True,
        'table': '4',
        'clause': '6.4.1',
    },
    {
        'thickness_mm': (40.0, 60.0),
        'frequency_mhz': (1.8, 2.5),
        'angle_direct_deg': (50, 60, 65),
        'angle_from_main_deg': (40, 45, 50),
        'angle_reflected_deg': (45, 50),
        'reflected_allowed': True,
        'table': '4',
        'clause': '6.4.1',
    },
    {
        'thickness_mm': (60.0, 100.0),
        'frequency_mhz': (1.8, 2.5),
        'angle_direct_deg': (50, 60, 65),
        'angle_from_main_deg': (40, 45, 50),
        'angle_reflected_deg': None,
        'reflected_allowed': False,
        'table': '4',
        'clause': '6.4.1',
    },
    {
        'thickness_mm': (100.0, 400.0),
        'frequency_mhz': (1.0, 2.5),
        'angle_direct_deg': (45, 50),
        'angle_from_main_deg': (40, 45, 50),
        'angle_reflected_deg': None,
        'reflected_allowed': False,
        'table': '4',
        'clause': '6.4.1',
    },
]

# ------------------------------------------------------------------
# Таблица 5 — УЗК на поперечные несплошности (п. 6.5.1)
# ------------------------------------------------------------------
TABLE_5_TRANSVERSE_INSPECTION = [
    {
        'joint_type': 'стыковое без усиления',
        'scan_surface': 'поверхность шва и околошовной зоны',
        'diameter_main_mm_min': 300,
        'thickness_mm_min': 34,
        'scheme': 'рис. 4а или 4б',
        'table': '5',
        'clause': '6.5.1',
    },
    {
        'joint_type': 'стыковое с усилением',
        'scan_surface': 'основной металл околошовной зоны',
        'diameter_main_mm_min': 800,
        'thickness_mm': (34, 60),
        'scheme': 'рис. 4в* или 4г',
        'note': 'Для Х-образной разделки предпочтительна схема рис. 4г',
        'table': '5',
        'clause': '6.5.1',
    },
    {
        'joint_type': 'угловое и тавровое с усилением',
        'scan_surface': 'со стороны основной детали (зона проекции шва + 10 мм)',
        'diameter_main_mm_min': 800,
        'thickness_mm_min': None,
        'scheme': 'рис. 4а',
        'table': '5',
        'clause': '6.5.1',
    },
    {
        'joint_type': 'угловое и тавровое с усилением',
        'scan_surface': 'со стороны привариваемой детали (патрубка)',
        'diameter_branch_mm_min': 800,
        'thickness_mm_min': 60,
        'scheme': 'рис. 4в',
        'table': '5',
        'clause': '6.5.1',
    },
]

# ------------------------------------------------------------------
# Таблица 6 — коэффициент K(α) для пересчёта зарубки (п. 7.4.2.5, формула 7)
# ------------------------------------------------------------------
TABLE_6_ANGLE_COEFFICIENT_K = {
    40: 2.4,
    45: 1.75,
    50: 1.25,
    55: 0.85,
    60: 0.6,
    65: 0.5,
    70: 0.7,
    72: 0.8,
}

# ------------------------------------------------------------------
# Таблица 7 — максимальная ширина фаски в вершине двугранного угла (п. 7.4.2.11)
# ------------------------------------------------------------------
TABLE_7_CHAMFER_WIDTH_MM = [
    {'frequency_mhz': (2.0, 2.5), 'width_mm_thickness_70_120': 1.5, 'width_mm_thickness_over_120': 3.0, 'table': '7', 'clause': '7.4.2.11'},
    {'frequency_mhz': (4.0, 4.0), 'tolerance_mhz': 1.0, 'width_mm_thickness_70_120': 1.0, 'width_mm_thickness_over_120': 2.0, 'table': '7', 'clause': '7.4.2.11'},
]

SENSITIVITY_CORRECTION_MAX_DB = 12  # п. 7.4.2.7

# ------------------------------------------------------------------
# Степени контроледоступности СС (п. 6.8.3)
# ------------------------------------------------------------------
ACCESSIBILITY_WELD = {
    '1C': 'центральный луч пересекает каждую точку сечения в ≥3 направлениях (различие ≥35°)',
    '2C': 'в ≥2 направлениях',
    '3C': 'в ≥1 направлении',
    '4C': 'часть сечения не прозвучивается ни в одном направлении для 1С',
    'inaccessible': 'всё сечение не прозвучивается',
}
ACCESSIBILITY_DIRECTION_MIN_ANGLE_DEG = 35

# Наплавки (п. 6.8.3.3)
ACCESSIBILITY_CLADDING = {
    '1N': 'непараллельность границы сплавления ≤ δ (формула 1)',
    '2NA': 'превышает δ, но УЗК с основного металла спец. ПЭП или зеркально',
    '2NB': 'УЗК только со стороны наплавки, непараллельность ≤ δ',
    'inaccessible': 'не выполнены а–в',
}

# ------------------------------------------------------------------
# Наплавки — частоты (п. 6.6, 6.7)
# ------------------------------------------------------------------
CLADDING_FREQUENCY_MHZ = (2.0, 5.0)
CLADDING_BASE_LAYER_MM = 2.0  # прилегающий слой ОМ, п. 6.6.1.1
CLADDING_NP_ANGLE_DEG = (65, 70)

# ------------------------------------------------------------------
# Разметка (п. 7.2)
# ------------------------------------------------------------------
MARKING_SEGMENT_LENGTH_MAX_MM = 500
MARKING_ANP_AREA_MAX_M2 = 0.25
MARKING_ANP_SIDE_MAX_M = 1.0

# ------------------------------------------------------------------
# Погрешности измерения параметров несплошностей (п. 7.6.1.9)
# ------------------------------------------------------------------
MEASUREMENT_TOLERANCE = {
    'amplitude_db': 2.0,
    'equivalent_area_pct': 50.0,
    'conditional_length_mm_thickness_le_200': 5.0,
    'conditional_length_mm_thickness_gt_200': 10.0,
    'conditional_height': 'удвоенные пределы погрешности глубиномера',
}

# ------------------------------------------------------------------
# Контактные среды — приложение В (справочное)
# ------------------------------------------------------------------
CONTACT_MEDIA = {
    'wallpaper_glue': {
        'name': 'на основе обойного клея',
        'composition': 'клей : вода = 1:1 … 1:3',
        'clause': 'В.1',
    },
    'dextrin': {
        'name': 'на основе дикстрина',
        'composition_pct': {'dextrin': (30, 34), 'OP-7': 4, 'glycerin': (9, 10), 'soda': 1, 'water': 'остальное'},
        'prep_temp_c': (40, 50),
        'clause': 'В.2',
    },
    'iks_1': {
        'name': 'ингибиторная ИКС-1',
        'composition_per_l_water': {'glycerin_g': (50, 70), 'Na-CMC_g': (40, 50), 'trisodium_phosphate_g': (30, 50)},
        'clause': 'В.3',
    },
}

# ------------------------------------------------------------------
# Таблица П.1 — НО для корпусов задвижек (прил. П)
# OCR: заголовки столбцов частично потеряны; числовые ряды сохранены как в тексте
# ------------------------------------------------------------------
TABLE_P1_VALVE_BODY_NO = {
    'note': 'OCR неполный: имена параметров строк (D, H, углы) в шапке таблицы потеряны',
    'angles_deg': (40, 50),
    'dn_groups': ['DN100-150', 'DN175-200', 'DN250'],
    'rows': [
        {'values_40deg': [135, 230, 250], 'values_50deg': [135, 230, 250]},
        {'values_40deg': [30, 45, 72], 'values_50deg': [30, 45, 72]},
        {'values_40deg': [30, 33, 25], 'values_50deg': [14, 22, 7]},
        {'values_40deg': [7, 7, 7], 'values_50deg': [7, 7, 7]},
        {'values_40deg': [46, 73, 118], 'values_50deg': [58, 80, 150]},
        {'values_40deg': [28, 48, 70], 'values_50deg': [26, 42, 60]},
    ],
    'table': 'П.1',
    'clause': 'П.5',
}

# ------------------------------------------------------------------
# Таблица Р.1 — положения ПЭП при УЗК угловых СС (прил. Р)
# ------------------------------------------------------------------
TABLE_R1_BRANCH_PEP_POSITIONS = [
    {'wall_thickness_mm': 4.5, 'sector_ab_mm': 7, 'sector_bg_mm': 5, 'sectors_1_4_mm': (17, 30)},
    {'wall_thickness_mm': 6, 'sector_ab_mm': 10, 'sector_bg_mm': 5, 'sectors_1_4_extra_mm': 7, 'sectors_1_4_mm': (20, 32)},
    {'wall_thickness_mm': 9, 'sector_ab_mm': 20, 'sector_bg_mm': 15, 'sectors_1_4_extra_mm': 17, 'sectors_1_4_mm': (35, 50)},
    {'wall_thickness_mm': (11, 12), 'sector_ab_mm': 25, 'sector_bg_mm': 20, 'sectors_1_4_extra_mm': 23, 'sectors_1_4_mm': (45, 60)},
    {'wall_thickness_mm': 16, 'sector_ab_mm': 23, 'sector_bg_mm': 15, 'sectors_1_4_extra_mm': 20, 'sectors_1_4_mm': (40, 60)},
    {'wall_thickness_mm': 18, 'sector_ab_mm': 25, 'sector_bg_mm': 17, 'sectors_1_4_extra_mm': 21, 'sectors_1_4_mm': (45, 65)},
]

# ------------------------------------------------------------------
# Пример таблицы Н.1 — уровни чувствительности по глубине (прил. Н, пример)
# ------------------------------------------------------------------
TABLE_H1_EXAMPLE_LEVELS_DB = [
    {'depth_mm': 20, 'reject_db': 57, 'control_db': 63, 'search_db': 69},
    {'depth_mm': 40, 'reject_db': 52, 'control_db': 58, 'search_db': 64},
    {'depth_mm': 60, 'reject_db': 53, 'control_db': 59, 'search_db': 65},
]

# ------------------------------------------------------------------
# Содержание ТКК/ТИ — приложение Г (краткий перечень)
# ------------------------------------------------------------------
TECH_CARD_REQUIRED_ITEMS = (
    'идентификация СС/наплавки (чертёж, материал, способ сварки, категория, объём, степень контроледоступности)',
    'документация, регламентирующая УЗК и нормы оценки ([2], [4], [10], КД, ТД)',
    'тип и размеры ОК для выбора параметров УЗК',
    'требования по оценке качества и настройке чувствительности',
    'аппаратура: дефектоскоп, ПЭП (тип/частота/угол), КО, НО, АРД-диаграммы',
    'схемы прозвучивания и сканирования с однозначными параметрами',
    'подготовка поверхности (п. 6.8.7–6.8.10)',
    'оформление отчётной документации',
    'раздел «Оценка качества»: допустимые экв. площади, протяжённости, количество, ориентация',
)

# ------------------------------------------------------------------
# Операции прозвучивания (п. 6.1.1)
# ------------------------------------------------------------------
SOUNDING_OPERATIONS = (
    'а) продольные волны 0° (ПС, ПРС)',
    'б) поперечные волны с углом ввода >33,5°',
    'в) головные волны',
    'г) «тандем» / «корневой тандем»',
    'д) стредл-схема',
)


# ------------------------------------------------------------------
# Функции справочника
# ------------------------------------------------------------------

def _match_thickness(thickness_mm: float, range_pair: tuple) -> bool:
    lo, hi = range_pair
    if lo <= thickness_mm <= hi:
        return True
    if thickness_mm == lo and 'включ' in str(range_pair):
        return True
    return lo < thickness_mm <= hi if lo != hi else thickness_mm == lo


def get_table1_np_row(thickness_mm: float) -> Optional[dict]:
    """Строка табл. 1 для стыковых СС по номинальной толщине."""
    for row in TABLE_1_NP_BUTT_WELDS:
        lo, hi = row['thickness_mm']
        if lo <= thickness_mm <= hi:
            return row
    return None


def get_table2_straight_pep_row(thickness_mm: float) -> Optional[dict]:
    """Строка табл. 2 — прямые ПЭП для стыковых СС."""
    for row in TABLE_2_STRAIGHT_PEP_BUTT:
        lo, hi = row['thickness_mm']
        if lo <= thickness_mm <= hi:
            return row
    return None


def get_table4_np_row(thickness_mm: float) -> Optional[dict]:
    """Строка табл. 4 — НП для угловых/тавровых СС."""
    for row in TABLE_4_NP_ANGLE_TEE:
        lo, hi = row['thickness_mm']
        if lo <= thickness_mm <= hi:
            return row
    return None


def get_angle_coefficient_k(angle_deg: float) -> Optional[float]:
    """Коэффициент K из табл. 6 для пересчёта площади зарубки (формула 7)."""
    if angle_deg in TABLE_6_ANGLE_COEFFICIENT_K:
        return TABLE_6_ANGLE_COEFFICIENT_K[angle_deg]
    # ближайший номинальный угол
    keys = sorted(TABLE_6_ANGLE_COEFFICIENT_K)
    for k in keys:
        if abs(k - angle_deg) < 1.0:
            return TABLE_6_ANGLE_COEFFICIENT_K[k]
    return None


def equivalent_flat_area_from_notch_area(notch_area_mm2: float, angle_deg: float) -> Optional[float]:
    """Эквивалентная площадь Sэкв = K(α)·Sзар (формула 7, п. 7.4.2.5)."""
    k = get_angle_coefficient_k(angle_deg)
    if k is None:
        return None
    return k * notch_area_mm2


def sensitivity_levels_db_from_reject(reject_db: float) -> dict:
    """Контрольный (+6 дБ) и поисковый (+12 дБ) относительно браковочного (п. 7.4.2.2)."""
    return {
        'reject_db': reject_db,
        'control_db': reject_db + SENSITIVITY_LEVEL_OFFSET_DB['control'],
        'search_db': reject_db + SENSITIVITY_LEVEL_OFFSET_DB['search'],
    }


def is_ambient_ok(temp_c: float) -> bool:
    """Температура окружающей среды и металла в зоне контроля (п. 5.2.7)."""
    return AMBIENT_TEMP_MIN_C <= temp_c <= AMBIENT_TEMP_MAX_C


def is_manual_uzk_time_allowed(hour_local: int, has_auto_recording: bool) -> bool:
    """Ручной УЗК без авто-записи запрещён 00:00–06:00 (п. 5.10)."""
    if has_auto_recording:
        return True
    start, end = MANUAL_UZK_FORBIDDEN_HOURS
    return not (start <= hour_local < end)


def format_scope() -> str:
    return f'{DOCUMENT_CODE}, раздел 1, п. 5.1: {SCOPE}'


def format_table1(thickness_mm: Optional[float] = None) -> str:
    lines = [f'{DOCUMENT_CODE}, таблица 1 — параметры НП для стыковых СС:']
    rows = TABLE_1_NP_BUTT_WELDS
    if thickness_mm is not None:
        row = get_table1_np_row(thickness_mm)
        rows = [row] if row else []
    for row in rows:
        if not row:
            continue
        lo, hi = row['thickness_mm']
        refl = row['angle_reflected_deg']
        refl_txt = f'{refl}' if refl else 'не допускается'
        lines.append(
            f"  t={lo}–{hi} мм: f={row['frequency_mhz']} МГц, "
            f"прямой {row['angle_direct_deg']}°, отражённый {refl_txt}."
        )
    lines.append(TABLE_1_NOTES)
    return ' '.join(lines)


def format_sensitivity_levels() -> str:
    return (
        f'{DOCUMENT_CODE}, п. 7.4.2.2: браковочный — по НП/КД/ТД; '
        f'контрольный (фиксации) = браковочный + {SENSITIVITY_LEVEL_OFFSET_DB["control"]} дБ; '
        f'поисковый = браковочный + {SENSITIVITY_LEVEL_OFFSET_DB["search"]} дБ. '
        f'Поперечные несплошности: поиск на +{TRANSVERSE_SEARCH_OFFSET_DB} дБ к контрольному (п. 6.5.3).'
    )


def format_surface_prep() -> str:
    return (
        f'{DOCUMENT_CODE}, п. 6.8.9: шероховатость зоны сканирования Ra ≤ {SURFACE_ROUGHNESS_RA_MAX} '
        f'(Rz {SURFACE_ROUGHNESS_RZ_MAX:g}); донная при отражённом луче Ra ≤ {BOTTOM_ROUGHNESS_RA_MAX} '
        f'(Rz {BOTTOM_ROUGHNESS_RZ_MAX:g}); зазор от волнистости ≤ {SURFACE_GAP_MAX_MM} мм.'
    )


def format_personnel() -> str:
    return (
        f'{DOCUMENT_CODE}, п. 6.10: допускаются специалисты с подтверждённой компетентностью по '
        f'{PERSONNEL_STANDARD}. Группа ≥ {TEAM_SIZE_MIN} чел., минимум один — с правом выдачи заключения (п. 5.2.9).'
    )


def format_recording() -> str:
    return (
        f'{DOCUMENT_CODE}, раздел 8: учётная документация — по [2], [10]; журнал со сквозной нумерацией; '
        f'отчёт — заключение (протокол) по [2], [10]. Допускается электронный журнал при возможности '
        f'восстановления (п. 8.1.5).'
    )


def format_transverse_table5() -> str:
    parts = [f'{DOCUMENT_CODE}, таблица 5 — УЗК на поперечные несплошности:']
    for row in TABLE_5_TRANSVERSE_INSPECTION:
        parts.append(
            f"  {row['joint_type']}: {row['scan_surface']}, схема {row['scheme']}."
        )
    return ' '.join(parts)


def all_kb_chunks() -> list[tuple[str, str]]:
    """Фрагменты базы знаний для RAG (30–100 чанков)."""
    chunks: list[tuple[str, str]] = []

    chunks.append(('identity', (
        f'{DOCUMENT_FULL_NAME}. Код метода: {METHOD_CODE}. '
        f'Действует с {DOCUMENT_EFFECTIVE_FROM}, заменяет {DOCUMENT_REPLACES}.'
    )))

    chunks.append(('scope', format_scope()))

    for code, row in SCOPE_OBJECTS.items():
        chunks.append((f'scope_{code}', (
            f"{DOCUMENT_CODE}, {row.get('clause', '5.1.1')}: {row['description']}. "
            f"Параметры: {row}."
        )))

    chunks.append(('curvature', (
        f'{DOCUMENT_CODE}, п. 5.1.2: мин. радиус кривизны — '
        f'продольные швы {CURVATURE_RADIUS_MIN_MM["longitudinal_weld_outer"]} мм, '
        f'наплавки {CURVATURE_RADIUS_MIN_MM["cladding_surface"]} мм, '
        f'кольцевые {CURVATURE_RADIUS_MIN_MM["circumferential_weld"]} мм, '
        f'внутр. угловые/тавровые {CURVATURE_RADIUS_MIN_MM["inner_angle_tee"]} мм.'
    )))

    chunks.append(('purpose_limits', (
        f'{DOCUMENT_CODE}, п. 5.1.3–5.1.4: контактный УЗК для выявления несплошностей по экв. площади '
        f'из [2],[4],[10],КД; не определяет действительные размеры; «мёртвая зона» и усиление шва — '
        f'ограничения; проверка мёртвой зоны — СО-2 по {EQUIPMENT_STANDARD}.'
    )))

    for abbr, full in ABBREVIATIONS.items():
        chunks.append((f'abbr_{abbr}', f'{DOCUMENT_CODE}, раздел 4: {abbr} — {full}.'))

    for key, term in TERMS.items():
        chunks.append((f'term_{key}', (
            f"{DOCUMENT_CODE}, {key} {term['term']}: {term['definition']}"
            + (f" ({term['source']})" if term.get('source') else '')
        )))

    chunks.append(('ambient', (
        f'{DOCUMENT_CODE}, п. 5.2.7: УЗК при {AMBIENT_TEMP_MIN_C}…{AMBIENT_TEMP_MAX_C} °C. '
        f'Освещённость ≥ {ILLUMINANCE_MIN_LX} лк (п. 5.2.4). '
        f'Вибрация/пыль < {VIBRATION_FORBIDDEN_DISTANCE_M} м; яркий свет < {BRIGHT_LIGHT_SCREEN_DISTANCE_M} м — экранировать.'
    )))

    chunks.append(('team', format_personnel()))
    chunks.append(('night_ban', (
        f'{DOCUMENT_CODE}, п. 5.10: ручной УЗК без автоматической записи сканирования '
        f'с {MANUAL_UZK_FORBIDDEN_HOURS[0]:02d}:00 до {MANUAL_UZK_FORBIDDEN_HOURS[1]:02d}:00 запрещён.'
    )))

    chunks.append(('contact_media_intro', (
        f'{DOCUMENT_CODE}, п. 5.2.10–5.2.12: контактная среда — смачиваемость, вязкость, прозрачность для УЗ; '
        f'не является ДМ; составы — приложение В.'
    )))
    for key, media in CONTACT_MEDIA.items():
        chunks.append((f'contact_{key}', f"{DOCUMENT_CODE}, {media['clause']}: {media['name']} — {media}."))

    chunks.append(('surface_prep', format_surface_prep()))
    chunks.append(('sensitivity', format_sensitivity_levels()))
    chunks.append(('transverse', format_transverse_table5()))
    chunks.append(('personnel', format_personnel()))
    chunks.append(('recording', format_recording()))

    for i, row in enumerate(TABLE_1_NP_BUTT_WELDS):
        lo, hi = row['thickness_mm']
        chunks.append((f'table1_row_{i}', (
            f"{DOCUMENT_CODE}, табл. 1, {lo}–{hi} мм: частота {row['frequency_mhz']} МГц, "
            f"НП прямой {row['angle_direct_deg']}°, отражённый {row.get('angle_reflected_deg') or 'нет'}."
        )))

    for i, row in enumerate(TABLE_2_STRAIGHT_PEP_BUTT):
        lo, hi = row['thickness_mm']
        chunks.append((f'table2_row_{i}', (
            f"{DOCUMENT_CODE}, табл. 2, {lo}–{hi} мм: {row['pep_type']}, f={row['frequency_mhz']} МГц."
        )))

    for i, row in enumerate(TABLE_3_STRAIGHT_PEP_ANGLE_TEE):
        lo, hi = row['thickness_mm']
        chunks.append((f'table3_row_{i}', (
            f"{DOCUMENT_CODE}, табл. 3, {lo}–{hi} мм: {row['pep_type']}, f={row['frequency_mhz']} МГц."
        )))

    for i, row in enumerate(TABLE_4_NP_ANGLE_TEE):
        lo, hi = row['thickness_mm']
        chunks.append((f'table4_row_{i}', (
            f"{DOCUMENT_CODE}, табл. 4, {lo}–{hi} мм: f={row['frequency_mhz']} МГц, "
            f"прямой {row['angle_direct_deg']}°, со стороны основной {row['angle_from_main_deg']}."
        )))

    for i, row in enumerate(TABLE_5_TRANSVERSE_INSPECTION):
        chunks.append((f'table5_row_{i}', f"{DOCUMENT_CODE}, табл. 5: {row}."))

    for angle, k in TABLE_6_ANGLE_COEFFICIENT_K.items():
        chunks.append((f'table6_a{angle}', f'{DOCUMENT_CODE}, табл. 6: угол {angle}° → K={k}.'))

    for i, row in enumerate(TABLE_7_CHAMFER_WIDTH_MM):
        chunks.append((f'table7_row_{i}', f'{DOCUMENT_CODE}, табл. 7 — фаска двугранного угла: {row}.'))

    for code, desc in ACCESSIBILITY_WELD.items():
        chunks.append((f'access_weld_{code}', f'{DOCUMENT_CODE}, п. 6.8.3: степень {code} — {desc}.'))

    for code, desc in ACCESSIBILITY_CLADDING.items():
        chunks.append((f'access_clad_{code}', f'{DOCUMENT_CODE}, п. 6.8.3.3: {code} — {desc}.'))

    chunks.append(('cladding_freq', (
        f'{DOCUMENT_CODE}, п. 6.6–6.7: наплавки — частота {CLADDING_FREQUENCY_MHZ} МГц; '
        f'перлитные — слой ОМ {CLADDING_BASE_LAYER_MM} мм; НП {CLADDING_NP_ANGLE_DEG}°.'
    )))

    chunks.append(('marking', (
        f'{DOCUMENT_CODE}, п. 7.2: участки СС ≤ {MARKING_SEGMENT_LENGTH_MAX_MM} мм; '
        f'АНП — участки ≤ {MARKING_ANP_AREA_MAX_M2} м², сторона ≤ {MARKING_ANP_SIDE_MAX_M} м.'
    )))

    chunks.append(('scan', (
        f'{DOCUMENT_CODE}, п. 7.5: контактное сканирование; поворот ПЭП 0–15°; '
        f'шаг ≤ половины доп. протяжённости; v ≤ {SCAN_SPEED_MAX_MM_S} мм/с; '
        f'проверка настройки каждые {SETUP_VERIFY_INTERVAL_H} ч (п. 6.9.2.4).'
    )))

    chunks.append(('measurement_tol', (
        f'{DOCUMENT_CODE}, п. 7.6.1.9: погрешности — амплитуда ±{MEASUREMENT_TOLERANCE["amplitude_db"]} дБ, '
        f'экв. площадь ±{MEASUREMENT_TOLERANCE["equivalent_area_pct"]} %, '
        f'усл. протяжённость ±5/±10 мм.'
    )))

    chunks.append(('acceptance', (
        f'{DOCUMENT_CODE}, п. 7.6.2: допустимость — по [2],[4],[10], КД, ТД; '
        f'классификация протяжённых/точечных — приложение С; дефект типа «Т» — п. 7.6.2.3.'
    )))

    chunks.append(('tech_card', (
        f'{DOCUMENT_CODE}, приложение Г: содержание ТКК/ТИ — '
        + '; '.join(TECH_CARD_REQUIRED_ITEMS[:5]) + '; …'
    )))

    for i, row in enumerate(TABLE_H1_EXAMPLE_LEVELS_DB):
        chunks.append((f'appendix_h1_{i}', f'{DOCUMENT_CODE}, табл. Н.1 (пример): {row}.'))

    chunks.append(('appendix_p1', (
        f'{DOCUMENT_CODE}, табл. П.1 (корпуса задвижек): {TABLE_P1_VALVE_BODY_NO["note"]}. '
        f'Данные OCR: {TABLE_P1_VALVE_BODY_NO["rows"]}.'
    )))

    for i, row in enumerate(TABLE_R1_BRANCH_PEP_POSITIONS):
        chunks.append((f'appendix_r1_{i}', f'{DOCUMENT_CODE}, табл. Р.1, t={row["wall_thickness_mm"]} мм: {row}.'))

    for op in SOUNDING_OPERATIONS:
        chunks.append(('sound_op', f'{DOCUMENT_CODE}, п. 6.1.1: операция {op}.'))

    chunks.append(('equipment', (
        f'{DOCUMENT_CODE}, п. 6.9.1: дефектоскопы по {EQUIPMENT_STANDARD}; ПЭП по {PEP_STANDARD}; '
        f'отклонение угла ввода ≤ ±{PEP_ANGLE_DEVIATION_MAX_DEG}° (п. 6.9.3).'
    )))

    chunks.append(('vrch', (
        f'{DOCUMENT_CODE}, п. 7.4.2.16: для t > 40 мм рекомендуется ВРЧ (АРК); '
        f'корректировка Δ ≤ {SENSITIVITY_CORRECTION_MAX_DB} дБ (п. 7.4.2.7).'
    )))

    return chunks
