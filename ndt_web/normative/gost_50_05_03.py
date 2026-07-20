"""
Данные ГОСТ Р 50.05.03-2022 «Система оценки соответствия в области использования
атомной энергии. Оценка соответствия в форме контроля. Унифицированные методики.
Ультразвуковой контроль. Измерение толщины монометаллов, биметаллов и
антикоррозионных наплавленных поверхностей».

Модуль содержит структурированные требования для ИИ-консультанта и справочных
вызовов (tools) по ультразвуковой толщинометрии (УЗТ):
- диапазоны измеряемой толщины и геометрии ОК (п. 5.1, 5.5);
- способы измерения моно-/биметалла и АНП (раздел 7);
- требования к поверхности, СИ, НО (разделы 8–9);
- погрешности и критерии годности (раздел 11);
- технология измерений и сканирования (разделы 12–13).

Источник: ГОСТ Р 50.05.03-2022 (введён в действие 01.01.2024, заменяет 50.05.03-2018).

ВАЖНО: при изменении стандарта актуализировать этот модуль по тексту НД.
"""

from __future__ import annotations

from typing import Optional

# ------------------------------------------------------------------
# Идентификатор документа
# ------------------------------------------------------------------
DOCUMENT_CODE = 'ГОСТ Р 50.05.03-2022'
DOCUMENT_SHORT = 'ГОСТ Р 50.05.03'
DOCUMENT_FULL_NAME = (
    'ГОСТ Р 50.05.03-2022 «Система оценки соответствия в области использования '
    'атомной энергии. Оценка соответствия в форме контроля. Унифицированные '
    'методики. Ультразвуковой контроль. Измерение толщины монометаллов, '
    'биметаллов и антикоррозионных наплавленных поверхностей»'
)
DOCUMENT_EFFECTIVE_FROM = '2024-01-01'
DOCUMENT_REPLACES = 'ГОСТ Р 50.05.03-2018'
METHOD_CODE = 'УЗТ'
METHOD_NAME = 'ультразвуковая толщинометрия'
METHOD_NAME_EN = 'Ultrasonic thickness measurement (UTT)'

# ------------------------------------------------------------------
# Область применения (раздел 1, п. 5)
# ------------------------------------------------------------------
SCOPE = (
    'Оценка соответствия монометаллов, биметаллов и антикоррозионных наплавленных '
    'поверхностей (АНП) продукции АЭУ при изготовлении, монтаже и эксплуатации. '
    'Нормы оценки — [2], [4], [5], документы по стандартизации, КД и ТД.'
)

THICKNESS_RANGE_MM = (0.5, 1000.0)
CURVATURE_RADIUS_MIN_MM = 8.0
PARALLELISM_MAX_DEVIATION_DEG = 10.0  # п. 5.5

# ------------------------------------------------------------------
# Нормативные ссылки (раздел 2)
# ------------------------------------------------------------------
NORMATIVE_REFERENCES = (
    'ГОСТ 9.106',
    'ГОСТ 2789',
    'ГОСТ 15467',
    'ГОСТ 20911',
    'ГОСТ Р 8.932',
    'ГОСТ Р 8.1015',
    'ГОСТ Р 50.05.11',
    'ГОСТ Р 50.05.15',
    'ГОСТ Р 50.05.16',
    'ГОСТ Р 53697',
    'ГОСТ Р 55614',
    'ГОСТ Р 55724-2013',
)

PERSONNEL_STANDARD = 'ГОСТ Р 50.05.11'
THICKNESS_GAUGE_STANDARD = 'ГОСТ Р 55614'
METROLOGY_STANDARD = 'ГОСТ Р 50.05.16'

