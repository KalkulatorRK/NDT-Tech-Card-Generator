"""
Расчётные модули для радиографического контроля.

Содержит Python-порт расчётной логики из приложения KalkulatorRK2
(https://github.com/KalkulatorRK/KalkulatorRK2).

Реализованы расчёты по:
  - ГОСТ 7512-82 «Контроль неразрушающий. Сварные соединения. Радиографический метод»
  - ГОСТ Р 50.05.07-2018 «Радиографический контроль. АЭУ»

Расчёты:
  1. Параметры просвечивания (f, N, L) для всех схем 4.6, 5a, 5б, 5в, 5г, 5д, 5е, 5ж, 5и
  2. Активность радиоизотопных источников (Ir-192, Se-75)
  3. Геометрическая нерезкость
"""

import math
from typing import Optional


# Допустимые значения объёма выборочного контроля (НП-105-18, п. 70)
CONTROL_VOLUME_OPTIONS = (100, 50, 25, 10, 5)
# Порог диаметра для полного контроля кольцевых швов (НП-105-18, п. 72)
RING_FULL_LENGTH_DIAMETER_MM = 250.0


# ------------------------------------------------------------------
# Таблицы из ГОСТ 7512-82 / ГОСТ Р 50.05.07-2018
# ------------------------------------------------------------------

# Таблица для схемы 5а: {m: {N: коэффициент}}
# m = d/D (отношение внутреннего диаметра к наружному)
# N — количество экспозиций
TABLE_DATA_5A = {
    0.50: {10: 14.2, 9: 3.3},
    0.55: {8: 27.3, 9: 3.4, 10: 1.8},
    0.60: {8: 4.2, 9: 1.9, 10: 1.2},
    0.65: {7: 7.7, 8: 2.2, 9: 1.3, 10: 0.9},
    0.70: {7: 3.1, 8: 1.5, 9: 1.0, 10: 0.7},
    0.75: {6: 7.1, 7: 1.9, 8: 1.1, 9: 0.8, 10: 0.6},
    0.80: {6: 3.2, 7: 1.4, 8: 0.9, 9: 0.7, 10: 0.5},
    0.85: {5: 18.2, 6: 2.0, 7: 1.0, 8: 0.7, 9: 0.5, 10: 0.4},
    0.90: {5: 4.7, 6: 1.5, 7: 0.8, 8: 0.6, 9: 0.5, 10: 0.4},
    0.95: {5: 2.6, 6: 1.1, 7: 0.7, 8: 0.5, 9: 0.4, 10: 0.3},
}

# Таблица для схемы 5б: {m: {N: коэффициент или None}}
TABLE_DATA_5B = {
    0.40: {8: 10.4, 9: 3.2, 10: 2.0},
    0.45: {7: 18.2, 8: 3.3, 9: 2.0},
    0.50: {7: 3.8, 8: 2.2, 9: 2.0},
    0.55: {6: 6.9, 7: 2.8, 8: 2.0},
    0.60: {6: 4.0, 7: 2.0},
    0.65: {6: 2.5, 7: 2.0},
    0.70: {5: 9.8, 6: 2.0},
    0.75: {5: 4.3, 6: 2.0},
    0.80: {5: 3.0, 6: 2.0},
    0.85: {5: 2.3, 6: 2.0},
    0.90: {5: 2.0},
    0.95: {4: 18.3, 5: 2.0},
}

# Таблица для схемы 5г: {m: {n: [оператор_сравнения, предел]}}
TABLE_DATA_5G = {
    0.50: {4: ("≤", 0.4), 5: ("≤", 1.4), 6: ("≤", 12.0), 7: (">", 12.0)},
    0.55: {4: ("≤", 0.6), 5: ("≤", 2.6), 6: (">", 2.6)},
    0.60: {3: ("≤", 0.1), 4: ("≤", 0.9), 5: ("≤", 5.8), 6: (">", 5.8)},
    0.65: {3: ("≤", 0.2), 4: ("≤", 1.3), 5: ("≤", 40.0), 6: (">", 40.0)},
    0.70: {3: ("≤", 0.3), 4: ("≤", 1.9), 5: (">", 1.9)},
    0.75: {3: ("≤", 0.4), 4: ("≤", 3.0), 5: (">", 3.0)},
    0.80: {3: ("≤", 0.5), 4: ("≤", 4.7), 5: (">", 4.7)},
    0.85: {3: ("≤", 0.6), 4: ("≤", 9.8), 5: (">", 9.8)},
    0.90: {3: ("≤", 1.0), 4: (">", 1.0)},
}

