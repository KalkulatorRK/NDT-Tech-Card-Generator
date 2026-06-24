"""
Данные НП-105-18 «Правила контроля металла оборудования и трубопроводов
атомных энергетических установок при изготовлении и монтаже»
(с изменениями 2024 года, приказ Ростехнадзора N 211 от 08.07.2024).

Модуль содержит точные табличные данные из документа:
- Таблица N 4.8 — Нормы для сварных соединений категорий I, II, III
- Таблица N 4.9 — Нормы для сварных соединений категорий Iн, IIн
- Таблица N 4.6 — Поверхностные дефекты (подрезы, вольфрамовые включения)

ВАЖНО: Данные введены из оригинального текста документа (PDF).
При выходе новых изменений необходимо актуализировать этот модуль.
"""

import math

# ------------------------------------------------------------------
# Идентификатор документа
# ------------------------------------------------------------------
DOCUMENT_CODE = 'НП-105-18'
DOCUMENT_FULL_NAME = (
    'НП-105-18 «Правила контроля металла оборудования и трубопроводов '
    'атомных энергетических установок при изготовлении и монтаже» '
    '(с изменениями 2024 года)'
)

# ------------------------------------------------------------------
# Типы дефектов
# ------------------------------------------------------------------
DEFECT_TYPES = {
    'crack': {
        'code': 'crack',
        'name': 'Трещина',
        'always_reject': True,
        'reject_reason': (
            'Трещины не допускаются ни в каком количестве и размере '
            '(НП-105-18, п. 14).'
        ),
    },
    'lack_of_fusion': {
        'code': 'lack_of_fusion',
        'name': 'Несплавление',
        'always_reject': True,
        'reject_reason': (
            'Несплавления не допускаются ни в каком количестве и размере '
            '(НП-105-18, п. 14).'
        ),
    },
    'incomplete_penetration': {
        'code': 'incomplete_penetration',
        'name': 'Непровар',
        'always_reject': True,
        'reject_reason': (
            'Непровары не допускаются ни в каком количестве и размере '
            '(НП-105-18, п. 14).'
        ),
    },
    'pore': {
        'code': 'pore',
        'name': 'Пора / Округлое включение',
        'always_reject': False,
    },
    'slag': {
        'code': 'slag',
        'name': 'Шлаковое включение',
        'always_reject': False,
    },
    'cluster': {
        'code': 'cluster',
        'name': 'Скопление включений',
        'always_reject': False,
    },
    'tungsten': {
        'code': 'tungsten',
        'name': 'Вольфрамовое включение',
        'always_reject': False,
    },
    'undercut': {
        'code': 'undercut',
        'name': 'Подрез основного металла',
        'always_reject': False,
    },
    'concavity': {
        'code': 'concavity',
        'name': 'Вогнутость корня шва',
        'always_reject': False,
    },
    'convexity': {
        'code': 'convexity',
        'name': 'Выпуклость корня шва',
        'always_reject': False,
    },
}

# ------------------------------------------------------------------
# Таблица N 4.8 — Нормы допустимых одиночных включений и скоплений
# для сварных соединений I, II, III категорий (сталь и Fe-Ni сплавы)
#
# Структура записи:
# (толщина_мин, толщина_макс, чувствительность_K,
#  макс_вкл, макс_скоп, кол_100мм, сумм_площадь,
#  кр_макс_разм, кр_макс_шир, кр_кол_100мм)
#
# где:
#   толщина — номинальная толщина свариваемых деталей, мм
#   чувствительность_K — требуемая чувствительность, мм (не более)
#   макс_вкл — допустимый наибольший размер одиночного включения, мм
#   макс_скоп — допустимый наибольший размер одиночного скопления, мм
#   кол_100мм — допустимое число включений и скоплений на 100 мм шва
#   сумм_площадь — допустимая суммарная приведённая площадь, мм²
#   кр_макс_разм — допустимый наибольший размер одиночного крупного включения, мм
#   кр_макс_шир — допустимая наибольшая ширина крупного включения, мм
#   кр_кол_100мм — допустимое число крупных включений на 100 мм шва
# ------------------------------------------------------------------