# ------------------------------------------------------------------
# Термины (раздел 3)
# ------------------------------------------------------------------
TERMS = {
    '3.1': {
        'term': 'антикоррозионная наплавленная поверхность',
        'definition': (
            'Наплавленная методом сварки поверхность ОМ детали, защищающая от '
            'коррозионной среды при эксплуатации.'
        ),
    },
    '3.2': {
        'term': 'биметалл',
        'definition': 'Металлический материал из двух слоёв разнородных металлов или сплавов.',
        'source': 'ГОСТ Р 59129-2020, ст. 147',
    },
    '3.4': {
        'term': 'донная поверхность объекта контроля',
        'definition': 'Поверхность ОК, противоположная поверхности ввода.',
        'source': 'ГОСТ 23829-85, ст. 11',
    },
    '3.9': {
        'term': 'монометалл',
        'definition': 'Однослойный металл.',
    },
    '3.15': {
        'term': 'эксплуатационный контроль металла',
        'definition': (
            'Контроль для оценки изменения состояния металла ОК и пригодности к '
            'дальнейшей эксплуатации.'
        ),
    },
}

ABBREVIATIONS = {
    'АНП': 'антикоррозионная наплавленная поверхность',
    'ЗИ': 'зондирующий импульс',
    'КД': 'конструкторская (проектная) документация',
    'КО': 'контрольный образец',
    'НО': 'настроечный образец',
    'НП': 'наклонный преобразователь',
    'ОК': 'объект контроля',
    'ПСП': 'прямой совмещенный преобразователь',
    'ПЭП': 'пьезоэлектрический преобразователь',
    'РСП': 'раздельно-совмещенный преобразователь',
    'СИ': 'средство измерений',
    'ТИ': 'технологическая инструкция',
    'ТКК': 'технологическая карта контроля',
    'УЗ': 'ультразвук (ультразвуковой)',
    'УЗК': 'ультразвуковой контроль',
    'УЗТ': 'ультразвуковой контроль с измерением толщины',
    'ЭМА': 'электромагнитно-акустический',
    'ЭМАП': 'электромагнитно-акустический преобразователь',
}

# ------------------------------------------------------------------
# Условия проведения (раздел 6, п. 5.8)
# ------------------------------------------------------------------
AMBIENT_TEMP_MIN_C = 5
AMBIENT_TEMP_MAX_C = 40
ILLUMINANCE_MIN_LX = 500
VIBRATION_FORBIDDEN_DISTANCE_M = 10
BRIGHT_LIGHT_SCREEN_DISTANCE_M = 15
MANUAL_UZT_FORBIDDEN_HOURS = (0, 6)
TEAM_SIZE_MIN = 2
SETUP_VERIFY_INTERVAL_H = 2
SCAN_SPEED_MAX_MM_S = 100.0
EMA_SCAN_STEP_MAX_MM = 5
CORROSION_SCAN_STEP_MAX_MM = 3
DISCRETE_POINT_DISTANCE_MM = (25, 150)

# ------------------------------------------------------------------
# Подготовка поверхности (раздел 8)
# ------------------------------------------------------------------
SURFACE_ROUGHNESS_RA_MAX = 6.3
SURFACE_ROUGHNESS_RZ_MAX = 40.0
SURFACE_GAP_MAX_MM = 0.2
EMA_GAP_RECOMMENDED_MAX_MM = 1.0
EMA_PAD_MAX_MM = 0.5
SURFACE_ROUGHNESS_STANDARD = 'ГОСТ 2789'
BOTTOM_ROUGHNESS_RA_DETECT_MAX = 40.0
BOTTOM_ROUGHNESS_RZ_DETECT_MAX = 160.0

PREP_AREA_MONOMETAL_MM = (30, 30)
PREP_AREA_ANP_PSP_RSP_MM = (50, 50)
PREP_AREA_DEFECT_FLAT_DIAM_MM = 15
PREP_AREA_ANP_NP_FORMULA = '40 × (2H + 60) мм'  # п. 12.3.2

# ------------------------------------------------------------------
# Средства контроля (раздел 9)
# ------------------------------------------------------------------
PEP_FREQUENCY_MHZ = (1.0, 15.0)
EMAP_FREQUENCY_MHZ = (2.0, 5.0)

# п. 9.6 — пределы допускаемой основной погрешности СИ
THICKNESS_METER_ERROR_FORMULA = '±(0,01·H + 0,1) мм'
DEFECTOSCOPE_ERROR_FORMULA = '±(0,02·H + 0,1) мм'