# Описание схем просвечивания (пользовательские названия по чертежам ГОСТ)
SCHEME_INFO = {
    '4_6': {
        'name': 'Чертёж 2',
        'description': 'Плоские детали, листы, обечайки.',
        'image': 'img/scheme_4_6.png',
        'requires_diameters': False,
        'requires_thickness': True,
        'for_pipes': False,
    },
    '5a': {
        'name': 'Чертёж 3а',
        'description': 'Трубопровод Dн > 50 мм. Плёнка внутри трубы.',
        'image': 'img/scheme_5a.png',
        'requires_diameters': True,
        'requires_thickness': False,
        'for_pipes': True,
    },
    '5b': {
        'name': 'Чертёж 3б',
        'description': 'Трубопровод Dн > 50 мм. Плёнка внутри трубы.',
        'image': 'img/scheme_5b.png',
        'requires_diameters': True,
        'requires_thickness': False,
        'requires_film_length': True,
        'for_pipes': True,
    },
    '5v': {
        'name': 'Чертёж 3в',
        'description': 'Трубопровод Dн ≤ 100 мм. Плёнка снаружи.',
        'image': 'img/scheme_5v.png',
        'requires_diameters': True,
        'requires_thickness': False,
        'for_pipes': True,
    },
    '5g': {
        'name': 'Чертёж 3г',
        'description': 'Трубопровод Dн > 50 мм. Плёнка снаружи.',
        'image': 'img/scheme_5g.png',
        'docx_image': 'img/scheme_5g_docx.jpg',
        'requires_diameters': True,
        'requires_thickness': False,
        'for_pipes': True,
    },
    '5d': {
        'name': 'Чертёж 3д',
        'description': 'Трубопровод Dн > 50 мм. Плёнка снаружи.',
        'image': 'img/scheme_5d.png',
        'requires_diameters': True,
        'requires_thickness': False,
        'for_pipes': True,
    },
    '5zh': {
        'name': 'Чертёж 3ж',
        'description': 'Трубопровод Dн ≤ 2000 мм. Панорамное просвечивание.',
        'image': 'img/scheme_5zh.png',
        'requires_diameters': True,
        'requires_thickness': False,
        'for_pipes': True,
    },
    '5z': {
        'name': 'Чертёж 3и',
        'description': 'Трубопровод Dн > 2000 мм. Плёнка снаружи.',
        'image': 'img/scheme_5z.png',
        'requires_diameters': True,
        'requires_thickness': False,
        'for_pipes': True,
    },
    '5e': {
        'name': 'Чертёж 3е',
        'description': 'Специальная схема просвечивания.',
        'image': 'img/scheme_5e.png',
        'requires_diameters': True,
        'requires_thickness': False,
        'for_pipes': True,
    },
}

# Количество стенок, через которые проходит излучение, и позиция детектора
# Ключи: код схемы → (wall_count, source_position, film_position)
# По описанию пользователя:
#   Схемы 3а, 3б (5a, 5b): источник снаружи, плёнка ВНУТРИ — 1 стенка
#   Схемы 3в, 3г, 3д (5v, 5g, 5d): источник снаружи, плёнка СНАРУЖИ — 2 стенки
#   Панорамные (5zh, 5z): источник внутри на оси — 1 стенка
SCHEME_WALL_COUNT = {
    '4_6': 1,    # Плоские детали: 1 стенка
    '5a':  1,    # 3а: источник снаружи, плёнка внутри — 1 стенка
    '5b':  1,    # 3б: источник снаружи, плёнка внутри (эллипс) — 1 стенка
    '5v':  2,    # 3в: оба снаружи — 2 стенки
    '5g':  2,    # 3г: оба снаружи — 2 стенки
    '5d':  2,    # 3д: оба снаружи — 2 стенки
    '5zh': 1,    # 3ж: панорамный (источник по оси) — 1 стенка
    '5z':  1,    # 3и: источник внутри — 1 стенка
    '5e':  1,    # 3е: 1 стенка
}

# Обновляем SCHEME_INFO полем wall_count
for _code, _walls in SCHEME_WALL_COUNT.items():
    if _code in SCHEME_INFO:
        SCHEME_INFO[_code]['wall_count'] = _walls


def effective_outer_diameter_mm(
    nominal_d_mm: float,
    g_max_mm: float,
    scheme_code: str,
) -> float:
    """
    Эффективный наружный диаметр D для расчёта расстояния f.

    При просвечивании через две стенки (схемы 5в, 5г, 5д):
        D = Dн + g_max + g_max
    """
    d_nom = float(nominal_d_mm or 0)
    if d_nom <= 0:
        return 0.0
    if SCHEME_WALL_COUNT.get(scheme_code, 1) == 2:
        return round(d_nom + 2 * float(g_max_mm or 0), 1)
    return round(d_nom, 1)


def clamp_f_mm(value) -> Optional[float]:
    """
    Нормализует расстояние f для техкарты: отрицательные значения → 0 мм.
    """
    if value is None or value == '':
        return None
    try:
        return max(0.0, round(float(value), 1))
    except (TypeError, ValueError):
        return None