TABLE_4_8_CAT_I = [
    # толщ_мин, толщ_макс,  K,   вкл,  скоп, n, S_пр,  кр_р, кр_ш, кр_n
    (1.0,  1.5,  0.10,  0.2,  0.3, 10,  0.15,  3.0,  0.2,  1),
    (1.5,  2.0,  0.10,  0.3,  0.4, 10,  0.30,  3.0,  0.3,  1),
    (2.0,  2.5,  0.10,  0.4,  0.6, 10,  0.60,  3.0,  0.4,  1),
    (2.5,  3.0,  0.10,  0.5,  0.8, 10,  1.00,  3.0,  0.5,  1),
    (3.0,  4.5,  0.10,  0.6,  1.0, 10,  1.40,  3.0,  0.6,  1),
    (4.5,  6.0,  0.20,  0.8,  1.2, 11,  2.50,  3.0,  0.8,  1),
    (6.0,  7.5,  0.20,  1.0,  1.5, 11,  4.00,  3.0,  1.0,  1),
    (7.5,  10.0, 0.20,  1.2,  2.0, 12,  5.50,  3.5,  1.2,  1),
    (10.0, 12.0, 0.20,  1.5,  2.5, 12,  7.50,  3.5,  1.5,  1),
    (12.0, 14.0, 0.30,  1.5,  2.5, 13,  9.00,  4.0,  1.5,  1),
    (14.0, 18.0, 0.30,  2.0,  3.0, 13, 11.00,  4.0,  2.0,  1),
    (18.0, 21.0, 0.30,  2.0,  3.0, 14, 14.00,  4.0,  2.0,  1),
    (21.0, 24.0, 0.40,  2.0,  3.0, 14, 17.50,  5.0,  2.0,  1),
    (24.0, 27.0, 0.40,  2.5,  3.5, 15, 20.00,  5.0,  2.5,  2),
    (27.0, 30.0, 0.40,  2.5,  3.5, 15, 23.00,  6.0,  2.5,  2),
    (30.0, 35.0, 0.50,  2.5,  4.0, 16, 26.00,  6.0,  2.5,  2),
    (35.0, 40.0, 0.50,  3.0,  4.5, 17, 30.00,  7.0,  3.0,  2),
    (40.0, 45.0, 0.60,  3.0,  4.5, 18, 34.00,  8.0,  3.0,  2),
    (45.0, 50.0, 0.60,  3.0,  4.5, 19, 38.00,  9.0,  3.0,  2),
    (50.0, 55.0, 0.60,  3.0,  4.5, 20, 42.00, 10.0,  3.0,  2),
    (55.0, 65.0, 0.75,  3.5,  5.0, 21, 48.00, 10.0,  3.5,  2),
    (65.0, 75.0, 0.75,  3.5,  5.0, 22, 56.00, 10.0,  3.5,  2),
    (75.0, 85.0, 1.00,  4.0,  6.0, 23, 64.00, 10.0,  4.0,  2),
    (85.0, 100.0,1.00,  4.0,  6.0, 24, 72.00, 10.0,  4.0,  2),
]

TABLE_4_8_CAT_II = [
    (1.5,  2.0,  0.10,  0.4,  0.6, 11,  0.60,  4.0,  0.4,  1),
    (2.0,  2.5,  0.10,  0.5,  0.8, 11,  1.20,  4.0,  0.5,  1),
    (2.5,  3.5,  0.10,  0.6,  1.0, 11,  1.70,  4.0,  0.6,  1),
    (3.5,  5.0,  0.20,  0.8,  1.2, 11,  3.00,  4.0,  0.8,  1),
    (5.0,  6.5,  0.20,  1.0,  1.5, 12,  4.50,  4.0,  1.0,  2),
    (6.5,  8.5,  0.20,  1.2,  2.0, 12,  6.50,  4.0,  1.2,  2),
    (8.5,  10.0, 0.20,  1.5,  2.5, 13,  8.50,  4.0,  1.5,  2),
    (10.0, 12.0, 0.30,  1.5,  2.5, 13, 10.00,  5.0,  1.5,  2),
    (12.0, 15.0, 0.30,  2.0,  3.0, 14, 12.00,  5.0,  2.0,  2),
    (15.0, 18.0, 0.30,  2.0,  3.0, 14, 15.00,  5.0,  2.0,  2),
    (18.0, 21.0, 0.40,  2.5,  3.5, 15, 18.00,  6.0,  2.5,  2),
    (21.0, 24.0, 0.40,  2.5,  4.0, 15, 21.00,  6.0,  2.5,  2),
    (24.0, 28.0, 0.50,  3.0,  4.5, 16, 24.00,  7.0,  3.0,  2),
    (28.0, 32.0, 0.50,  3.0,  4.5, 16, 28.00,  7.0,  3.0,  2),
    (32.0, 38.0, 0.60,  3.0,  4.5, 18, 32.00,  8.0,  3.0,  2),
    (38.0, 44.0, 0.60,  3.5,  5.0, 20, 37.00,  9.0,  3.5,  2),
    (44.0, 52.0, 0.75,  3.5,  5.0, 21, 43.00, 10.0,  3.5,  2),
    (52.0, 60.0, 0.75,  4.0,  6.0, 22, 50.00, 12.0,  4.0,  3),
    (60.0, 70.0, 1.00,  4.0,  6.0, 23, 58.00, 12.0,  4.0,  3),
    (70.0, 80.0, 1.00,  4.0,  6.0, 24, 67.00, 12.0,  4.0,  3),
    (80.0, 100.0,1.25,  4.0,  6.0, 25, 81.00, 12.0,  4.0,  3),
    (100.0,120.0,1.50,  5.0,  7.0, 26,100.00, 12.0,  5.0,  3),
    (120.0,140.0,1.75,  5.0,  7.0, 25,115.00, 12.0,  5.0,  3),
    (140.0,160.0,2.00,  5.0,  8.0, 24,135.00, 13.0,  5.0,  3),
    (160.0,200.0,2.50,  6.0,  9.0, 24,160.00, 13.0,  6.0,  3),
    (200.0,240.0,3.00,  6.0,  9.0, 23,200.00, 14.0,  6.0,  3),
    (240.0,280.0,3.50,  7.0, 10.0, 22,235.00, 14.0,  7.0,  3),
    (280.0,9999, 4.00,  8.0, 12.0, 22,250.00, 14.0,  8.0,  3),
]