NO_METAL_VELOCITY_TOLERANCE_PCT = 1.0
NO_ATTENUATION_TOLERANCE_DB = 4.0
NO_MONOMETAL_MEASURE_TOLERANCE_MM = 0.01
SETUP_CHECK_THICKNESS_DEVIATION_PCT = 10
DIRECT_MEASURE_SETUP_TOLERANCE_MM = 0.05

# ------------------------------------------------------------------
# Настроечные образцы (раздел 9.9)
# ------------------------------------------------------------------
NO_TYPES = {
    'T1': {
        'use': 'настройка скорости УЗ дефектоскопа (монометалл); нуль толщиномера',
        'clause': '9.9.2',
    },
    'T2': {
        'use': 'настройка СИ при измерении толщины монометалла',
        'tolerance': 'H = (1±0,1)·Hном',
        'clause': '9.9.3',
    },
    'TB1': {
        'use': 'настройка СИ при измерении толщины биметалла',
        'clause': '9.9.4',
    },
    'TN1': {
        'use': 'скорость развертки при измерении АНП со стороны ОМ',
        'clause': '9.9.5',
    },
    'TN2': {
        'use': 'настройка дефектоскопа при измерении АНП со стороны наплавки',
        'clause': '9.9.6',
    },
    'TN3': {
        'use': 'настройка при измерении H АНП с обеих сторон',
        'tolerance': 'H = Hном ± 1 мм',
        'clause': '9.9.7',
    },
    'TNN1': {
        'use': 'измерение толщины АНП биметаллических труб НП',
        'clause': '9.9.8',
    },
    'NOT-1': {
        'use': 'альтернативный НО для настройки СИ',
        'clause': '9.9.14',
    },
}

NO_ALTERNATIVES = (
    'СО-2', 'СО-3', 'СО-2А', 'СО-3А', 'V1', 'V2 (ГОСТ Р 55724)',
)

# ------------------------------------------------------------------
# Способы измерения (раздел 7)
# ------------------------------------------------------------------
MEASUREMENT_METHODS = {
    'monometal': {
        'a': 'ЗИ → первый эхо-сигнал (рис. 1а)',
        'b': 'между донными эхо-сигналами (рис. 1б)',
        'c': 'излучатель на вводе → приёмник на донной поверхности (рис. 1в)',
        'pep': 'ПЭП контактным методом (а–в)',
        'emap': 'ЭМАП контактным/бесконтактным (а, б)',
        'clause': '7.1',
    },
    'bimetal': {
        'a': 'ЗИ → первый эхо (рис. 2а)',
        'b': 'ЗИ → эхо от границы сплавления (толщина ОМ, рис. 2б)',
        'c': 'между донными эхо (рис. 2в)',
        'pep': 'контактный ПЭП',
        'clause': '7.2',
    },
    'anp': {
        'a': 'между эхо границы сплавления и донным (рис. 3а, 3в)',
        'b': 'ЗИ → эхо границы сплавления (рис. 3б)',
        'pep': 'контактный ПЭП',
        'clause': '7.3',
    },
}

# ------------------------------------------------------------------
# Погрешности измерений (раздел 11)
# ------------------------------------------------------------------
CONFIDENCE_PROBABILITY = 0.95

THICKNESS_ERROR_LIMITS = {
    'anp_mm': 1.0,
    'cladding_plate_mm': 0.2,
    'monometal_thin_mm': 0.2,
    'monometal_thin_threshold_mm': 20.0,
    'monometal_thick_pct': 1.5,
    'monometal_thick_threshold_mm': 20.0,
    'acceptance_vs_tolerance_pct': 35,
}

# ------------------------------------------------------------------
# Параметры преобразователей для АНП и биметалла (раздел 13)
# ------------------------------------------------------------------
BIMETAL_PSP_FREQUENCY_MHZ = (2.0, 6.0)

ANP_NP_PARAMS = {
    'angle_deg': (38, 52),
    'frequency_mhz': (2.0, 5.0),
    'clause': '13.5.5',
}