def calc_radiation_thickness(
    wall_thickness_mm: float,
    g_min_mm: float,
    g_max_mm: float,
    scheme_code: str,
    backing_thickness_mm: float = 0.0,
) -> dict:
    """
    Рассчитывает радиационную толщину для заданной схемы просвечивания.

    По НП-105-18, п. 46 / Табл. 4.8, для определения K:
        S_K = S + g_min + Sпк   (одна стенка, Sпк — толщина подкладки/кольца)
        S_K = S + S             (две стенки)

    По ГОСТ Р 50.05.07-2018 (раздел 6.3.5) для расчёта f применяется g_max
    с учётом числа просвечиваемых стенок:
        S_рад(f) = S + g_max (1 стенка) или 2S + 2g_max (2 стенки)

    :param wall_thickness_mm: толщина стенки S, мм
    :param g_min_mm: наименьшая допустимая высота валика шва, мм
    :param g_max_mm: наибольшая допустимая высота валика шва, мм
    :param scheme_code: код схемы просвечивания
    :param backing_thickness_mm: толщина подкладки Sпк, мм (0 если нет)
    :return: словарь с S_rad_K, S_rad_f и формулами
    """
    walls = SCHEME_WALL_COUNT.get(scheme_code, 1)
    s_pk = max(0.0, float(backing_thickness_mm or 0))

    if walls == 2:
        s_rad_k = 2 * wall_thickness_mm
        formula_k = f'{wall_thickness_mm} + {wall_thickness_mm} = {s_rad_k:.1f} мм'
        wall_desc = 'Две стенки'
    else:
        s_rad_k = wall_thickness_mm + g_min_mm + s_pk
        if s_pk > 0:
            formula_k = (
                f'{wall_thickness_mm} + {g_min_mm:.1f} + {s_pk:.1f} '
                f'= {s_rad_k:.1f} мм'
            )
        else:
            formula_k = f'{wall_thickness_mm} + {g_min_mm:.1f} = {s_rad_k:.1f} мм'
        wall_desc = 'Одна стенка'

    if walls == 2:
        s_rad_f = 2 * wall_thickness_mm + 2 * g_max_mm
        formula_f = f'2×{wall_thickness_mm} + 2×{g_max_mm:.1f} = {s_rad_f:.1f} мм'
    else:
        s_rad_f = wall_thickness_mm + g_max_mm
        formula_f = f'{wall_thickness_mm} + {g_max_mm:.1f} = {s_rad_f:.1f} мм'

    return {
        'wall_count': walls,
        'wall_desc': wall_desc,
        's_rad_k_mm': round(s_rad_k, 1),
        's_rad_f_mm': round(s_rad_f, 1),
        'backing_thickness_mm': round(s_pk, 1),
        'g_min_mm': g_min_mm,
        'g_max_mm': g_max_mm,
        'formula_k': formula_k,
        'formula_f': formula_f,
    }


def resolve_table_b_thickness_mm(
    wall_thickness_mm: float,
    scheme_code: str,
    joint_code: str = '',
    welding_method: str = '30',
) -> dict:
    """
    Радиационная толщина для подбора источника и плёнки по табл. Б.1–Б.3.

    Используется S_рад(f) — путь излучения через металл с учётом числа стенок
    и наибольшего усиления шва (g_max).
    """
    from normative.gost_59023_2 import get_inspection_zone

    zone = get_inspection_zone(joint_code, wall_thickness_mm, welding_method)
    rad = calc_radiation_thickness(
        wall_thickness_mm,
        zone.get('g_min_mm',  0.5),
        zone.get('g_max_mm', 3.5),
        scheme_code,
        zone.get('backing_thickness_mm', 0.0),
    )
    rad['table_b_thickness_mm'] = rad['s_rad_f_mm']
    return rad

def _get_C(focal_spot_mm: float, sensitivity_mm: float) -> float:
    """
    Вспомогательный коэффициент C = 2Φ/K, но не менее 4.

    :param focal_spot_mm: размер фокусного пятна Φ, мм
    :param sensitivity_mm: требуемая чувствительность K, мм
    :return: коэффициент C
    """
    return max(2 * focal_spot_mm / sensitivity_mm, 4.0)


def calc_scheme_4_6(focal_spot_mm: float, thickness_mm: float,
                     sensitivity_mm: float) -> dict:
    """
    Расчёт параметров просвечивания для схемы 4.6 (плоские детали).

    Формула: f = C × s

    :param focal_spot_mm: размер фокусного пятна Φ, мм
    :param thickness_mm: радиационная толщина s, мм
    :param sensitivity_mm: требуемая чувствительность K, мм
    :return: словарь с результатами расчёта
    """
    C = _get_C(focal_spot_mm, sensitivity_mm)
    f = C * thickness_mm
    return {
        'scheme': '4_6',
        'C': round(C, 4),
        'f_min_mm': round(f, 1),
        'N': 1,
        'L_mm': None,
        'formula': f'f = C × s = {C:.2f} × {thickness_mm} = {f:.1f} мм',
        'notes': 'Одна экспозиция, кассета охватывает всю ширину контролируемой зоны.',
    }


def calc_scheme_5a(focal_spot_mm: float, d_outer_mm: float,
                    d_inner_mm: float, sensitivity_mm: float) -> dict:
    """
    Расчёт параметров для схемы 5а (трубопровод, источник снаружи, через 2 стенки).

    Формула: f = 0.7 × C × (1 - m) × D

    :param focal_spot_mm: размер фокусного пятна Φ, мм
    :param d_outer_mm: наружный диаметр D, мм
    :param d_inner_mm: внутренний диаметр d, мм
    :param sensitivity_mm: требуемая чувствительность K, мм
    :return: словарь с результатами расчёта
    """
    m = d_inner_mm / d_outer_mm
    C = _get_C(focal_spot_mm, sensitivity_mm)
    f = 0.7 * C * (1 - m) * d_outer_mm

    # Определяем N по таблице: минимальное N, при котором f/D ≥ порога
    m_rounded = round(m * 20) / 20
    n_table = TABLE_DATA_5A.get(m_rounded) or TABLE_DATA_5A.get(
        min(TABLE_DATA_5A.keys(), key=lambda k: abs(k - m))
    ) or {}
    f_over_d = f / d_outer_mm
    N_min = max(n_table.keys()) if n_table else 10
    for exposures, min_f_over_d in sorted(n_table.items(), key=lambda item: int(item[0])):
        if f_over_d >= min_f_over_d:
            N_min = int(exposures)
            break
    L = math.pi * d_outer_mm / N_min if N_min > 0 else None

    return {
        'scheme': '5a',
        'C': round(C, 4),
        'm': round(m, 4),
        'f_min_mm': round(f, 1),
        'N': N_min,
        'L_mm': round(L, 0) if L else None,
        'formula': (
            f'f = 0,7 × C × (1 - m) × D = '
            f'0,7 × {C:.2f} × (1 - {m:.4f}) × {d_outer_mm} = {f:.1f} мм'
        ),
        'notes': f'По Таблице ГОСТ для m={m:.2f}: N ≥ {N_min} экспозиций.',
    }