TABLE_4_8_CAT_III = [
    (1.0,  2.0,  0.10,  0.4,  0.6, 12,  0.80,  5.0,  0.5,  2),
    (2.0,  3.0,  0.10,  0.6,  1.0, 12,  2.00,  5.0,  0.6,  2),
    (3.0,  4.0,  0.20,  0.8,  1.2, 12,  3.50,  5.0,  0.8,  2),
    (4.0,  5.0,  0.20,  1.0,  1.5, 13,  5.00,  5.0,  1.0,  2),
    (5.0,  6.5,  0.20,  1.2,  2.0, 13,  6.00,  5.0,  1.2,  3),
    (6.5,  8.0,  0.20,  1.5,  2.5, 13,  8.00,  5.0,  1.5,  3),
    (8.0,  10.0, 0.30,  1.5,  2.5, 14, 10.00,  5.0,  1.5,  3),
    (10.0, 12.0, 0.30,  2.0,  3.0, 14, 12.00,  6.0,  2.0,  3),
    (12.0, 14.0, 0.40,  2.0,  3.0, 15, 14.00,  6.0,  2.0,  3),
    (14.0, 18.0, 0.40,  2.5,  3.5, 15, 16.00,  6.0,  2.5,  3),
    (18.0, 22.0, 0.50,  3.0,  4.0, 16, 20.00,  7.0,  3.0,  3),
    (22.0, 24.0, 0.50,  3.0,  4.5, 16, 25.00,  7.0,  3.0,  3),
    (24.0, 28.0, 0.60,  3.0,  4.5, 18, 25.00,  8.0,  3.0,  3),
    (28.0, 32.0, 0.60,  3.5,  5.0, 18, 31.00,  8.0,  3.5,  3),
    (32.0, 35.0, 0.60,  3.5,  5.0, 20, 35.00,  9.0,  3.5,  3),
    (35.0, 38.0, 0.75,  3.5,  5.0, 20, 35.00,  9.0,  3.5,  3),
    (38.0, 44.0, 0.75,  4.0,  6.0, 21, 41.00, 10.0,  4.0,  3),
    (44.0, 50.0, 0.75,  4.0,  6.0, 22, 47.00, 12.0,  4.0,  3),
    (50.0, 60.0, 1.00,  4.0,  6.0, 23, 55.00, 14.0,  4.0,  4),
    (60.0, 70.0, 1.00,  4.0,  6.0, 24, 65.00, 14.0,  4.0,  4),
    (70.0, 85.0, 1.25,  5.0,  7.0, 25, 78.00, 14.0,  5.0,  4),
    (85.0, 100.0,1.50,  5.0,  7.0, 26, 92.00, 14.0,  5.0,  4),
    (100.0,130.0,2.00,  5.0,  8.0, 27,115.00, 14.0,  5.0,  4),
    (130.0,165.0,2.50,  6.0,  9.0, 26,145.00, 15.0,  6.0,  4),
    (165.0,200.0,3.00,  6.0,  9.0, 25,160.00, 15.0,  6.0,  4),
    (200.0,225.0,3.50,  7.0, 10.0, 25,210.00, 15.0,  7.0,  4),
    (225.0, 9999,4.00,  8.0, 12.0, 24,230.00, 16.0,  8.0,  4),
]