ANP_RSP_FROM_CLADDING = [
    {
        'cladding_thickness_mm': (2, 8),
        'frequency_mhz': (4, 6),
        'focus_mm': (4, 10),
        'contact_diameter_max_mm': 16,
        'clause': '13.5.6',
    },
    {
        'cladding_thickness_mm': (8, None),
        'frequency_mhz': (4, 5),
        'focus_mm': (20, 30),
        'contact_diameter_max_mm': 16,
        'clause': '13.5.6',
    },
]

CORROSION_PROBE_RULES = {
    'wavelength_coverage_min': 1.5,
    'thickness_ge_10_mm': 'ПСП или ЭМАП',
    'thickness_lt_10_mm': 'прямой РСП',
    'pit_focus_match': True,
    'min_pit_diameter_detect_mm': 2.5,
    'min_pit_radius_mm': 1.5,
    'clause': '13.10',
}

# ------------------------------------------------------------------
# Настройка аппаратуры — соответствие образцов (п. 12.5)
# ------------------------------------------------------------------
SETUP_NO_MAPPING = {
    'thickness_meter_speed_monometal': 'T2',
    'thickness_meter_speed_bimetal': 'TB1',
    'defectoscope_speed_monometal': 'T1',
    'defectoscope_speed_bimetal': 'TB1',
    'defectoscope_speed_anp_base': ('TN1', 'TN3'),
    'defectoscope_speed_anp_cladding': ('TN2', 'TN3'),
    'defectoscope_speed_anp_np_tube': 'TNN1',
    'zero_monometal_bimetal': 'T1',
    'sweep_monometal': 'T2',
    'sweep_bimetal': 'TB1',
}

ECHO_HEIGHT_SCREEN_FRACTION = (0.5, 2 / 3)  # п. 12.5.9
ECHO_AMPLITUDE_MATCH_DB = 2.0  # п. 13.3.4

# ------------------------------------------------------------------
# Содержание ТКК/ТИ — приложение Б
# ------------------------------------------------------------------
TECH_CARD_REQUIRED_ITEMS = (
    'идентификационные данные ОК и схема разметки точек',
    'марка стали/сплава; для АНП — номинальная толщина и марка электродов/наплавки',
    'номинальная толщина в зоне контроля',
    'СИ и преобразователи с однозначными параметрами; НО',
    'погрешность измерения и критерии годности',
    'подготовка поверхности и разметки',
    'порядок измерения по настоящему стандарту',
    'для сканирования: шаг, скорость, схемы, именование файлов, хранение результатов',
)

# ------------------------------------------------------------------
# Единая ТКК для группы ОК (п. 12.2.5)
# ------------------------------------------------------------------
GROUP_TKK_CONDITIONS = {
    'same_steel_grade': True,
    'same_plastic_deformation': True,
    'same_surface_roughness_waviness_parallelism': True,
    'thickness_deviation_max_pct': 10,
    'curvature_radius_min_for_formula_mm': 250,
}

# ------------------------------------------------------------------
# Процедура шага сканирования ЭМАП — приложение В
# ------------------------------------------------------------------
APPENDIX_V_SCAN_STEP = {
    'reference_sample': 'СО-2',
    'hole_d_mm': 6,
    'hole_depth_mm': 15,
    'step_probe_mm': 1,
    'max_scan_step_rule': 'удвоенное расстояние от оси отверстия, где ещё определяется d=6 мм',
    'clause': 'приложение В',
}


# ------------------------------------------------------------------
# Функции справочника
# ------------------------------------------------------------------

def thickness_meter_max_error_mm(h_mm: float) -> float:
    """Предел основной погрешности толщиномера ±(0,01·H+0,1) мм (п. 9.6)."""
    return 0.01 * h_mm + 0.1


def defectoscope_max_error_mm(h_mm: float) -> float:
    """Предел основной погрешности дефектоскопа ±(0,02·H+0,1) мм (п. 9.6)."""
    return 0.02 * h_mm + 0.1