def calc_scheme_5v(focal_spot_mm: float, d_outer_mm: float,
                    d_inner_mm: float, sensitivity_mm: float) -> dict:
    """
    Расчёт параметров для схемы 5в (малый диаметр, источник снаружи).

    Формула: f = C × D

    Просветка «на эллипс»: соединение снимают за 2 экспозиции, но на одном
    снимке одновременно попадают 2 участка шва, поэтому
    L = D × π / 4 (длина участка за 1 экспозицию).

    :param focal_spot_mm: размер фокусного пятна Φ, мм
    :param d_outer_mm: наружный диаметр D, мм
    :param d_inner_mm: внутренний диаметр d, мм
    :param sensitivity_mm: требуемая чувствительность K, мм
    :return: словарь с результатами расчёта
    """
    C = _get_C(focal_spot_mm, sensitivity_mm)
    f = C * d_outer_mm
    N = 2
    N_segments = 4
    L = math.pi * d_outer_mm / 4 if d_outer_mm else None
    return {
        'scheme': '5v',
        'C': round(C, 4),
        'f_min_mm': round(f, 1),
        'N': N,
        'N_segments': N_segments,
        'L_mm': round(L, 1) if L else None,
        'formula': f'f = C × D = {C:.2f} × {d_outer_mm} = {f:.1f} мм',
        'L_formula': f'L = D × π / 4 = {d_outer_mm} × 3,14 / 4 = {L:.1f} мм',
        'notes': (
            '2 экспозиции под углом 90°. Просветка на эллипс: на одном снимке '
            'одновременно 2 участка шва, L = D×π/4.'
        ),
    }


def calc_scheme_5g(focal_spot_mm: float, d_outer_mm: float,
                    d_inner_mm: float, sensitivity_mm: float) -> dict:
    """
    Расчёт параметров для схемы 5г (источник внутри, смещён от оси).

    Формула: f = 0.5 × (1.5C(D - d) - D)

    :param focal_spot_mm: размер фокусного пятна Φ, мм
    :param d_outer_mm: наружный диаметр D, мм
    :param d_inner_mm: внутренний диаметр d, мм
    :param sensitivity_mm: требуемая чувствительность K, мм
    :return: словарь с результатами расчёта
    """
    C = _get_C(focal_spot_mm, sensitivity_mm)
    f = 0.5 * (1.5 * C * (d_outer_mm - d_inner_mm) - d_outer_mm)

    # N по таблице
    m = d_inner_mm / d_outer_mm
    m_rounded = round(m * 20) / 20
    table_m = min(TABLE_DATA_5G.keys(), key=lambda k: abs(k - m))
    n_table = TABLE_DATA_5G.get(table_m, {})
    N_min = min(n_table.keys()) if n_table else 4
    L = math.pi * d_outer_mm / N_min if N_min else None

    return {
        'scheme': '5g',
        'C': round(C, 4),
        'm': round(m, 4),
        'f_min_mm': round(f, 1),
        'N': N_min,
        'L_mm': round(L, 0) if L else None,
        'L_formula': (
            f'L = D × π / N = {d_outer_mm} × 3,14 / {N_min} = {L:.1f} мм'
            if L else ''
        ),
        'formula': (
            f'f = 0,5 × (1,5C(D - d) - D) = '
            f'0,5 × (1,5 × {C:.2f} × ({d_outer_mm} - {d_inner_mm}) - {d_outer_mm}) = {f:.1f} мм'
        ),
        'notes': f'По Таблице ГОСТ для m={m:.2f}: N ≥ {N_min} экспозиций.',
    }


def calc_scheme_5d(focal_spot_mm: float, d_outer_mm: float,
                    d_inner_mm: float, sensitivity_mm: float) -> dict:
    """
    Расчёт параметров для схемы 5д.

    Формула: f = 0.5 × (C × (1.4D - d) - D)
    """
    C = _get_C(focal_spot_mm, sensitivity_mm)
    f = 0.5 * (C * (1.4 * d_outer_mm - d_inner_mm) - d_outer_mm)
    m = d_inner_mm / d_outer_mm

    return {
        'scheme': '5d',
        'C': round(C, 4),
        'm': round(m, 4),
        'f_min_mm': round(f, 1),
        'N': 4,
        'L_mm': round(math.pi * d_outer_mm / 4, 0),
        'L_formula': (
            f'L = D × π / N = {d_outer_mm} × 3,14 / 4 = '
            f'{math.pi * d_outer_mm / 4:.1f} мм'
        ),
        'formula': (
            f'f = 0,5 × (C × (1,4D - d) - D) = '
            f'0,5 × ({C:.2f} × (1,4 × {d_outer_mm} - {d_inner_mm}) - {d_outer_mm}) = {f:.1f} мм'
        ),
        'notes': '',
    }