# Таблица N 4.9 — Категории Iн и IIн
TABLE_4_9_CAT_IN = [
    # (толщ_мин, толщ_макс, K, макс_разм, n_100мм, сумм_площадь)
    (0.0,  2.0,  0.10, None, None, None),   # Не допускаются
    (2.0,  3.0,  0.10, None, None, None),   # Не допускаются
    (3.0,  5.0,  0.10,  0.4,    3,   0.5),
    (5.0,  8.0,  0.20,  0.5,    3,   1.0),
    (8.0,  11.0, 0.30,  0.6,    4,   1.5),
    (11.0, 14.0, 0.30,  0.8,    4,   2.0),
    (14.0, 20.0, 0.30,  1.0,    4,   3.0),
    (20.0, 26.0, 0.40,  1.2,    4,   4.5),
    (26.0, 34.0, 0.40,  1.6,    4,   7.0),
    (34.0, 45.0, 0.50,  2.0,    5,  12.0),
    (45.0, 67.0, 0.60,  2.5,    5,  20.0),
    (67.0, 90.0, 1.00,  3.0,    5,  27.0),
    (90.0, 120.0,1.25,  4.0,    5,  45.0),
    (120.0,200.0,1.50,  5.0,    5,  75.0),
    (200.0, 9999,2.00,  5.0,    7, 125.0),
]

TABLE_4_9_CAT_IIN = [
    (0.0,  2.0,  0.10, None, None, None),   # Не допускаются
    (2.0,  3.0,  0.10,  0.4,    5,   0.6),
    (3.0,  5.0,  0.20,  0.5,    5,   1.0),
    (5.0,  8.0,  0.20,  0.6,    5,   1.5),
    (8.0,  11.0, 0.20,  0.8,    5,   2.5),
    (11.0, 14.0, 0.30,  1.0,    6,   4.0),
    (14.0, 20.0, 0.30,  1.2,    6,   6.0),
    (20.0, 26.0, 0.40,  1.5,    6,   9.0),
    (26.0, 34.0, 0.50,  2.0,    6,  16.0),
    (34.0, 45.0, 0.60,  2.5,    7,  25.0),
    (45.0, 67.0, 0.75,  3.0,    7,  36.0),
    (67.0, 90.0, 1.00,  4.0,    7,  64.0),
    (90.0, 120.0,1.25,  5.0,    7, 100.0),
    (120.0,200.0,1.50,  5.0,    8, 125.0),
]

# Сводный словарь таблиц по категориям
INCLUSION_TABLES = {
    'I':   TABLE_4_8_CAT_I,
    'II':  TABLE_4_8_CAT_II,
    'III': TABLE_4_8_CAT_III,
    'Iн':  TABLE_4_9_CAT_IN,
    'IIн': TABLE_4_9_CAT_IIN,
}


def _lookup_table(category: str, thickness_mm: float) -> dict:
    """
    Возвращает строку таблицы нормативных критериев для заданной
    категории сварного соединения и толщины.

    :param category: категория ('I', 'II', 'III', 'Iн', 'IIн')
    :param thickness_mm: номинальная толщина свариваемых деталей, мм
    :return: словарь с критериями или пустой словарь
    """
    table = INCLUSION_TABLES.get(category)
    if not table:
        return {}

    for row in table:
        t_min, t_max = row[0], row[1]
        if t_min < thickness_mm <= t_max:
            K = row[2]
            # Определяем расширенный или укороченный формат строки
            if len(row) >= 10:
                # Полная таблица 4.8 (категории I, II, III)
                return {
                    'sensitivity_K': K,
                    'max_inclusion_mm': row[3],
                    'max_cluster_mm': row[4],
                    'max_count_100mm': row[5],
                    'max_total_area_mm2': row[6],
                    'max_large_size_mm': row[7],
                    'max_large_width_mm': row[8],
                    'max_large_count_100mm': row[9],
                    'table': '4.8',
                }
            else:
                # Укороченная таблица 4.9 (категории Iн, IIн)
                return {
                    'sensitivity_K': K,
                    'max_inclusion_mm': row[3],
                    'max_cluster_mm': row[3],   # Нет отдельного скопления — берём включение
                    'max_count_100mm': row[4],
                    'max_total_area_mm2': row[5],
                    'max_large_size_mm': None,
                    'max_large_width_mm': None,
                    'max_large_count_100mm': None,
                    'table': '4.9',
                }
    return {}


def get_required_sensitivity(category: str, thickness_mm: float) -> float:
    """
    Возвращает требуемую чувствительность контроля K (мм) по
    НП-105-18, Таблица 4.8/4.9.

    :param category: категория сварного соединения
    :param thickness_mm: номинальная толщина, мм
    :return: требуемая чувствительность K, мм (или 0 если не найдено)
    """
    row = _lookup_table(category, thickness_mm)
    return row.get('sensitivity_K', 0)