def get_thickness_error_limit(
    material_kind: str = 'monometal',
    nominal_thickness_mm: float = 10.0,
) -> dict:
    """
    Нормативная погрешность по разделу 11.

    :param material_kind: 'monometal' | 'bimetal' | 'anp' | 'cladding_plate'
    """
    kind = (material_kind or 'monometal').strip().lower()
    if kind in ('anp', 'anticorrosion', 'наплавка'):
        return {'value': THICKNESS_ERROR_LIMITS['anp_mm'], 'unit': 'mm', 'clause': '11.2'}
    if kind in ('cladding_plate', 'plating', 'плакировка'):
        return {'value': THICKNESS_ERROR_LIMITS['cladding_plate_mm'], 'unit': 'mm', 'clause': '11.3'}
    if nominal_thickness_mm < THICKNESS_ERROR_LIMITS['monometal_thin_threshold_mm']:
        return {'value': THICKNESS_ERROR_LIMITS['monometal_thin_mm'], 'unit': 'mm', 'clause': '11.5'}
    return {
        'value': THICKNESS_ERROR_LIMITS['monometal_thick_pct'],
        'unit': 'percent',
        'clause': '11.4',
    }


def is_geometry_ok(curvature_radius_mm: float, parallelism_deg: float = 0.0) -> bool:
    """Проверка п. 5.1 и 5.5 (радиус и параллельность/эквидистантность)."""
    if curvature_radius_mm < CURVATURE_RADIUS_MIN_MM:
        return False
    return abs(parallelism_deg) <= PARALLELISM_MAX_DEVIATION_DEG


def is_ambient_ok(temp_c: float) -> bool:
    return AMBIENT_TEMP_MIN_C <= temp_c <= AMBIENT_TEMP_MAX_C


def format_scope() -> str:
    return (
        f'{DOCUMENT_CODE}, п. 5.1: {SCOPE} '
        f'Диапазон t = {THICKNESS_RANGE_MM[0]}…{THICKNESS_RANGE_MM[1]} мм, '
        f'R ≥ {CURVATURE_RADIUS_MIN_MM} мм.'
    )


def format_parallelism() -> str:
    return (
        f'{DOCUMENT_CODE}, п. 5.5: поверхность ввода и донная — параллельны или '
        f'эквидистантны; макс. отклонение ±{PARALLELISM_MAX_DEVIATION_DEG}°.'
    )


def format_surface_prep() -> str:
    return (
        f'{DOCUMENT_CODE}, п. 8.1: Ra ≤ {SURFACE_ROUGHNESS_RA_MAX} (Rz {SURFACE_ROUGHNESS_RZ_MAX:g}); '
        f'зазор ≤ {SURFACE_GAP_MAX_MM} мм; для ЭМАП подготовка не требуется (п. 8.2), '
        f'зазор ≤ {EMA_GAP_RECOMMENDED_MAX_MM} мм.'
    )


def format_si_requirements() -> str:
    return (
        f'{DOCUMENT_CODE}, п. 9.1–9.6: толщиномеры по {THICKNESS_GAUGE_STANDARD}; '
        f'ПЭП f = {PEP_FREQUENCY_MHZ[0]}–{PEP_FREQUENCY_MHZ[1]} МГц; '
        f'ЭМАП f = {EMAP_FREQUENCY_MHZ[0]}–{EMAP_FREQUENCY_MHZ[1]} МГц; '
        f'погрешность толщиномера {THICKNESS_METER_ERROR_FORMULA}, '
        f'дефектоскопа {DEFECTOSCOPE_ERROR_FORMULA}.'
    )


def format_personnel() -> str:
    return (
        f'{DOCUMENT_CODE}, раздел 10: специалисты с компетентностью по {PERSONNEL_STANDARD}; '
        f'группа ≥ {TEAM_SIZE_MIN}, один — с правом заключения (п. 6.9).'
    )


