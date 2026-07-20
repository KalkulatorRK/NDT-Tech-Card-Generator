"""
Данные ГОСТ Р 50.05.04-2022 «Система оценки соответствия в области
использования атомной энергии. Оценка соответствия в форме контроля.
Унифицированные методики. Ультразвуковой контроль сварных соединений
из стали аустенитного класса».

Модуль содержит структурированные требования для ИИ-консультанта и
справочных вызовов по УЗК аустенитных сварных соединений (УЗК-А):
- область применения и ограничения;
- термины, сокращения, уровни чувствительности;
- параметры ПЭП (табл. 1), БЦО в НО (табл. 2), области H/R (табл. В.1);
- степени контроледоступности, контролепригодности;
- условия проведения, подготовка поверхности, сканирование;
- требования к персоналу, ТКК/ТИ, отчётности.

Источник: ГОСТ Р 50.05.04-2022 (дата введения 2023-03-01; заменяет
ГОСТ Р 50.05.04-2018; применяется с 01.01.2024).

ВАЖНО: при изменении стандарта актуализировать этот модуль по тексту НД.
"""

from __future__ import annotations

from typing import Optional

# ------------------------------------------------------------------
# Идентификатор документа
# ------------------------------------------------------------------
DOCUMENT_CODE = 'ГОСТ Р 50.05.04-2022'
DOCUMENT_SHORT = 'ГОСТ Р 50.05.04'
DOCUMENT_FULL_NAME = (
    'ГОСТ Р 50.05.04-2022 «Система оценки соответствия в области использования '
    'атомной энергии. Оценка соответствия в форме контроля. Унифицированные '
    'методики. Ультразвуковой контроль сварных соединений из стали аустенитного '
    'класса»'
)
DOCUMENT_EFFECTIVE_FROM = '2023-03-01'
DOCUMENT_APPLIES_FROM = '2024-01-01'
DOCUMENT_REPLACES = 'ГОСТ Р 50.05.04-2018'
METHOD_CODE = 'УЗК-А'
METHOD_NAME = 'ультразвуковой контроль сварных соединений из аустенитных сталей'
METHOD_NAME_EN = 'Ultrasonic examination of austenitic steel welded joints'

PERSONNEL_STANDARD = 'ГОСТ Р 50.05.11'
NO_STANDARD = 'ГОСТ Р 50.05.14'
METROLOGY_STANDARD = 'ГОСТ Р 50.05.16'

# ------------------------------------------------------------------
# Область применения (п. 5.1.1)
# ------------------------------------------------------------------
SCOPE_THICKNESS_MIN_MM = 5.5
SCOPE_THICKNESS_MAX_MM = 100.0
SCOPE_CURVATURE_LONGITUDINAL_MIN_MM = 100.0
SCOPE_CURVATURE_CIRCUMFERENTIAL_MIN_MM = 25.0
SCOPE_INNER_DIAMETER_UT_MIN_MM = 800.0

SCOPE_EXCLUDED = (
    'литые изделия',
    'угловые и тавровые сварные соединения',
    'несплошности, ориентированные поперёк оси АСС',
    'определение размеров, формы и ориентации несплошностей',
)

WELDING_PROCESSES_ALLOWED = (
    'электродуговая сварка',
    'аргонодуговая сварка',
    'комбинированная (электродуговая и аргонодуговая) сварка',
)

# ------------------------------------------------------------------
# Термины (раздел 3)
# ------------------------------------------------------------------
TERMS = {
    '3.1': {
        'term': 'браковочный уровень чувствительности',
        'definition': (
            'Уровень чувствительности, при превышении которого выявленная несплошность '
            'относится к дефекту ([2], приложение N 2).'
        ),
    },
    '3.2': {
        'term': 'контрольный уровень чувствительности (уровень фиксации)',
        'definition': (
            'Уровень чувствительности, при котором производят регистрацию несплошностей '
            'и оценку их допустимости по условным размерам и количеству ([2], приложение N 2).'
        ),
    },
    '3.3': {
        'term': 'методика контроля',
        'definition': (
            'Документ, содержащий совокупность процедур, условий проведения и требований '
            'к средствам контроля, реализующих один или несколько способов контроля.'
        ),
    },
    '3.4': {
        'term': 'поисковый уровень чувствительности',
        'definition': (
            'Уровень чувствительности, устанавливаемый при поиске несплошностей '
            '(ГОСТ Р 55724-2013, п. 3.1.26).'
        ),
    },
    '3.5': {
        'term': 'структурные шумы',
        'definition': (
            'Многочисленные сигналы на экране дефектоскопа от переотражений на границах '
            'зёрен и структурных неоднородностей; амплитуда и местоположение хаотически '
            'меняются при перемещении ПЭП на 2–3 мм.'
        ),
    },
    '3.6': {
        'term': 'схема прозвучивания',
        'definition': (
            'Документально оформленный порядок сканирования сварного соединения '
            'пьезоэлектрическим(и) преобразователем(ями) для полного прозвучивания '
            'наплавленного металла с учётом возможных несплошностей и доступности.'
        ),
    },
    '3.7': {
        'term': 'технологическая инструкция по неразрушающему контролю',
        'short': 'ТИ',
        'definition': (
            'Документ, регламентирующий объёмы и технологию контроля на конкретном ОК '
            'по унифицированной методике, содержащий нормы оценки качества.'
        ),
    },
    '3.8': {
        'term': 'технологическая карта контроля',
        'short': 'ТКК',
        'definition': (
            'Производственная контрольная документация, регламентирующая средства, '
            'параметры, последовательность и содержание операций НК.'
        ),
    },
}