def get_defect_type_choices():
    """Список кортежей типов дефектов для выпадающего списка."""
    return [(code, info['name']) for code, info in DEFECT_TYPES.items()]


# ------------------------------------------------------------------
# Таблица N 4.6 — Поверхностные дефекты (ВИК)
# ------------------------------------------------------------------

# Подрезы основного металла (п. 10 прил. 4, табл. 4.6)
# Категории I, II, III: глубина ≤ 0.1S, не более 0.5 мм
# Длина участков не более 50.0 мм на любых 100.0 мм шва (≤ 10%)
UNDERCUT_CRITERIA = {
    'I':   {'depth_coeff': 0.10, 'abs_max_depth': 0.50, 'max_length_100mm': 50.0},
    'II':  {'depth_coeff': 0.10, 'abs_max_depth': 0.50, 'max_length_100mm': 50.0},
    'III': {'depth_coeff': 0.10, 'abs_max_depth': 0.50, 'max_length_100mm': 50.0},
    'Iн':  {'depth_coeff': 0.10, 'abs_max_depth': 0.50, 'max_length_100mm': 50.0},
    'IIн': {'depth_coeff': 0.10, 'abs_max_depth': 0.50, 'max_length_100mm': 50.0},
}

# Вольфрамовые включения (табл. 4.6)
# Размер ≤ 0.1S, не более 2.0 мм — 1 шт на 100 мм
# Размер ≤ 0.1S (большей группы) — 3 шт на 100 мм
TUNGSTEN_CRITERIA = {
    'I':   {'size_coeff': 0.10, 'abs_max': 2.0, 'max_count_100mm': 1},
    'II':  {'size_coeff': 0.10, 'abs_max': 2.0, 'max_count_100mm': 1},
    'III': {'size_coeff': 0.10, 'abs_max': 2.0, 'max_count_100mm': 1},
}

# Западания между валиками и чешуйчатость (табл. 4.6)
RIPPLE_CRITERIA = {
    # Для всех категорий I, II, III
    'all_max_up_to_10': 1.0,   # мм при толщине ≤ 10 мм
    'II_III_10_20': 1.2,        # мм для II, III при 10 < S ≤ 20 мм
    'II_III_over_20': 1.5,      # мм для II, III при S > 20 мм
}

# Вогнутость корня шва (поворотные стыки, без подкладных колец, табл. 4.6)
CONCAVITY_CRITERIA_ROTARY = {
    (1.0, 2.0): 0.2,
    (2.0, 3.0): 0.4,
    (3.0, 4.0): 0.6,
    (4.0, 6.0): 0.8,
    (6.0, 8.0): 1.0,
    (8.0, 12.0): 1.2,
    (12.0, 9999): 1.5,
}

# Вогнутость корня шва (неповоротные стыки, без подкладных колец, табл. 4.6)
CONCAVITY_CRITERIA_FIXED = {
    (1.0, 2.0): 0.4,
    (2.0, 3.0): 0.6,
    (3.0, 4.0): 0.8,
    (4.0, 6.0): 1.0,
    (6.0, 8.0): 1.2,
    (8.0, 9999): None,  # 0.15S, не более 1.6 мм (при условии увеличения усиления)
}

# Выпуклость корня шва (односторонняя сварка, без подкладных колец, табл. 4.6)
CONVEXITY_CRITERIA = {
    'dn_up_to_25': 1.5,     # Ду ≤ 25 мм
    'dn_25_to_150': 2.0,    # Ду 25–150 мм
    'dn_over_150': 2.5,     # Ду > 150 мм
}


# ------------------------------------------------------------------
# Функции оценки дефектов
# ------------------------------------------------------------------