def format_measurement_errors() -> str:
    return (
        f'{DOCUMENT_CODE}, раздел 11 (Р={CONFIDENCE_PROBABILITY}): '
        f'АНП ±{THICKNESS_ERROR_LIMITS["anp_mm"]} мм; '
        f'плакировка ±{THICKNESS_ERROR_LIMITS["cladding_plate_mm"]} мм; '
        f'монометалл < {THICKNESS_ERROR_LIMITS["monometal_thin_threshold_mm"]} мм — '
        f'±{THICKNESS_ERROR_LIMITS["monometal_thin_mm"]} мм; '
        f'≥ {THICKNESS_ERROR_LIMITS["monometal_thick_threshold_mm"]} мм — '
        f'±{THICKNESS_ERROR_LIMITS["monometal_thick_pct"]} %.'
    )


def format_acceptance_criterion(measured_mm: float, error_mm: float, min_allowed_mm: float) -> str:
    """Пример логики п. 11.8 и образца ТКК (рис. Б.1)."""
    adjusted = measured_mm - error_mm
    ok = adjusted > min_allowed_mm
    return (
        f'Измерено {measured_mm:g} мм, погрешность {error_mm:g} мм → '
        f'с учётом погрешности {adjusted:g} мм; мин. допустимо {min_allowed_mm:g} мм — '
        f'{"годен" if ok else "не годен"}.'
    )


def format_no_types() -> str:
    lines = [f'{DOCUMENT_CODE}, п. 9.9 — типы НО:']
    for code, info in NO_TYPES.items():
        lines.append(f'  {code}: {info["use"]} ({info["clause"]}).')
    return ' '.join(lines)


def format_scan_modes() -> str:
    return (
        f'{DOCUMENT_CODE}, п. 13.2: дискретно (рис. 18), по полосам (рис. 19), '
        f'сплошное сканирование (рис. 20); расстояние между точками '
        f'{DISCRETE_POINT_DISTANCE_MM[0]}–{DISCRETE_POINT_DISTANCE_MM[1]} мм; '
        f'v ≤ {SCAN_SPEED_MAX_MM_S} мм/с (ЭМАП); шаг ≤ {EMA_SCAN_STEP_MAX_MM} мм.'
    )