ABBREVIATIONS = {
    'АСС': 'аустенитные сварные соединения',
    'БЦО': 'боковой цилиндрический отражатель',
    'НО': 'настроечный образец',
    'ОК': 'объект контроля',
    'ПГВ': 'преобразователь головных волн',
    'ПДО': 'плоскодонный отражатель',
    'ПС': 'прямой совмещенный',
    'ПРС': 'прямой раздельно-совмещенный',
    'ПЭП': 'пьезоэлектрический преобразователь',
    'РС': 'раздельно-совмещенный',
    'ТИ': 'технологическая инструкция',
    'ТКК': 'технологическая карта контроля',
    'УЗ': 'ультразвуковой(ая)',
    'УЗК': 'ультразвуковой контроль',
    'DAC': 'зависимость амплитуды от расстояния (Distance-Amplitude Curve)',
}

ILLUMINANCE_MIN_LX = 500
AMBIENT_TEMP_MIN_C = 5
AMBIENT_TEMP_MAX_C = 40
VIBRATION_DUST_DISTANCE_MIN_M = 10
BRIGHT_LIGHT_SCREEN_DISTANCE_MIN_M = 15
MANUAL_UT_FORBIDDEN_HOURS = ('00:00', '06:00')
TEAM_SIZE_MIN = 2
TEAM_CONCLUSION_RIGHTS_MIN = 1

TABLE_1_PEP_BY_THICKNESS = [
    {
        'thickness_min_mm': 5.5,
        'thickness_max_mm': 10.0,
        'wave_types': ('поперечная',),
        'pep_types': ('совмещенный', 'РС'),
        'frequency_mhz_min': 4.0,
        'frequency_mhz_max': 5.0,
        'frequency_reduce_allowed_mhz': 2.5,
        'angles_direct_deg': (70, 72, 65, 70),
        'angles_reflected_deg': (65, 70),
    },
    {
        'thickness_min_mm': 10.0,
        'thickness_max_mm': 20.0,
        'wave_types': ('поперечная', 'продольная', 'головная'),
        'pep_types': ('совмещенный', 'РС'),
        'frequency_mhz_min': 2.5,
        'frequency_mhz_max': 5.0,
        'pgv_frequency_mhz': 1.8,
        'angles_direct_deg': (60, 65),
        'angles_reflected_deg': (60, 65, 70),
    },
    {
        'thickness_min_mm': 20.0,
        'thickness_max_mm': 40.0,
        'wave_types': ('продольная',),
        'pep_types': ('совмещенный', 'РС'),
        'frequency_mhz_min': 1.5,
        'frequency_mhz_max': 2.5,
        'angles_direct_deg': (55, 60, 65),
        'angles_reflected_deg': None,
        'angles_reflected_note': 'не допускается',
    },
    {
        'thickness_min_mm': 40.0,
        'thickness_max_mm': 100.0,
        'wave_types': ('продольная',),
        'pep_types': ('РС',),
        'frequency_mhz_min': 0.8,
        'frequency_mhz_max': 2.5,
        'angles_direct_deg': (40, 45),
        'angles_reflected_deg': (55, 60, 65),
    },
]