def calc_scheme_5zh(focal_spot_mm: float, d_outer_mm: float,
                     d_inner_mm: float, sensitivity_mm: float) -> dict:
    """
    Расчёт параметров для схемы 5ж (панорамный, источник на оси, D ≤ 2 м).

    ВАЖНО: По ГОСТ Р 50.05.07-2018, п. Г.5 для схемы на рисунке 3ж
    расстояние f и число экспозиций N определяются ОПЫТНЫМ ПУТЁМ
    с учётом требований настоящего стандарта.

    Расчётные значения приведены для справки (по методике ГОСТ 7512-82)
    и являются МИНИМАЛЬНЫМИ ориентировочными значениями.
    """
    m = d_inner_mm / d_outer_mm
    C = _get_C(focal_spot_mm, sensitivity_mm)
    f_min = 0.5 * C * (1 - m) * d_outer_mm

    # Проверяем, помещается ли источник
    if f_min > d_inner_mm:
        return {
            'scheme': '5zh',
            'is_empirical': True,
            'empirical_reason': (
                f'f_расч = {f_min:.1f} мм > d_вн = {d_inner_mm} мм — '
                'источник не помещается, параметры только опытным путём.'
            ),
            'error': None,
            'f_min_mm': None,
            'N': None,
        }

    # Вспомогательный коэффициент r
    numerator = 0.25 * (C ** 2) * (1 - m ** 2)
    denominator = (m ** 2) * (C + 1)
    r = math.sqrt(1 - numerator / denominator)

    optimal_N = float('inf')
    optimal_n = 1
    for n in range(1, 6):
        arg1 = r * m
        arg2 = r * m / (2 * n - m)
        if abs(arg1) > 1 or abs(arg2) > 1:
            continue
        angle1 = math.degrees(math.asin(arg1))
        angle2 = math.degrees(math.asin(arg2))
        N = 180 / (angle1 + angle2)
        N_rounded = math.ceil(N)
        if N_rounded < optimal_N:
            optimal_N = N_rounded
            optimal_n = n

    L = math.pi * d_outer_mm / optimal_N if optimal_N != float('inf') else None

    return {
        'scheme': '5zh',
        # --- ОПЫТНЫЙ ПУТЬ (обязательно по ГОСТ Р 50.05.07-2018 п. Г.5) ---
        'is_empirical': True,
        'empirical_reason': (
            'По ГОСТ Р 50.05.07-2018, п. Г.5: для схемы 3ж расстояние f '
            'и число экспозиций N определяются ОПЫТНЫМ ПУТЁМ. '
            'Расчётные значения — для справки.'
        ),
        # Расчётные значения (справочно, по ГОСТ 7512-82)
        'C': round(C, 4),
        'm': round(m, 4),
        'r': round(r, 4),
        'f_min_mm': round(f_min, 1),
        'N': optimal_N if optimal_N != float('inf') else '—',
        'L_mm': round(L, 0) if L else None,
        'formula': (
            f'f_справ ≥ {f_min:.1f} мм; r = {r:.4f}; N_справ ≥ {optimal_N}'
        ),
        'notes': (
            'По ГОСТ Р 50.05.07-2018, п. Г.5 — опытным путём. '
            'Расчёт по ГОСТ 7512-82 — ориентировочно.'
        ),
    }