def assess_inclusion(
    defect_type: str,
    category: str,
    thickness_mm: float,
    size_mm: float,
    is_cluster: bool = False,
    count: int = 1,
) -> dict:
    """
    Оценивает допустимость одиночного включения или скопления
    по Таблице N 4.8 или 4.9 НП-105-18.

    :param defect_type: тип дефекта ('pore', 'slag', 'cluster')
    :param category: категория сварного соединения
    :param thickness_mm: номинальная толщина, мм
    :param size_mm: максимальный размер дефекта, мм
    :param is_cluster: True если это скопление, False если одиночное включение
    :param count: количество дефектов на оцениваемом участке
    :return: словарь с результатом оценки
    """
    criteria = _lookup_table(category, thickness_mm)

    if not criteria:
        return {
            'is_acceptable': False,
            'reason': f'Нет данных для категории {category} и толщины {thickness_mm} мм',
            'criterion': '',
            'reference': 'НП-105-18, Таблица 4.8',
            'max_allowed_mm': 0,
            'max_allowed_count': 0,
        }

    max_allowed = criteria['max_cluster_mm'] if is_cluster else criteria['max_inclusion_mm']
    max_count = criteria.get('max_count_100mm')

    if max_allowed is None:
        return {
            'is_acceptable': False,
            'reason': f'Включения не допускаются для категории {category} при толщине {thickness_mm} мм',
            'criterion': 'Не допускаются',
            'reference': 'НП-105-18, Таблица 4.9',
            'max_allowed_mm': 0,
            'max_allowed_count': 0,
        }

    size_ok = size_mm <= max_allowed
    count_ok = True
    if max_count is not None:
        count_ok = count <= max_count

    is_ok = size_ok and count_ok
    reasons = []
    if not size_ok:
        reasons.append(
            f'{"Одиночное скопление" if is_cluster else "Одиночное включение"} '
            f'{size_mm:.2f} мм превышает допустимый размер {max_allowed:.2f} мм'
        )
    if not count_ok and max_count is not None:
        reasons.append(
            f'Количество {count} шт. превышает допустимое {max_count} шт. '
            f'на участке длиной 100,0 мм'
        )

    if is_ok:
        reason = (
            f'{"Одиночное скопление" if is_cluster else "Одиночное включение"} '
            f'{size_mm:.2f} мм, {count} шт. — допустимо '
            f'(размер ≤ {max_allowed:.2f} мм'
            + (f', число ≤ {max_count} шт. на 100,0 мм' if max_count is not None else '')
            + ')'
        )
    else:
        reason = ' | '.join(reasons)

    criterion = f'Допустимый размер: {max_allowed:.2f} мм'
    if max_count is not None:
        criterion += (
            f'; допустимое число включений и скоплений на 100,0 мм: {max_count} шт.'
        )

    return {
        'is_acceptable': is_ok,
        'reason': reason,
        'criterion': criterion,
        'reference': f'НП-105-18, Таблица {criteria["table"]}',
        'max_allowed_mm': max_allowed,
        'max_allowed_count': max_count,
        'sensitivity_K': criteria['sensitivity_K'],
    }


def assess_undercut(
    category: str,
    thickness_mm: float,
    depth_mm: float,
    length_mm: float = 0,
    segment_length_mm: float = 0,
) -> dict:
    """
    Оценивает допустимость подреза по Таблице N 4.6 НП-105-18.

    :param category: категория шва
    :param thickness_mm: толщина стенки S, мм
    :param depth_mm: глубина подреза, мм
    :param length_mm: суммарная длина подреза на 100 мм шва
    :param segment_length_mm: длина отдельного участка подреза
    """
    crit = UNDERCUT_CRITERIA.get(category)
    if not crit:
        crit = UNDERCUT_CRITERIA.get('I')

    max_depth = min(crit['depth_coeff'] * thickness_mm, crit['abs_max_depth'])
    max_length = crit['max_length_100mm']

    depth_ok = depth_mm <= max_depth
    length_ok = (length_mm <= max_length) if length_mm else True
    segment_ok = (segment_length_mm <= 50.0) if segment_length_mm else True

    is_ok = depth_ok and length_ok and segment_ok

    reasons = []
    if not depth_ok:
        reasons.append(
            f'Глубина {depth_mm:.2f} мм превышает допустимую '
            f'{max_depth:.2f} мм (0,1S = 0,1×{thickness_mm})'
        )
    if not length_ok:
        reasons.append(
            f'Суммарная длина {length_mm:.1f} мм > {max_length:.0f} мм на 100 мм шва'
        )
    if not segment_ok:
        reasons.append(
            f'Длина отдельного участка {segment_length_mm:.1f} мм > 50,0 мм'
        )

    return {
        'is_acceptable': is_ok,
        'reason': ' | '.join(reasons) if reasons else (
            f'Глубина {depth_mm:.2f} мм ≤ {max_depth:.2f} мм — допустимо'
        ),
        'criterion': (
            f'Глубина: 0,1×S = {max_depth:.2f} мм, не более 0,5 мм; '
            f'Длина: не более {max_length:.0f} мм на 100 мм шва'
        ),
        'reference': 'НП-105-18, Таблица N 4.6',
        'max_allowed_mm': max_depth,
    }