PEP_ANGLE_TOLERANCE_DEG = 2.0
PEP_STANDARD = 'ГОСТ Р 55725'
DIRECT_PEP_RS_MAX_THICKNESS_MM = 40.0
PGV_LAYER_MIN_MM = 1.0
PGV_LAYER_MAX_MM = 15.0
PGV_MIN_THICKNESS_MM = 20.0
PGV_FREQUENCY_MHZ = 1.8
PGV_BCO_DEPTH_MM = 7.0
PGV_BCO_DEPTH_TOLERANCE_MM = 0.2

TABLE_2_BCO_IN_NO = [
    {'thickness_min_mm': 5.5, 'thickness_max_mm': 10.0, 'bco_diameter_mm': 2,
     'depths_center': ('H/2',), 'depths_fusion_line': ('H/2',)},
    {'thickness_min_mm': 10.0, 'thickness_max_mm': 20.0, 'bco_diameter_mm': 3,
     'depths_center': ('H/3', '2H/3'), 'depths_fusion_line': ('H/3', '2H/3')},
    {'thickness_min_mm': 20.0, 'thickness_max_mm': 40.0, 'bco_diameter_mm': 4,
     'depths_center': ('H/4', 'H/2', '3H/4'), 'depths_fusion_line': ('H/4', 'H/2', '3H/4')},
    {'thickness_min_mm': 40.0, 'thickness_max_mm': 100.0, 'bco_diameter_mm': 5,
     'depths_center': ('H/5', '2H/5', '3H/5', '4H/5'),
     'depths_fusion_line': ('H/5', '2H/5', '3H/5', '4H/5')},
]

NO_MIN_WIDTH_MM = 60

SENSITIVITY_LEVELS_DB = {
    'браковочный': {'offset_db': 0},
    'контрольный': {'offset_db': 6},
    'поисковый': {'offset_db': 12},
}

STROBE_HEIGHT_PERCENT = (50, 80)
STROBE_WIDTH_PERCENT = (70, 80)
SCAN_SPEED_MAX_MM_S = 50
SCAN_STEP_MAX_FRACTION_PIEZO = 0.5
PEP_ROTATION_DEG_RANGE = (10, 15)

SURFACE_ROUGHNESS_RA_MAX = 6.3
SURFACE_ROUGHNESS_RZ_MAX = 40.0
BOTTOM_SURFACE_RA_MAX = 20.0
BOTTOM_SURFACE_RZ_MAX = 80.0
SURFACE_GAP_MAX_MM = 0.2
REINFORCEMENT_REMOVAL_MIN_THICKNESS_MM = 20.0
REINFORCEMENT_REMOVAL_MIN_DIAMETER_MM = 350.0

ACCESSIBILITY_GRADES = {
    '1С': 'центральный луч пересекает каждую точку сечения в трёх и более направлениях',
    '2С': 'в двух и более направлениях',
    '3С': 'в одном и более направлениях',
    '4С': 'частично или полностью не выполняется прозвучивание по направлениям для 1С',
}
ACCESSIBILITY_ANGLE_DIFF_MIN_DEG = 35

TESTABILITY_SIGNAL_NOISE_MIN_DB = 6
TESTABILITY_ANGLE_DIFF_MAX_DEG = 5
TESTABILITY_REFLECTOR_SIZES_MM = {'initial': (2.0, 1.0), 'increased': (3.0, 1.5)}

MEASUREMENT_TOLERANCE = {
    'amplitude_db': 2.0,
    'equivalent_area_percent': 50.0,
    'conditional_length_mm_thin': 5.0,
    'conditional_length_mm_thick': 10.0,
    'conditional_length_thickness_boundary_mm': 200.0,
    'comparison_factor': 1.41,
}
DISCONTINUITY_SEPARATION_DB = 6
SETUP_CHECK_INTERVAL_H = 2

TABLE_V1_HR_REGIONS = [
    {'angle_deg': 40, 'region_a': (0, 0.188), 'region_b': (0.188, 0.375), 'region_c_min': 0.375},
    {'angle_deg': 45, 'region_a': (0, 0.140), 'region_b': (0.140, 0.293), 'region_c_min': 0.293},
    {'angle_deg': 50, 'region_a': (0, 0.104), 'region_b': (0.104, 0.234), 'region_c_min': 0.234},
    {'angle_deg': 60, 'region_a': (0, 0.052), 'region_b': (0.052, 0.134), 'region_c_min': 0.134},
    {'angle_deg': 65, 'region_a': (0, 0.035), 'region_b': (0.036, 0.094), 'region_c_min': 0.094},
    {'angle_deg': 68, 'region_a': (0, 0.026), 'region_b': (0.026, 0.073), 'region_c_min': 0.073},
    {'angle_deg': 70, 'region_a': (0, 0.021), 'region_b': (0.021, 0.060), 'region_c_min': 0.060},
    {'angle_deg': 72, 'region_a': (0, 0.017), 'region_b': (0.017, 0.049), 'region_c_min': 0.049},
]