def calc_scheme_5b_iterative(focal_spot_mm: float, d_outer_mm: float,
                              d_inner_mm: float, film_length_mm: float,
                              sensitivity_mm: float) -> dict:
    """
    Расчёт параметров для схемы 5б (источник снаружи, просвечивание через 1 стенку).

    По ГОСТ Р 50.05.07-2018, п. Г.5:
    - Если длина плёнки (l) < внутреннего диаметра (d_вн):
        f и N определяются ОПЫТНЫМ ПУТЁМ.
    - Если l >= d_вн: расчёт по формулам ГОСТ 7512-82, Прил. 4, п. 4.

    Формулы (для случая l >= d_вн):
      b = l/d
      C = max(2Φ/K, 4)
      f ≥ 0,5C(1 - m√(1 - b²))D
      q = b(2n + 1) / √((2n + 1 - m√(1 - b²))² + m²b²)
      N = 180° / (arcsin(qm) - arcsin(qm/(2n + 1)))
    """
    m = d_inner_mm / d_outer_mm
    C = _get_C(focal_spot_mm, sensitivity_mm)

    # --- Проверка по ГОСТ Р 50.05.07-2018 п. Г.5 ---
    if film_length_mm < d_inner_mm:
        # Длина плёнки меньше внутреннего диаметра → ОПЫТНЫМ ПУТЁМ
        # Формула из ГОСТ 7512-82 применима (b = l/d < 1), но результат
        # является расчётным ориентиром — итоговые параметры определяются опытно.
        empirical_prefix = (
            f'По ГОСТ Р 50.05.07-2018, п. Г.5: l = {film_length_mm:.0f} мм '
            f'< d_вн = {d_inner_mm:.1f} мм — '
            'f и N определяются ОПЫТНЫМ ПУТЁМ. '
            'Расчётные значения — для справки (ГОСТ 7512-82, Прил. 4).'
        )
        is_empirical = True
    elif film_length_mm >= d_inner_mm:
        # l >= d_вн: формула неприменима (b = l/d ≥ 1 → sqrt ошибка)
        return {
            'scheme': '5b',
            'is_empirical': True,
            'empirical_reason': (
                f'По ГОСТ Р 50.05.07-2018, п. Г.5: l = {film_length_mm:.0f} мм '
                f'>= d_вн = {d_inner_mm:.1f} мм — расчётная формула неприменима. '
                'f и N определяются ОПЫТНЫМ ПУТЁМ.'
            ),
            'f_min_mm': None, 'N': None, 'L_mm': None,
            'C': round(C, 4), 'm': round(m, 4),
            'formula': f'Формула неприменима при l={film_length_mm:.0f} ≥ d_вн={d_inner_mm:.1f}',
            'notes': 'ГОСТ Р 50.05.07-2018, п. Г.5',
        }
    else:
        empirical_prefix = ''
        is_empirical = False
    current_L = film_length_mm
    optimal_N = None
    optimal_f = None
    optimal_q = None
    optimal_L = film_length_mm

    for iteration in range(10):
        b = current_L / d_inner_mm
        f = 0.5 * C * (1 - m * math.sqrt(1 - b * b)) * d_outer_mm

        found = False
        for n in range(1, 6):
            denom = math.sqrt(
                (2 * n + 1 - m * math.sqrt(1 - b * b)) ** 2 + (m ** 2) * (b ** 2)
            )
            q = (b * (2 * n + 1)) / denom
            max_q = math.sqrt(1 - 0.2 * (2.6 - 1 / m) ** 2)

            if q <= max_q:
                arg1 = q * m
                arg2 = q * m / (2 * n + 1)
                if abs(arg1) <= 1 and abs(arg2) <= 1:
                    N = 180 / (
                        math.degrees(math.asin(arg1)) - math.degrees(math.asin(arg2))
                    )
                    optimal_N = math.ceil(N)
                    optimal_f = f
                    optimal_q = q
                    optimal_L = current_L
                    found = True
                    break

        if found:
            break

        new_l = current_L * 0.9
        if new_l < 50:
            break
        current_L = new_l

    if optimal_N is None:
        return {
            'scheme': '5b',
            'error': 'Решение не найдено. Уменьшите длину снимка или используйте источник с меньшим фокусным пятном.',
        }

    L_section = math.pi * d_outer_mm / optimal_N

    notes = 'Расчёт по методике ГОСТ 7512-82, Приложение 4, п. 4. '
    if optimal_L < film_length_mm:
        notes += f'Длина снимка уменьшена до {optimal_L:.1f} мм.'

    return {
        'scheme': '5b',
        # Флаг опытного определения (ГОСТ Р 50.05.07-2018 п. Г.5)
        'is_empirical': is_empirical,
        'empirical_reason': empirical_prefix if is_empirical else '',
        # Расчётные значения
        'C': round(C, 4),
        'm': round(m, 4),
        'b': round(optimal_L / d_inner_mm, 4),
        'q': round(optimal_q, 4),
        'f_min_mm': round(optimal_f, 1),
        'N': optimal_N,
        'L_mm': round(L_section, 0),
        'film_length_used_mm': round(optimal_L, 1),
        'formula': (
            f'f_справ ≥ {optimal_f:.1f} мм; N_справ = {optimal_N} экспоз. '
            f'(b = {optimal_L/d_inner_mm:.4f}, q = {optimal_q:.4f})'
            if is_empirical else
            f'f ≥ 0,5C(1-m√(1-b²))D = {optimal_f:.1f} мм; '
            f'N = {optimal_N} экспозиций'
        ),
        'notes': (empirical_prefix + '\n' if is_empirical else '') + notes,
    }


def calc_exposure_parameters(
    scheme: str,
    focal_spot_mm: float,
    sensitivity_mm: float,
    thickness_mm: float = 0,
    d_outer_mm: float = 0,
    d_inner_mm: float = 0,
    film_length_mm: float = 350,
) -> dict:
    """
    Универсальная функция расчёта параметров просвечивания для любой схемы.

    :param scheme: код схемы ('4_6', '5a', '5b', '5v', '5g', '5d', '5zh', '5z', '5e')
    :param focal_spot_mm: размер фокусного пятна Φ, мм
    :param sensitivity_mm: требуемая чувствительность K, мм
    :param thickness_mm: радиационная толщина s, мм (для схемы 4.6)
    :param d_outer_mm: наружный диаметр D, мм (для трубных схем)
    :param d_inner_mm: внутренний диаметр d, мм (для трубных схем)
    :param film_length_mm: длина снимка l, мм (для схемы 5б)
    :return: словарь с результатами расчёта
    """
    if scheme == '4_6':
        return _normalize_exposure_result(
            calc_scheme_4_6(focal_spot_mm, thickness_mm, sensitivity_mm),
            d_outer_mm,
        )
    elif scheme == '5a':
        return _normalize_exposure_result(
            calc_scheme_5a(focal_spot_mm, d_outer_mm, d_inner_mm, sensitivity_mm),
            d_outer_mm,
        )
    elif scheme == '5b':
        return _normalize_exposure_result(
            calc_scheme_5b_iterative(
                focal_spot_mm, d_outer_mm, d_inner_mm, film_length_mm, sensitivity_mm,
            ),
            d_outer_mm,
        )
    elif scheme == '5v':
        return _normalize_exposure_result(
            calc_scheme_5v(focal_spot_mm, d_outer_mm, d_inner_mm, sensitivity_mm),
            d_outer_mm,
        )
    elif scheme == '5g':
        return _normalize_exposure_result(
            calc_scheme_5g(focal_spot_mm, d_outer_mm, d_inner_mm, sensitivity_mm),
            d_outer_mm,
        )
    elif scheme == '5d':
        return _normalize_exposure_result(
            calc_scheme_5d(focal_spot_mm, d_outer_mm, d_inner_mm, sensitivity_mm),
            d_outer_mm,
        )
    elif scheme == '5zh':
        return _normalize_exposure_result(
            calc_scheme_5zh(focal_spot_mm, d_outer_mm, d_inner_mm, sensitivity_mm),
            d_outer_mm,
        )
    else:
        return {
            'scheme': scheme,
            'error': f'Схема {scheme} пока не реализована.',
        }