def all_kb_chunks() -> list[tuple[str, str]]:
    """Фрагменты базы знаний для RAG (30–100 чанков)."""
    chunks: list[tuple[str, str]] = []

    chunks.append(('identity', (
        f'{DOCUMENT_FULL_NAME}. Код: {METHOD_CODE}. '
        f'С {DOCUMENT_EFFECTIVE_FROM}, заменяет {DOCUMENT_REPLACES}.'
    )))

    chunks.append(('scope', format_scope()))
    chunks.append(('parallelism', format_parallelism()))
    chunks.append(('purpose', (
        f'{DOCUMENT_CODE}, п. 5.4: УЗТ — где недоступно прямое измерение (штангенциркуль, микрометр). '
        f'Объём, точки и критерии — в КД (п. 5.6).'
    )))

    for abbr, full in ABBREVIATIONS.items():
        chunks.append((f'abbr_{abbr}', f'{DOCUMENT_CODE}, раздел 4: {abbr} — {full}.'))

    for key, term in TERMS.items():
        src = f" ({term['source']})" if term.get('source') else ''
        chunks.append((f'term_{key}', f"{DOCUMENT_CODE}, {key} {term['term']}: {term['definition']}{src}"))

    chunks.append(('ambient', (
        f'{DOCUMENT_CODE}, п. 6.7: {AMBIENT_TEMP_MIN_C}…{AMBIENT_TEMP_MAX_C} °C; '
        f'освещённость ≥ {ILLUMINANCE_MIN_LX} лк (п. 6.4).'
    )))

    chunks.append(('night_ban', (
        f'{DOCUMENT_CODE}, п. 5.8: ручной УЗТ без авто-записи запрещён '
        f'{MANUAL_UZT_FORBIDDEN_HOURS[0]:02d}:00–{MANUAL_UZT_FORBIDDEN_HOURS[1]:02d}:00.'
    )))

    chunks.append(('team', format_personnel()))
    chunks.append(('surface', format_surface_prep()))
    chunks.append(('si', format_si_requirements()))
    chunks.append(('errors', format_measurement_errors()))
    chunks.append(('no_types', format_no_types()))
    chunks.append(('scan', format_scan_modes()))

    for kind, methods in MEASUREMENT_METHODS.items():
        chunks.append((f'method_{kind}', f'{DOCUMENT_CODE}, {methods["clause"]}: способы {kind} — {methods}.'))

    for code, info in NO_TYPES.items():
        chunks.append((f'no_{code.lower()}', f'{DOCUMENT_CODE}, {info["clause"]}: НО {code} — {info["use"]}.'))

    chunks.append(('no_alt', (
        f'{DOCUMENT_CODE}, п. 9.9.15: допускаются {", ".join(NO_ALTERNATIVES)} при выполнении 9.9.1.'
    )))

    chunks.append(('no_tolerance', (
        f'{DOCUMENT_CODE}, п. 9.9.16: допуски НО vs ОК — скорость УЗ ±{NO_METAL_VELOCITY_TOLERANCE_PCT} %, '
        f'затухание ±{NO_ATTENUATION_TOLERANCE_DB} дБ.'
    )))

    for key, sample in SETUP_NO_MAPPING.items():
        chunks.append((f'setup_{key}', f'{DOCUMENT_CODE}, п. 12.5: {key} → образец {sample}.'))

    chunks.append(('setup_check', (
        f'{DOCUMENT_CODE}, п. 12.5.12–12.6: проверка настройки до/после, каждые {SETUP_VERIFY_INTERVAL_H} ч; '
        f'отклонение t на ОК ≤ {SETUP_CHECK_THICKNESS_DEVIATION_PCT} %.'
    )))

    chunks.append(('prep_discrete', (
        f'{DOCUMENT_CODE}, п. 12.3.1: площадка {PREP_AREA_MONOMETAL_MM[0]}×{PREP_AREA_MONOMETAL_MM[1]} мм; '
        f'АНП ПСП/РСП — {PREP_AREA_ANP_PSP_RSP_MM[0]}×{PREP_AREA_ANP_PSP_RSP_MM[1]} мм; '
        f'АНП НП — {PREP_AREA_ANP_NP_FORMULA}.'
    )))

    chunks.append(('bimetal_pep', (
        f'{DOCUMENT_CODE}, п. 13.4.2: биметалл с ОМ — ПСП f={BIMETAL_PSP_FREQUENCY_MHZ} МГц, '
        f'жёсткий протектор, узкая ДН.'
    )))

    chunks.append(('anp_np', (
        f'{DOCUMENT_CODE}, п. 13.5.5: АНП НП — два ПЭП {ANP_NP_PARAMS["angle_deg"]}°, '
        f'f={ANP_NP_PARAMS["frequency_mhz"]} МГц, раздельная схема.'
    )))

    for i, row in enumerate(ANP_RSP_FROM_CLADDING):
        chunks.append((f'anp_rsp_{i}', f'{DOCUMENT_CODE}, п. 13.5.6: {row}.'))

    chunks.append(('anp_base_side', (
        f'{DOCUMENT_CODE}, п. 13.5.2: t_АНП = разность донного эхо и эхо зоны сплавления.'
    )))

    chunks.append(('anp_cladding_side', (
        f'{DOCUMENT_CODE}, п. 13.5.9: со стороны наплавки — положение эхо границы сплавления; '
        f'если эхо нет — отметить в заключении (п. 13.5.10).'
    )))

    chunks.append(('emap_static', (
        f'{DOCUMENT_CODE}, п. 13.6: ЭМАП под углом 30–60°, прокладка ≤ {EMA_PAD_MAX_MM} мм; '
        f'магнит вдоль оси трубы (п. 13.6.5).'
    )))

    chunks.append(('emap_dynamic', (
        f'{DOCUMENT_CODE}, п. 13.7–13.8: сканирование v ≤ {SCAN_SPEED_MAX_MM_S} мм/с, '
        f'шаг ≤ {EMA_SCAN_STEP_MAX_MM} мм; шаг при отсутствии указаний — приложение В.'
    )))

    chunks.append(('appendix_v', (
        f'{DOCUMENT_CODE}, приложение В: определение шага ЭМАП по {APPENDIX_V_SCAN_STEP["reference_sample"]}, '
        f'отверстие d={APPENDIX_V_SCAN_STEP["hole_d_mm"]} мм на {APPENDIX_V_SCAN_STEP["hole_depth_mm"]} мм; '
        f'{APPENDIX_V_SCAN_STEP["max_scan_step_rule"]}.'
    )))

    chunks.append(('corrosion', (
        f'{DOCUMENT_CODE}, п. 13.10: коррозия/эрозия — шаг ≤ {CORROSION_SCAN_STEP_MAX_MM} мм; '
        f'мин. t — минимальное показание; язва d до {CORROSION_PROBE_RULES["min_pit_diameter_detect_mm"]} мм '
        f'может не фиксироваться (п. 13.10.11).'
    )))

    chunks.append(('corrosion_probe', (
        f'{DOCUMENT_CODE}, п. 13.10.4: ≥ {CORROSION_PROBE_RULES["wavelength_coverage_min"]} λ на толщину; '
        f't≥10 мм — {CORROSION_PROBE_RULES["thickness_ge_10_mm"]}; t<10 мм — {CORROSION_PROBE_RULES["thickness_lt_10_mm"]}.'
    )))

    chunks.append(('acceptance_rule', (
        f'{DOCUMENT_CODE}, п. 11.8: годность если погрешность ≤ {THICKNESS_ERROR_LIMITS["acceptance_vs_tolerance_pct"]} % '
        f'половины интервала допуска (или согласованных пределов в КД).'
    )))

    chunks.append(('tech_card', (
        f'{DOCUMENT_CODE}, приложение Б: ТКК/ТИ — ' + '; '.join(TECH_CARD_REQUIRED_ITEMS[:4]) + '; …'
    )))

    chunks.append(('group_tkk', (
        f'{DOCUMENT_CODE}, п. 12.2.5: одна ТКК на несколько ОК — одна марка, Δt ≤ '
        f'{GROUP_TKK_CONDITIONS["thickness_deviation_max_pct"]} %, одинаковая подготовка поверхности.'
    )))

    chunks.append(('recording', (
        f'{DOCUMENT_CODE}, раздел 14: журнал по [2]–[5]; заключение по [2]–[5]; '
        f'рекомендуемая форма — приложение Г (для заключения) / В (таблица результатов).'
    )))

    chunks.append(('metrology', (
        f'{DOCUMENT_CODE}, раздел 15: метrologия по [12],[13] и {METROLOGY_STANDARD}; '
        f'СИ — утверждённый тип и поверка; НО — аттестация при отнесении к АО.'
    )))

    chunks.append(('discrete_procedure', (
        f'{DOCUMENT_CODE}, п. 13.3.2: одно измерение; при грубой ошибке — три и среднее; '
        f'РСП: экран ⊥ образующей трубы (п. 13.3.3); амплитуды эхо ±{ECHO_AMPLITUDE_MATCH_DB} дБ.'
    )))

    chunks.append(('water_filled', (
        f'{DOCUMENT_CODE}, п. 8.3: допускается измерение через воду в заполненном ОК.'
    )))

    chunks.append(('coating_measure', (
        f'{DOCUMENT_CODE}, п. 12.3.3: через плотную оксидную плёнку или тонкий ЛКП — '
        f'способ 7.1б и СИ с функцией измерения через покрытие; проверить экспериментально.'
    )))

    chunks.append(('pit_detection', (
        f'{DOCUMENT_CODE}, п. 13.10.6–13.10.10: язвенная коррозия — РСП с фокусом на глубину язвы; '
        f'45° НП для отличия включений; только первый донный эхo при поиске точечной коррозии.'
    )))

    chunks.append(('formula_errors', (
        f'{DOCUMENT_CODE}, п. 9.6: δ_толщиномер = {THICKNESS_METER_ERROR_FORMULA}; '
        f'δ_дефектоскоп = {DEFECTOSCOPE_ERROR_FORMULA}.'
    )))

    return chunks