TECH_CARD_REQUIRED_ITEMS = (
    'идентификация АСС',
    'документация по контролю и нормы оценки',
    'исходные данные для параметров УЗК',
    'аппаратура, ПЭП, КО, НО',
    'схемы прозвучивания и сканирования',
    'подготовка поверхности и разметка',
    'проверка контролепригодности',
    'параметры контроля и оценка качества',
    'требования к отчётной документации',
)


def get_term(paragraph: str) -> Optional[dict]:
    return TERMS.get((paragraph or '').strip()) if paragraph else None


def _match_thickness_row(thickness_mm: float, table: list) -> Optional[dict]:
    if thickness_mm is None:
        return None
    for row in table:
        if row['thickness_min_mm'] <= thickness_mm <= row['thickness_max_mm']:
            return row
    return None


def get_table1_row(thickness_mm: float) -> Optional[dict]:
    """Строка табл. 1 по номинальной толщине, мм."""
    return _match_thickness_row(thickness_mm, TABLE_1_PEP_BY_THICKNESS)


def get_table2_bco(thickness_mm: float) -> Optional[dict]:
    """Строка табл. 2 — БЦО в НО."""
    return _match_thickness_row(thickness_mm, TABLE_2_BCO_IN_NO)


def get_accessibility_grade_info(code: str) -> Optional[str]:
    if not code:
        return None
    return ACCESSIBILITY_GRADES.get(code.strip().upper().replace('C', 'С'))


def is_ambient_ok(temp_c: float) -> bool:
    return AMBIENT_TEMP_MIN_C <= temp_c <= AMBIENT_TEMP_MAX_C


def is_in_scope(thickness_mm: float) -> bool:
    return SCOPE_THICKNESS_MIN_MM <= thickness_mm <= SCOPE_THICKNESS_MAX_MM


def format_scope() -> str:
    procs = ', '.join(WELDING_PROCESSES_ALLOWED)
    excl = '; '.join(SCOPE_EXCLUDED)
    return (
        f'{DOCUMENT_CODE}, п. 5.1.1: УЗК стыковых АСС толщиной '
        f'{SCOPE_THICKNESS_MIN_MM}–{SCOPE_THICKNESS_MAX_MM} мм; радиусы кривизны ≥ '
        f'{SCOPE_CURVATURE_LONGITUDINAL_MIN_MM} мм (продольные) и ≥ '
        f'{SCOPE_CURVATURE_CIRCUMFERENTIAL_MIN_MM} мм (кольцевые); без подкладных колец '
        f'({procs}, полное проплавление корня). Не распространяется: {excl}. '
        f'п. 5.1.6: эхо-импульсный метод, прямой и однократно отражённый лучи.'
    )


def format_ambient_rules() -> str:
    return (
        f'{DOCUMENT_CODE}, п. 5.2.4: освещённость ≥ {ILLUMINANCE_MIN_LX} лк. '
        f'п. 5.2.7: t = {AMBIENT_TEMP_MIN_C}–{AMBIENT_TEMP_MAX_C} °C. '
        f'п. 5.1.10: ручной УЗК без записи {MANUAL_UT_FORBIDDEN_HOURS[0]}–'
        f'{MANUAL_UT_FORBIDDEN_HOURS[1]} запрещён. п. 5.2.9: ≥ {TEAM_SIZE_MIN} '
        f'специалистов, ≥ {TEAM_CONCLUSION_RIGHTS_MIN} с правом заключения.'
    )


def format_table1() -> str:
    lines = [f'{DOCUMENT_CODE}, таблица 1 — параметры наклонных ПЭП:']
    for row in TABLE_1_PEP_BY_THICKNESS:
        ang_r = (
            ', '.join(str(a) for a in row['angles_reflected_deg'])
            if row.get('angles_reflected_deg')
            else row.get('angles_reflected_note', '—')
        )
        lines.append(
            f'  {row["thickness_min_mm"]}–{row["thickness_max_mm"]} мм: '
            f'{", ".join(row["wave_types"])}, {", ".join(row["pep_types"])}, '
            f'{row["frequency_mhz_min"]}–{row["frequency_mhz_max"]} МГц, '
            f'углы {", ".join(str(a) for a in row["angles_direct_deg"])}° / {ang_r}.'
        )
    return ' '.join(lines) + f' Отклонение угла ±{PEP_ANGLE_TOLERANCE_DEG}°.'