def assess_tungsten(category: str, thickness_mm: float, size_mm: float, count: int = 1) -> dict:
    """
    Оценивает допустимость вольфрамового включения по Таблице N 4.6.
    """
    crit = TUNGSTEN_CRITERIA.get(category, TUNGSTEN_CRITERIA.get('I'))
    max_size = min(crit['size_coeff'] * thickness_mm, crit['abs_max'])
    max_count = crit.get('max_count_100mm', 1)

    size_ok = size_mm <= max_size
    count_ok = count <= max_count
    is_ok = size_ok and count_ok

    reasons = []
    if not size_ok:
        reasons.append(
            f'Размер {size_mm:.2f} мм превышает допустимый {max_size:.2f} мм'
        )
    if not count_ok:
        reasons.append(
            f'Количество {count} шт. превышает допустимое {max_count} шт. на 100,0 мм'
        )

    if is_ok:
        reason = (
            f'Вольфрамовое включение {size_mm:.2f} мм, {count} шт. — допустимо'
        )
    else:
        reason = ' | '.join(reasons)

    return {
        'is_acceptable': is_ok,
        'reason': reason,
        'criterion': (
            f'≤ 0,1S = {max_size:.2f} мм; не более {max_count} шт. на 100,0 мм'
        ),
        'reference': 'НП-105-18, Таблица N 4.6',
        'max_allowed_mm': max_size,
        'max_allowed_count': max_count,
    }


def _check_aggregate_inclusion_count(
    defects: list,
    category: str,
    thickness_mm: float,
    weld_length_mm: float = 0,
) -> dict | None:
    """
    Суммарная проверка числа включений и скоплений по табл. 4.8/4.9.

    Учитывает все поры, шлаковые включения и скопления на оцениваемом участке.
    """
    criteria = _lookup_table(category, thickness_mm)
    max_per_100 = criteria.get('max_count_100mm')
    if max_per_100 is None:
        return None

    inclusion_types = {'pore', 'slag', 'cluster'}
    total = sum(
        int(d.get('count', 1) or 1)
        for d in defects
        if d.get('type') in inclusion_types
    )
    if total == 0:
        return None

    segment_mm = 100.0
    if weld_length_mm and weld_length_mm > segment_mm:
        segments = math.ceil(weld_length_mm / segment_mm)
        allowed = max_per_100 * segments
        segment_desc = (
            f'на длине шва {weld_length_mm:.0f} мм '
            f'({segments:.0f}×100,0 мм, всего {allowed:.0f} шт.)'
        )
    else:
        allowed = max_per_100
        segment_desc = f'на участке длиной 100,0 мм (не более {allowed} шт.)'

    is_ok = total <= allowed
    return {
        'is_acceptable': is_ok,
        'total_count': total,
        'allowed_count': allowed,
        'max_count_100mm': max_per_100,
        'reason': (
            f'Суммарное число включений и скоплений: {total} шт. — '
            f'{"допустимо" if is_ok else "ПРЕВЫШАЕТ НОРМУ"} '
            f'({segment_desc})'
        ),
        'reference': f'НП-105-18, Таблица {criteria.get("table", "4.8")}',
    }


def _attach_gost_notation(
    result: dict,
    defect_type: str,
    size_1_mm: float,
    size_2_mm: float,
    count: int,
) -> dict:
    """Добавляет условную запись дефекта по ГОСТ 7512-82, приложение 5."""
    from normative.gost_7512 import format_gost_7512_defect_notation, NOTATION_REFERENCE

    morphology = 'cluster' if defect_type == 'cluster' else 'single'
    elongated = defect_type in ('pore', 'slag', 'tungsten') and size_2_mm > 0
    result['gost_notation'] = format_gost_7512_defect_notation(
        defect_type,
        size_1_mm,
        size_2_mm,
        count,
        morphology=morphology,
        elongated=elongated,
    )
    result['gost_notation_ref'] = NOTATION_REFERENCE
    return result