def _normalize_exposure_result(result: dict, d_outer_mm: float = 0) -> dict:
    """Приводит f к неотрицательному значению и дополняет L при необходимости."""
    if result.get('f_min_mm') is not None:
        result['f_min_mm'] = clamp_f_mm(result['f_min_mm'])
    if result.get('L_mm') is None:
        N = result.get('N')
        try:
            n = int(N)
        except (TypeError, ValueError):
            n = 0
        if d_outer_mm and n > 0:
            result['L_mm'] = round(math.pi * d_outer_mm / n, 0)
    return result


# ------------------------------------------------------------------
# Объём выборочного контроля (НП-105-18, п. 70–72)
# ------------------------------------------------------------------

def normalize_control_volume_pct(value) -> int:
    """Приводит объём контроля к одному из допустимых значений."""
    try:
        pct = int(float(value))
    except (TypeError, ValueError):
        return 100
    return pct if pct in CONTROL_VOLUME_OPTIONS else 100


def requires_full_length_ring_control(object_type: str, outer_diameter_mm: float) -> bool:
    """
    НП-105-18, п. 72: сварные соединения деталей с D ≤ 250 мм с кольцевыми швами
    контролируются по всей протяженности — число экспозиций и участков не уменьшается.
    """
    if object_type != 'pipe':
        return False
    d = float(outer_diameter_mm or 0)
    return 0 < d <= RING_FULL_LENGTH_DIAMETER_MM