def format_table2() -> str:
    lines = [f'{DOCUMENT_CODE}, таблица 2 — БЦО в НО:']
    for row in TABLE_2_BCO_IN_NO:
        lines.append(
            f'  {row["thickness_min_mm"]}–{row["thickness_max_mm"]} мм: Ø{row["bco_diameter_mm"]} мм, '
            f'центр {", ".join(row["depths_center"])}, сплавление {", ".join(row["depths_fusion_line"])}.'
        )
    return ' '.join(lines)


def format_sensitivity_levels() -> str:
    return (
        f'{DOCUMENT_CODE}, п. 9.3.5.3: контрольный +{SENSITIVITY_LEVELS_DB["контрольный"]["offset_db"]} дБ '
        f'к браковочному; поисковый +{SENSITIVITY_LEVELS_DB["контрольный"]["offset_db"]} дБ к контрольному.'
    )


def format_surface_preparation() -> str:
    return (
        f'{DOCUMENT_CODE}, п. 6.3.6: Ra ≤ {SURFACE_ROUGHNESS_RA_MAX} (Rz {SURFACE_ROUGHNESS_RZ_MAX}); '
        f'донная Ra ≤ {BOTTOM_SURFACE_RA_MAX}. Зазор ≤ {SURFACE_GAP_MAX_MM} мм.'
    )


def format_scanning_rules() -> str:
    return (
        f'{DOCUMENT_CODE}, п. 9.4.8–9.4.9: скорость ≤ {SCAN_SPEED_MAX_MM_S} мм/с; '
        f'шаг ≤ 1/2 диаметра пьезоэлемента.'
    )


def format_testability() -> str:
    w0, h0 = TESTABILITY_REFLECTOR_SIZES_MM['initial']
    return (
        f'{DOCUMENT_CODE}, прил. А: сигнал/шум ≥ {TESTABILITY_SIGNAL_NOISE_MIN_DB} дБ; '
        f'разность углов > {TESTABILITY_ANGLE_DIFF_MAX_DEG}° — неконтролепригодно; '
        f'отражатель {w0}×{h0} мм (t 5,5–10 мм).'
    )


def format_accessibility() -> str:
    parts = [f'{DOCUMENT_CODE}, п. 6.3.3:']
    for code, desc in ACCESSIBILITY_GRADES.items():
        parts.append(f'{code} — {desc};')
    return ' '.join(parts)


def format_personnel() -> str:
    return f'{DOCUMENT_CODE}, раздел 8: персонал по {PERSONNEL_STANDARD}; ТИ/ТКК — СПВЗ или СПА (п. 5.3.2).'


def format_measurement_tolerances() -> str:
    t = MEASUREMENT_TOLERANCE
    return (
        f'{DOCUMENT_CODE}, п. 9.5.1.6: ±{t["amplitude_db"]} дБ; ±{t["equivalent_area_percent"]} % площади; '
        f'протяжённость ±{t["conditional_length_mm_thin"]}/{t["conditional_length_mm_thick"]} мм.'
    )


def all_kb_chunks() -> list[tuple[str, str]]:
    chunks = [
        ('п. 5.1.1 область применения', format_scope()),
        ('п. 5.2 условия УЗК', format_ambient_rules()),
        ('таблица 1 ПЭП', format_table1()),
        ('таблица 2 БЦО', format_table2()),
        ('п. 9.3.5.3 чувствительность', format_sensitivity_levels()),
        ('п. 6.3.6 подготовка поверхности', format_surface_preparation()),
        ('п. 9.4.8–9.4.9 сканирование', format_scanning_rules()),
        ('п. 6.3.3 контроледоступность', format_accessibility()),
        ('приложение А контролепригодность', format_testability()),
        ('раздел 8 персонал', format_personnel()),
        ('п. 9.5.1.6 погрешности', format_measurement_tolerances()),
    ]
    for para, row in TERMS.items():
        chunks.append((f'п. {para} {row["term"]}', f'{DOCUMENT_CODE}, п. {para}: {row["definition"]}'))
    for row in TABLE_V1_HR_REGIONS:
        chunks.append((
            f'табл. В.1 {row["angle_deg"]}°',
            f'{DOCUMENT_CODE}, табл. В.1, {row["angle_deg"]}°: A {row["region_a"]}, B {row["region_b"]}, V>{row["region_c_min"]}.',
        ))
    return chunks