def assess_defect(
    defect_type: str,
    category: str,
    thickness_mm: float,
    size_1_mm: float = 0,
    size_2_mm: float = 0,
    count: int = 1,
    weld_length_mm: float = 0,
) -> dict:
    """
    Универсальная функция оценки допустимости дефекта по НП-105-18.

    :param defect_type: код типа дефекта
    :param category: категория сварного соединения ('I', 'II', 'III', 'Iн', 'IIн')
    :param thickness_mm: номинальная толщина свариваемых деталей, мм
    :param size_1_mm: основной размер дефекта (диаметр/глубина/длина), мм
    :param size_2_mm: вспомогательный размер (длина подреза и т.д.), мм
    :param count: количество дефектов
    :param weld_length_mm: длина шва (для расчёта суммарной длины)
    :return: словарь с результатом оценки
    """
    defect_info = DEFECT_TYPES.get(defect_type, {})

    # Абсолютно недопустимые дефекты
    if defect_info.get('always_reject'):
        result = {
            'defect_type': defect_type,
            'defect_name': defect_info.get('name', defect_type),
            'is_acceptable': False,
            'reason': defect_info.get('reject_reason', 'Недопустимо'),
            'criterion': 'Не допускается ни в каком количестве и размере',
            'reference': 'НП-105-18, п. 14',
            'max_allowed_mm': 0,
        }
        return _attach_gost_notation(result, defect_type, size_1_mm, size_2_mm, count)

    base = {
        'defect_type': defect_type,
        'defect_name': defect_info.get('name', defect_type),
    }

    # Оценка включений (поры, шлак, скопления)
    if defect_type in ('pore', 'slag'):
        result = assess_inclusion(
            defect_type, category, thickness_mm, size_1_mm,
            is_cluster=False, count=count,
        )
        base.update(result)

    elif defect_type == 'cluster':
        result = assess_inclusion(
            defect_type, category, thickness_mm, size_1_mm,
            is_cluster=True, count=count,
        )
        base.update(result)

    elif defect_type == 'tungsten':
        result = assess_tungsten(category, thickness_mm, size_1_mm, count=count)
        base.update(result)

    elif defect_type == 'undercut':
        result = assess_undercut(
            category, thickness_mm,
            depth_mm=size_1_mm,
            length_mm=size_2_mm,
        )
        base.update(result)

    else:
        # Неизвестный тип
        base.update({
            'is_acceptable': False,
            'reason': f'Оценка типа "{defect_type}" не реализована',
            'criterion': '',
            'reference': 'НП-105-18',
            'max_allowed_mm': 0,
        })

    return _attach_gost_notation(base, defect_type, size_1_mm, size_2_mm, count)


def assess_multiple_defects(
    defects: list,
    category: str,
    thickness_mm: float,
    weld_length_mm: float = 0,
) -> dict:
    """
    Оценивает перечень дефектов и формирует итоговое заключение.

    :param defects: список словарей {'type', 'size_1', 'size_2', 'count'}
    :param category: категория сварного соединения
    :param thickness_mm: толщина стенки, мм
    :param weld_length_mm: длина шва (для подрезов)
    :return: итоговое заключение
    """
    results = []
    for defect in defects:
        result = assess_defect(
            defect_type=defect.get('type', ''),
            category=category,
            thickness_mm=thickness_mm,
            size_1_mm=float(defect.get('size_1', 0) or 0),
            size_2_mm=float(defect.get('size_2', 0) or 0),
            count=int(defect.get('count', 1) or 1),
            weld_length_mm=weld_length_mm,
        )
        results.append(result)

    aggregate = _check_aggregate_inclusion_count(
        defects, category, thickness_mm, weld_length_mm,
    )
    if aggregate and not aggregate['is_acceptable']:
        results.append({
            'defect_type': '_aggregate_inclusions',
            'defect_name': (
                'Суммарное число включений и скоплений (табл. 4.8, на 100,0 мм)'
            ),
            'is_acceptable': False,
            'reason': aggregate['reason'],
            'criterion': (
                f'Не более {aggregate["max_count_100mm"]} шт. '
                f'на участке длиной 100,0 мм'
            ),
            'reference': aggregate['reference'],
            'max_allowed_mm': 0,
            'max_allowed_count': aggregate['max_count_100mm'],
        })

    all_ok = all(r.get('is_acceptable', False) for r in results)

    # Также получаем требуемую чувствительность для данной толщины/категории
    criteria_row = _lookup_table(category, thickness_mm)
    required_sensitivity = criteria_row.get('sensitivity_K', '—')

    count_exceeded = aggregate is not None and not aggregate['is_acceptable']

    from normative.gost_7512 import format_gost_7512_notation_list
    notations = [
        r.get('gost_notation', '')
        for r in results
        if r.get('gost_notation') and r.get('defect_type') != '_aggregate_inclusions'
    ]
    combined_notation = format_gost_7512_notation_list(notations)

    return {
        'is_acceptable': all_ok,
        'verdict': 'ГОДЕН' if all_ok else 'БРАК',
        'results': results,
        'required_sensitivity_K': required_sensitivity,
        'criteria_table': criteria_row,
        'max_count_100mm': criteria_row.get('max_count_100mm'),
        'total_inclusion_count': aggregate['total_count'] if aggregate else 0,
        'max_inclusion_count_allowed': aggregate['allowed_count'] if aggregate else None,
        'count_exceeded': count_exceeded,
        'count_reason': aggregate['reason'] if count_exceeded else '',
        'score_exceeded': count_exceeded,
        'score_reason': aggregate['reason'] if count_exceeded else '',
        'combined_gost_notation': combined_notation,
        'gost_notation_ref': 'ГОСТ 7512-82, приложение 5',
    }


def get_weld_category_choices():
    """Категории I–III для полей выбора (НП-105-18, табл. 4.8)."""
    return [
        ('I', 'I'),
        ('II', 'II'),
        ('III', 'III'),
    ]