def scale_exposure_count(value, volume_pct: int) -> int:
    """Пропорциональное уменьшение числа экспозиций/участков, минимум 1."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 1
    if n <= 0:
        return 1
    if volume_pct >= 100:
        return n
    return max(1, math.ceil(n * volume_pct / 100))


def calc_straight_seam_full_coverage(seam_length_mm: float, segment_length_mm: float) -> int:
    """
    Число экспозиций для 100 % контроля прямолинейного шва (схема 4.6 / чертёж 2).

    Отношение суммарной протяженности контролируемых участков к длине шва = 100 %.
    """
    if not seam_length_mm or not segment_length_mm or segment_length_mm <= 0:
        return 1
    return max(1, math.ceil(float(seam_length_mm) / float(segment_length_mm)))


def apply_control_volume_adjustment(
    *,
    N_full,
    N_segments_full=None,
    volume_pct: int = 100,
    apply_sample_scaling: bool = True,
    seam_length_mm: float | None = None,
    segment_length_mm: float | None = None,
) -> tuple[int, int, float | None]:
    """
    Корректирует «Число экспозиций» (6.6) и «Число контролируемых участков» (6.7)
    пропорционально объёму выборочного контроля.

    :param N_full: расчётное число экспозиций при 100 % охвате
    :param N_segments_full: расчётное число участков при 100 % охвате
    :param volume_pct: объём контроля, % (100, 50, 25, 10, 5)
    :param apply_sample_scaling: False для кольцевых швов D ≤ 250 мм (п. 72)
    :param seam_length_mm: длина прямолинейного шва (схема 4.6)
    :param segment_length_mm: длина участка за одну экспозицию L, мм
    :return: (N, N_segments, controlled_length_mm)
    """
    volume_pct = normalize_control_volume_pct(volume_pct)
    try:
        n_full = int(N_full) if N_full not in (None, '', '—') else 1
    except (TypeError, ValueError):
        n_full = 1
    try:
        n_seg_full = (
            int(N_segments_full)
            if N_segments_full not in (None, '', '—')
            else n_full
        )
    except (TypeError, ValueError):
        n_seg_full = n_full

    controlled_length: float | None = None

    if not apply_sample_scaling or volume_pct >= 100:
        if seam_length_mm and seam_length_mm > 0:
            controlled_length = float(seam_length_mm)
        return n_full, n_seg_full, controlled_length

    n_adj = scale_exposure_count(n_full, volume_pct)
    n_seg_adj = scale_exposure_count(n_seg_full, volume_pct)

    if seam_length_mm and segment_length_mm and seam_length_mm > 0 and segment_length_mm > 0:
        required_length = float(seam_length_mm) * volume_pct / 100.0
        controlled_length = min(float(seam_length_mm), n_adj * float(segment_length_mm))
        if controlled_length < required_length:
            n_adj = max(n_adj, math.ceil(required_length / float(segment_length_mm)))
            controlled_length = min(float(seam_length_mm), n_adj * float(segment_length_mm))

    return n_adj, n_seg_adj, controlled_length


def recommend_scheme(d_outer_mm: float, d_inner_mm: float,
                     access_inside: bool = False) -> list:
    """
    Рекомендует схемы просвечивания в зависимости от параметров трубопровода.

    :param d_outer_mm: наружный диаметр, мм
    :param d_inner_mm: внутренний диаметр, мм
    :param access_inside: есть ли доступ для размещения источника внутри
    :return: список рекомендуемых схем в порядке предпочтения
    """
    if d_outer_mm == 0:
        return ['4_6']

    recommendations = []
    if d_outer_mm <= 100 and not access_inside:
        recommendations.append('5v')
    if d_outer_mm > 50:
        recommendations.append('5a')
    if access_inside:
        if d_outer_mm <= 2000:
            recommendations.append('5zh')
        recommendations.extend(['5g', '5d'])
    if d_outer_mm > 100:
        recommendations.append('5b')

    return recommendations or ['5a']


# ------------------------------------------------------------------
# 2. Расчёт активности изотопных источников
# ------------------------------------------------------------------

# Периоды полураспада (сутки)
HALF_LIFE_DAYS = {
    'Ir-192': 73.83,
    'Se-75': 119.78,
    'Co-60': 1925.5,  # 5.27 лет
    'Tm-170': 128.6,
}

# Коэффициенты пересчёта Ки → Р·м²/ч (гамма-постоянная)
# Значения для пересчёта в мощность экспозиционной дозы на расстоянии 1 м
CONVERSION_FACTORS = {
    'Ir-192': 0.34,   # (Р·м²/ч) / Ки
    'Se-75': 0.27,
    'Co-60': 1.30,
    'Tm-170': 0.018,
}


def calc_remaining_activity(source_type: str, initial_activity_ci: float,
                             release_date_str: str, target_date_str: str) -> dict:
    """
    Рассчитывает остаточную активность радиоизотопного источника.

    Формула: A(t) = A₀ × (0,5)^(Δt / T½)

    :param source_type: тип источника ('Ir-192', 'Se-75', 'Co-60', 'Tm-170')
    :param initial_activity_ci: начальная активность, Ки
    :param release_date_str: дата выпуска (ГГГГ-ММ-ДД)
    :param target_date_str: целевая дата (ГГГГ-ММ-ДД)
    :return: словарь с результатами
    """
    from datetime import date

    try:
        release_date = date.fromisoformat(release_date_str)
        target_date = date.fromisoformat(target_date_str)
    except ValueError as e:
        return {'error': f'Неверный формат даты: {e}'}

    delta_days = (target_date - release_date).days
    half_life = HALF_LIFE_DAYS.get(source_type)

    if not half_life:
        return {'error': f'Неизвестный тип источника: {source_type}'}

    remaining_ci = initial_activity_ci * (0.5 ** (delta_days / half_life))
    conversion = CONVERSION_FACTORS.get(source_type, 1.0)
    dose_rate_at_1m = remaining_ci * conversion  # Р/ч на расстоянии 1 м

    return {
        'source_type': source_type,
        'initial_activity_ci': initial_activity_ci,
        'release_date': release_date_str,
        'target_date': target_date_str,
        'delta_days': delta_days,
        'remaining_activity_ci': round(remaining_ci, 4),
        'dose_rate_at_1m_rhr': round(dose_rate_at_1m, 4),
        'half_life_days': half_life,
        'formula': (
            f'A = {initial_activity_ci} × 0,5^({delta_days}/{half_life:.1f}) = '
            f'{remaining_ci:.4f} Ки'
        ),
    }


def calc_activity_table(source_type: str, initial_activity_ci: float,
                         release_date_str: str,
                         start_date_str: str, end_date_str: str) -> list:
    """
    Генерирует таблицу активности источника на каждый день периода.

    :return: список словарей {date, activity_ci, dose_rate}
    """
    from datetime import date, timedelta

    result = calc_remaining_activity(source_type, initial_activity_ci,
                                     release_date_str, start_date_str)
    if 'error' in result:
        return []

    release_date = date.fromisoformat(release_date_str)
    start_date = date.fromisoformat(start_date_str)
    end_date = date.fromisoformat(end_date_str)
    half_life = HALF_LIFE_DAYS[source_type]
    conversion = CONVERSION_FACTORS.get(source_type, 1.0)

    table = []
    current = start_date
    while current <= end_date:
        delta = (current - release_date).days
        activity = initial_activity_ci * (0.5 ** (delta / half_life))
        table.append({
            'date': current.strftime('%d.%m.%Y'),
            'activity_ci': round(activity, 3),
            'dose_rate_rhr': round(activity * conversion, 3),
        })
        current += timedelta(days=1)

    return table


# ------------------------------------------------------------------
# 3. Геометрическая нерезкость (повторно экспортируем для удобства)
# ------------------------------------------------------------------

def calc_geometric_unsharpness_full(focal_spot_mm: float, ofd_mm: float,
                                     sfd_mm: float,
                                     sensitivity_mm: Optional[float] = None) -> dict:
    """
    Расчёт геометрической нерезкости с проверкой соответствия ГОСТ.

    Формула: Ug = Φ × b / (f - b)

    :param focal_spot_mm: размер фокусного пятна Φ, мм
    :param ofd_mm: расстояние объект–детектор b, мм
    :param sfd_mm: расстояние источник–детектор f, мм
    :param sensitivity_mm: требуемая чувствительность K (для проверки ГОСТ)
    :return: словарь с результатами
    """
    if sfd_mm <= ofd_mm:
        return {'error': 'SFD должно быть больше OFD'}

    ug = focal_spot_mm * ofd_mm / (sfd_mm - ofd_mm)

    gost_ok = None
    max_allowed = None
    if sensitivity_mm:
        if sensitivity_mm <= 2.0:
            max_allowed = sensitivity_mm / 2
        else:
            max_allowed = 1.0
        gost_ok = ug <= max_allowed

    return {
        'ug_mm': round(ug, 3),
        'gost_ok': gost_ok,
        'max_allowed_mm': max_allowed,
        'formula': (
            f'Ug = Φ × b / (f - b) = '
            f'{focal_spot_mm} × {ofd_mm} / ({sfd_mm} - {ofd_mm}) = {ug:.3f} мм'
        ),
    }
