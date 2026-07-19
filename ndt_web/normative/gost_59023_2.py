"""
Данные ГОСТ Р 59023.2-2020 «Сварка и наплавка оборудования и трубопроводов
атомных энергетических установок. Основные типы сварных соединений».

Модуль содержит:
- Коды способов сварки (раздел 3.2)
- Типы сварных соединений (С, У, Т) с данными таблиц 9.1–9.122
- Функции расчёта ширины валика шва, ширины контролируемой зоны

Данные введены из оригинального текста документа (RTF).
"""

from __future__ import annotations

import re
from pathlib import Path

# ------------------------------------------------------------------
# Коды способов сварки (раздел 3.2 ГОСТ Р 59023.2-2020)
# ------------------------------------------------------------------

WELDING_PROCESSES = {
    '10': {
        'code': '10',
        'name': 'Автоматическая сварка под флюсом',
        'abbr': 'АДФ (флюс)',
        'iso_ref': 'SAW',
    },
    '11': {
        'code': '11',
        'name': 'Автоматическая сварка под флюсом с предварительной подваркой корня шва РДС',
        'abbr': 'АДФ (флюс) + подварка РДС',
        'iso_ref': 'SAW+SMAW',
    },
    '20': {
        'code': '20',
        'name': 'Электрошлаковая сварка',
        'abbr': 'ЭШС',
        'iso_ref': 'ESW',
    },
    '30': {
        'code': '30',
        'name': 'Ручная дуговая сварка покрытыми электродами',
        'abbr': 'РДС',
        'iso_ref': 'SMAW',
    },
    '31': {
        'code': '31',
        'name': 'Ручная дуговая сварка покрытыми электродами с подваркой корня шва',
        'abbr': 'РДС с подваркой корня',
        'iso_ref': 'SMAW (root pass)',
    },
    '32': {
        'code': '32',
        'name': 'Ручная дуговая сварка покрытыми электродами на стальной подкладке',
        'abbr': 'РДС на подкладке',
        'iso_ref': 'SMAW (backing)',
    },
    '40': {
        'code': '40',
        'name': 'Комбинированная сварка (корневую часть шва выполняют аргонодуговой сваркой)',
        'abbr': 'Комб. (корень АДС + РДС)',
        'iso_ref': 'TIG+SMAW',
    },
    '42': {
        'code': '42',
        'name': 'Комбинированная сварка на стальной подкладке (корень — аргонодуговая)',
        'abbr': 'Комб. на подкладке (АДС + РДС)',
        'iso_ref': 'TIG+SMAW (backing)',
    },
    '51': {
        'code': '51',
        'name': 'Аргонодуговая сварка неплавящимся электродом без присадочного материала',
        'abbr': 'АДС (без присадки)',
        'iso_ref': 'GTAW (autogenous)',
    },
    '52': {
        'code': '52',
        'name': 'Аргонодуговая сварка неплавящимся электродом с присадочным материалом',
        'abbr': 'АДС (с присадкой)',
        'iso_ref': 'GTAW (filler)',
    },
    '53': {
        'code': '53',
        'name': 'Аргонодуговая сварка плавящимся электродом',
        'abbr': 'АДС (плавящийся электрод)',
        'iso_ref': 'GMAW',
    },
    '60': {
        'code': '60',
        'name': 'Электронно-лучевая сварка',
        'abbr': 'ЭЛС',
        'iso_ref': 'EBW',
    },
}


def get_welding_process_choices():
    """Список кортежей для выпадающего списка способов сварки."""
    return [(code, f'{code} — {info["name"]}') for code, info in WELDING_PROCESSES.items()]


def get_welding_process_choices_for_joint(joint_code: str):
    """
    Допустимые способы сварки для типа соединения по ГОСТ Р 59023.2-2020.

    Возвращает только коды из поля methods соответствующей строки таблицы.
    """
    info = JOINT_TYPES.get(joint_code, {})
    allowed = info.get('methods', [])
    choices = [('', '— Выберите способ сварки —')]
    for code, label in get_welding_process_choices():
        if code in allowed:
            choices.append((code, label))
    return choices


# Изображения швов в разрезе (столбец «шва сварного соединения», таблицы ГОСТ Р 59023.2-2020)
JOINT_IMAGES = {
    'С-1': 'gost/С_1.gif',
    'С-1-1': 'gost/С_1_1.gif',
    'С-3': 'gost/С_3.gif',
    'С-4': 'gost/С_4.gif',
    'С-5': 'gost/С_5.gif',
    'С-6': 'gost/С_6.gif',
    'С-7': 'gost/С_7.gif',
    'С-11': 'gost/С_11.gif',
    'С-12': 'gost/С_12.gif',
    'С-13': 'gost/С_13.gif',
    'С-14': 'gost/С_14.gif',
    'С-15': 'gost/С_15.gif',
    'С-16': 'gost/С_16.gif',
    'С-17': 'gost/С_17.gif',
    'С-18': 'gost/С_18.gif',
    'С-19': 'gost/С_19.gif',
    'С-21': 'gost/С_21.gif',
    'С-22': 'gost/С_22.gif',
    'С-22-1': 'gost/С_22_1.gif',
    'С-25': 'gost/С_25.gif',
    'С-27': 'gost/С_27.gif',
    'С-42': 'gost/С_42.gif',
    'У-1': 'gost/У_1.gif',
    'У-10': 'gost/У_10.gif',
    'Т-1': 'gost/Т_1.gif',
    'Т-2': 'gost/Т_2.gif',
}


def _welds_static_dir() -> Path:
    return Path(__file__).resolve().parent.parent / 'static' / 'img' / 'welds'


def _gost_image_stem(joint_code: str) -> str:
    return joint_code.replace('-', '_')


def _image_path_variants(rel_path: str) -> list[str]:
    """Варианты png/gif для одного и того же эскиза ГОСТ."""
    if not rel_path:
        return []
    variants = [rel_path]
    if rel_path.endswith('.png'):
        variants.append(rel_path[:-4] + '.gif')
    elif rel_path.endswith('.gif'):
        variants.append(rel_path[:-4] + '.png')
    return variants


def _joint_image_code_aliases(joint_code: str) -> list[str]:
    """Альтернативные коды для поиска эскиза (ТС-1 → С-1, ТУ-3 → У-3)."""
    aliases = [joint_code]
    if joint_code.startswith('ТС-'):
        aliases.append('С-' + joint_code[3:])
    elif joint_code.startswith('ТУ-'):
        aliases.append('У-' + joint_code[3:])
    return aliases


def _joint_image_candidates(joint_code: str) -> list[str]:
    seen: set[str] = set()
    candidates: list[str] = []

    def add(path: str) -> None:
        for variant in _image_path_variants(path):
            if variant and variant not in seen:
                seen.add(variant)
                candidates.append(variant)

    for code in _joint_image_code_aliases(joint_code):
        add(JOINT_IMAGES.get(code, '') or '')
        add(JOINT_TYPES.get(code, {}).get('sketch', '') or '')
        for ext in ('gif', 'png'):
            add(f'gost/{_gost_image_stem(code)}.{ext}')

    return candidates


def get_joint_image_path(joint_code: str) -> str:
    """Относительный путь к изображению шва (от static/img/welds/)."""
    base = _welds_static_dir()
    for candidate in _joint_image_candidates(joint_code):
        if (base / candidate).exists():
            return candidate
    return ''


# ------------------------------------------------------------------
# Типы сварных соединений
#
# Структура:
#   code:     условное обозначение (С-1, С-1-1, У-1, Т-1, ...)
#   name:     краткое описание типа соединения
#   joint_type: 'butt' (С), 'corner' (У), 'tee' (Т)
#   material: 'perlit' | 'austenite' | 'titanium' | 'aluminum'
#   methods:  список кодов допустимых способов сварки
#   groove:   тип разделки кромок (краткое описание)
#   sketch:   имя SVG-файла с эскизом (из static/img/welds/)
#   dimensions: список кортежей (S_min, S_max, e_nom, g_nom)
#     S — номинальная толщина стенки, мм
#     e — ширина шва, мм (номинальное значение из таблицы)
#     g — высота усиления, мм (номинальное значение)
# ------------------------------------------------------------------

JOINT_TYPES = {
    # ============================================================
    # СТЫКОВЫЕ СОЕДИНЕНИЯ ПЕРЛИТНЫХ И ВЫСОКОХРОМИСТЫХ СТАЛЕЙ
    # ============================================================

    'С-1': {
        'code': 'С-1',
        'name': 'Стыковое, без разделки кромок (тонкие стенки)',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'Без разделки',
        'methods': ['53', '10'],
        'sketch': 'weld_C1.svg',
        # (S_min, S_max, e_ширина_шва_мм, g_усиление_мм)
        'dimensions': [
            (3.0,  4.0,   8.0,  1.5),
            (4.0,  5.0,  10.0,  1.5),
            (5.0,  9.0,  12.0,  2.0),
            (9.0,  14.0, 20.0,  2.0),
            (14.0, 20.0, 22.0,  2.5),
        ],
    },
    'С-1-1': {
        'code': 'С-1-1',
        'name': 'Стыковое, без разделки, на остающейся подкладке',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'Без разделки (комбинированная/аргонодуговая)',
        'methods': ['40', '51', '52'],
        'sketch': 'weld_C1_1.svg',
        'dimensions': [
            (3.0,  4.0,  6.0,  1.0),
            (4.0,  5.0,  7.0,  1.0),
            (5.0,  6.0,  8.0,  1.5),
            (6.0,  8.0, 10.0,  1.5),
        ],
    },
    'С-3': {
        'code': 'С-3',
        'name': 'Стыковое, V-образная разделка, флюс с подваркой / РДС',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'V-образная (двусторонняя)',
        'methods': ['11', '31'],
        'sketch': 'weld_C3.svg',
        'gost_table': '9.6',
        'bead_mode': 'dual',
        # табл. 9.6: e, g — лицевой валик; e1, g1 — по эскизу (gost_59023_sketch_beads)
        'dimensions': [
            (3.0,  5.0,   8.0,  2.0,  0.5,  3.5,  2.0),
            (5.0,  8.0,  12.0,  2.0),
            (8.0, 11.0,  16.0,  2.0),
            (11.0, 14.0,  19.0,  2.0),
            (14.0, 17.0,  22.0,  2.5,  0.5,  4.5,  6.0),
            (17.0, 20.0,  26.0,  2.5,  0.5,  4.5),
            (20.0, 24.0,  30.0,  2.5,  0.5,  4.5),
            (24.0, 28.0,  34.0,  3.0,  0.5,  5.0,  8.0),
            (28.0, 32.0,  38.0,  3.0,  0.5,  5.0),
            (32.0, 36.0,  42.0,  3.0,  0.5,  5.0),
            (36.0, 40.0,  47.0,  3.0,  0.5,  5.0),
        ],
    },
    'С-4': {
        'code': 'С-4',
        'name': 'Стыковое, V-образная разделка, флюс/РДС (средние толщины)',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'V-образная (одностороняя)',
        'methods': ['10', '30'],
        'sketch': 'weld_C4.svg',
        'dimensions': [
            (20.0, 22.0, 15.0, 2.0),
            (22.0, 25.0, 17.0, 2.0),
            (25.0, 30.0, 19.0, 2.0),
        ],
    },
    'С-5': {
        'code': 'С-5',
        'name': 'Стыковое, V-образная разделка, флюс (большие толщины)',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'V-образная (большие толщины)',
        'methods': ['10'],
        'sketch': 'weld_C5.svg',
        'gost_table': '9.8',
        'bead_mode': 'dual',
        'dimensions': [
            (30.0, 34.0, 32.0, 2.5, 0.0, 5.0, 6.0),
            (34.0, 36.0, 34.0, 2.5, 1.0, 4.0),
            (36.0, 38.0, 38.0, 2.5),
            (38.0, 40.0, 39.0, 2.5),
            (40.0, 42.0, 42.0, 3.0, 0.5, 5.5, 8.0),
            (42.0, 45.0, 44.0, 3.0),
            (45.0, 50.0, 47.0, 3.0, 1.0, 5.0),
            (50.0, 55.0, 50.0, 3.0),
            (55.0, 60.0, 53.0, 3.0),
            (60.0, 65.0, 56.0, 3.0),
            (65.0, 70.0, 59.0, 3.0),
            (70.0, 75.0, 63.0, 3.5, 1.0, 6.0, 10.0),
            (75.0, 80.0, 66.0, 3.5),
        ],
    },
    'С-6': {
        'code': 'С-6',
        'name': 'Стыковое, V-образная разделка, флюс (большие толщины 50+)',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'V-образная (50+ мм)',
        'methods': ['10'],
        'sketch': 'weld_C6.svg',
        'dimensions': [
            (50.0,  55.0, 34.0, 2.5),
            (55.0,  60.0, 35.0, 2.5),
            (60.0, 100.0, 37.0, 2.5),
        ],
    },
    'С-7': {
        'code': 'С-7',
        'name': 'Стыковое, X-образная разделка, флюс (100+ мм)',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'X-образная',
        'methods': ['10'],
        'sketch': 'weld_C7.svg',
        'dimensions': [
            (100.0, 120.0, 15.0, 2.5),
            (120.0, 200.0, 20.0, 2.5),
        ],
    },
    'С-14': {
        'code': 'С-14',
        'name': 'Стыковое, без разделки, РДС/аргонодуговая (тонкие)',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'Без разделки',
        'methods': ['30', '53'],
        'sketch': 'weld_C14.svg',
        'gost_table': '9.20',
        'bead_mode': 'dual',
        'dimensions': [
            (2.0, 2.0, 7.0, 1.5, 0.5, 2.5, 2.0),
            (3.0, 3.0, 8.0, 1.5, 0.5, 2.5),
            (4.0, 4.0, 9.0, 1.5, 0.5, 2.5, 3.0),
        ],
    },
    'С-15': {
        'code': 'С-15',
        'name': 'Стыковое, V-образная разделка, РДС/комбинированная',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'V-образная',
        'methods': ['31', '40'],
        'sketch': 'weld_C15.svg',
        'gost_table': '9.20',
        'bead_mode': 'dual',
        'dimensions': [
            (3.0, 3.0, 10.0, 2.0, 0.5, 3.0, 3.0),
            (4.0, 4.0, 11.0, 2.0, 1.0, 3.0),
            (5.0, 5.0, 12.0, 2.0, 0.5, 3.5),
            (6.0, 6.0, 15.0, 2.0, 0.5, 3.5, 4.0),
        ],
    },
    'С-16': {
        'code': 'С-16',
        'name': 'Стыковое, на стальной подкладке (РДС/АДС/АДФ)',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'V-образная на подкладке',
        'methods': ['32', '42', '53'],
        'sketch': 'weld_C16.svg',
        'dimensions': [
            (4.0,  6.0, 12.0, 2.0),
            (6.0,  8.0, 15.0, 2.0),
            (8.0, 12.0, 18.0, 2.0),
        ],
    },
    'С-17': {
        'code': 'С-17',
        'name': 'Стыковое, V-образная разделка, комбинированная/РДС',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'V-образная',
        'methods': ['31', '40'],
        'sketch': 'weld_C17.svg',
        'gost_table': '9.22',
        'bead_mode': 'dual',
        'dimensions': [
            (5.0, 5.0, 12.0, 2.0, 0.5, 3.0, 3.0),
            (7.0, 7.0, 15.0, 2.0, 0.5, 3.5, 4.0),
            (10.0, 10.0, 19.0, 3.0),
            (15.0, 15.0, 27.0, 2.5, 0.5, 4.5, 5.0),
            (20.0, 20.0, 34.0, 2.5, 0.5, 5.0, 6.0),
            (25.0, 25.0, 42.0, 2.5, 0.5, 5.0, 8.0),
            (30.0, 30.0, 49.0, 3.0, 0.5, 5.5),
        ],
    },
    'С-18': {
        'code': 'С-18',
        'name': 'Стыковое, V-образная разделка, РДС/комбинированная (ср. толщины)',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'V-образная',
        'methods': ['30', '40'],
        'sketch': 'weld_C18.svg',
        'dimensions': [
            (14.0, 16.0, 16.0, 2.0),
            (16.0, 18.0, 17.0, 2.0),
            (18.0, 25.0, 19.0, 2.0),
        ],
    },
    'С-19': {
        'code': 'С-19',
        'name': 'Стыковое, электрошлаковая сварка',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'Специальная (ЭШС)',
        'methods': ['20'],
        'sketch': 'weld_C19.svg',
        'dimensions': [
            (20.0,  34.0, 22.0, 2.5),
            (35.0,  80.0, 26.0, 3.0),
            (81.0, 300.0, 30.0, 3.5),
        ],
    },
    'С-21': {
        'code': 'С-21',
        'name': 'Стыковое, без разделки, аргонодуговая (ультратонкие)',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'Без разделки',
        'methods': ['51', '52'],
        'sketch': 'weld_C21.svg',
        'gost_table': '9.26',
        'bead_mode': 'dual',
        'dimensions': [
            (1.0, 1.0, 4.0, 1.0, 0.0, 2.0, 2.0),
            (2.0, 2.0, 5.0, 1.0, 0.0, 1.5),
        ],
    },
    'С-22': {
        'code': 'С-22',
        'name': 'Стыковое, комбинированная/аргонодуговая (тонкостенные)',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'V-образная',
        'methods': ['40', '52'],
        'sketch': 'weld_C22.svg',
        'gost_table': '9.26',
        'bead_mode': 'dual',
        'dimensions': [
            (2.0, 2.0, 7.0, 1.5, 0.0, 2.5, 2.0),
            (3.0, 3.0, 10.0, 2.5, 0.5, 3.5),
        ],
    },
    'С-22-1': {
        'code': 'С-22-1',
        'name': 'Стыковое, V-образная разделка, комбинированная/аргонодуговая (Dн ≤ 750 мм)',
        'joint_type': 'butt',
        'material': 'austenite',
        'groove': 'V-образная (45°±2°)',
        'methods': ['40', '52', '53'],
        'sketch': 'weld_C22_1.svg',
        'gost_table': '9.29',
        # Табл. 9.29 ГОСТ Р 59023.2-2020: (S, e, g±, e_tol)
        'dimensions': [
            (1.5, 1.5, 6.0, 1.0, 0.5, 1.5, 2.0),
            (2.0, 2.0, 7.0, 1.0, 0.5, 1.5, 2.0),
            (2.5, 2.5, 8.0, 1.0, 0.5, 1.5, 3.0),
            (3.0, 3.0, 9.0, 1.0, 0.5, 1.5, 3.0),
            (3.5, 3.5, 10.0, 1.0, 0.5, 1.5, 3.0),
        ],
    },
    'С-25': {
        'code': 'С-25',
        'name': 'Стыковое, V-образная разделка, комбинированная/аргонодуговая',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'V-образная',
        'methods': ['40', '52'],
        'sketch': 'weld_C25.svg',
        'gost_table': '9.34',
        'bead_mode': 'dual',
        'dimensions': [
            (6.0,  6.0, 15.0, 2.0, 0.0, 4.0, 4.0),
            (8.0,  8.0, 16.0, 2.0, 0.0, 3.0),
            (10.0, 10.0, 18.0, 2.5, 0.5, 4.5),
            (12.0, 12.0, 20.0, 2.5, 0.5, 4.5, 5.0),
            (14.0, 14.0, 21.0, 2.5, 0.5, 4.5),
            (16.0, 16.0, 22.0, 2.5, 1.0, 4.5),
            (18.0, 18.0, 23.0, 2.5, 1.0, 4.0),
            (20.0, 20.0, 24.0, 2.5, 1.0, 4.0),
            (22.0, 22.0, 26.0, 2.5),
            (25.0, 25.0, 28.0, 2.5),
            (28.0, 28.0, 30.0, 2.5, 0.5, 5.0, 6.0),
            (30.0, 30.0, 32.0, 2.5, 1.0, 4.0),
        ],
    },
    'С-27': {
        'code': 'С-27',
        'name': 'Стыковое, V-образная разделка, РДС (большие толщины)',
        'joint_type': 'butt',
        'material': 'perlit',
        'groove': 'V-образная',
        'methods': ['30', '40'],
        'sketch': 'weld_C27.svg',
        'dimensions': [
            (38.0, 40.0, 27.0, 2.5),
            (40.0, 50.0, 28.0, 2.5),
        ],
    },

    # ============================================================
    # УГЛОВЫЕ СОЕДИНЕНИЯ ПЕРЛИТНЫХ СТАЛЕЙ
    # ============================================================

    'У-1': {
        'code': 'У-1',
        'name': 'Угловое, V-образная разделка, флюс/РДС',
        'joint_type': 'corner',
        'material': 'perlit',
        'groove': 'V-образная разделка одной детали',
        'methods': ['11', '31'],
        'sketch': 'weld_U1.svg',
        'dimensions': [
            (10.0, 12.0, 19.0, 2.0),
            (12.0, 14.0, 22.0, 2.5),
            (14.0, 20.0, 26.0, 2.5),
        ],
    },
    'У-10': {
        'code': 'У-10',
        'name': 'Угловое, V-образная разделка, комбинированная',
        'joint_type': 'corner',
        'material': 'perlit',
        'groove': 'V-образная',
        'methods': ['40'],
        'sketch': 'weld_U10.svg',
        'dimensions': [
            (22.0, 24.0, 36.0, 2.0),
            (24.0, 26.0, 39.0, 2.0),
            (26.0, 30.0, 41.0, 2.0),
        ],
    },

    # ============================================================
    # ТАВРОВЫЕ СОЕДИНЕНИЯ ПЕРЛИТНЫХ СТАЛЕЙ
    # ============================================================

    'Т-1': {
        'code': 'Т-1',
        'name': 'Тавровое, с V-образной разделкой, флюс/РДС',
        'joint_type': 'tee',
        'material': 'perlit',
        'groove': 'V-образная разделка',
        'methods': ['11', '31'],
        'sketch': 'weld_T1.svg',
        'dimensions': [
            (4.0,  6.0,  7.0, 4.0),
            (6.0,  8.0,  9.0, 4.0),
            (8.0, 12.0, 11.0, 4.0),
        ],
    },
    'Т-2': {
        'code': 'Т-2',
        'name': 'Тавровое, V-образная разделка, флюс/РДС (большие толщины)',
        'joint_type': 'tee',
        'material': 'perlit',
        'groove': 'V-образная разделка',
        'methods': ['10', '30'],
        'sketch': 'weld_T2.svg',
        'dimensions': [
            (10.0, 15.0,  8.0, 4.0),
            (15.0, 25.0, 12.0, 4.0),
            (25.0, 50.0, 16.0, 6.0),
        ],
    },

    # ============================================================
    # СТЫКОВЫЕ СОЕДИНЕНИЯ АУСТЕНИТНЫХ СТАЛЕЙ
    # (Tables 9.21-9.66 — перлит/аустенит)
    # ============================================================

    'С-11': {
        'code': 'С-11',
        'name': 'Стыковое ауст., V-образная разделка, комбинированная/аргонодуговая',
        'joint_type': 'butt',
        'material': 'austenite',
        'groove': 'V-образная',
        'methods': ['40', '52'],
        'sketch': 'weld_C11.svg',
        'dimensions': [
            (14.0, 16.0, 15.0, 2.0),
            (16.0, 18.0, 16.0, 2.0),
            (18.0, 25.0, 17.0, 2.0),
        ],
    },
    'С-12': {
        'code': 'С-12',
        'name': 'Стыковое ауст., V-образная разделка, флюс/РДС',
        'joint_type': 'butt',
        'material': 'austenite',
        'groove': 'V-образная',
        'methods': ['11', '30'],
        'sketch': 'weld_C12.svg',
        'gost_table': '9.18',
        'bead_mode': 'dual',
        'dimensions': [
            (30.0, 32.0, 32.0, 2.5, 0.0, 5.0, 6.0),
            (35.0, 35.0, 35.0, 2.5),
            (40.0, 40.0, 38.0, 2.5, 1.0, 4.0),
            (45.0, 45.0, 43.0, 3.0, 0.5, 5.5, 8.0),
            (50.0, 50.0, 46.0, 3.0),
            (55.0, 55.0, 53.0, 3.0, 1.0, 5.0),
            (60.0, 60.0, 56.0, 3.0),
        ],
    },
    'С-13': {
        'code': 'С-13',
        'name': 'Стыковое ауст., V/X-образная разделка, флюс/РДС (большие толщины)',
        'joint_type': 'butt',
        'material': 'austenite',
        'groove': 'V-образная',
        'methods': ['11', '30'],
        'sketch': 'weld_C13.svg',
        'gost_table': '9.19',
        'bead_mode': 'dual',
        'dimensions': [
            (60.0, 60.0, 48.0, 3.0, 0.5, 5.5, 8.0),
            (65.0, 65.0, 50.0, 3.0),
            (70.0, 70.0, 52.0, 3.0, 1.0, 5.0),
            (75.0, 75.0, 54.0, 3.0),
            (80.0, 80.0, 56.0, 3.0),
            (90.0, 90.0, 60.0, 3.0),
            (100.0, 100.0, 66.0, 3.5, 1.0, 6.0, 10.0),
            (110.0, 110.0, 70.0, 3.5),
            (120.0, 120.0, 74.0, 3.5),
            (130.0, 130.0, 78.0, 4.0, 1.0, 7.0, 12.0),
            (140.0, 140.0, 82.0, 4.0),
        ],
    },
    'С-42': {
        'code': 'С-42',
        'name': 'Стыковое ауст., V-образная разделка, комбинированная (малые толщины)',
        'joint_type': 'butt',
        'material': 'austenite',
        'groove': 'V-образная',
        'methods': ['40', '52'],
        'sketch': 'weld_C42.svg',
        'dimensions': [
            (4.0,  5.0, 10.0, 1.0),
            (5.0,  6.0, 11.0, 1.0),
            (6.0,  8.0, 12.0, 1.5),
        ],
    },
}

from normative.gost_59023_joint_supplement import (  # noqa: E402
    SUPPLEMENT_JOINT_IMAGES,
    SUPPLEMENT_JOINT_TYPES,
)

JOINT_TYPES.update(SUPPLEMENT_JOINT_TYPES)
JOINT_IMAGES.update(SUPPLEMENT_JOINT_IMAGES)

from normative.gost_59023_extended_joints import (  # noqa: E402
    JOINT_TYPES_EXT,
    MATERIAL_VARIANTS,
)
from normative.gost_59023_sketch_beads import get_sketch_inner_bead  # noqa: E402
from normative.gost_59023_rtf_dimensions import RTF_DIMENSIONS  # noqa: E402
from normative.gost_59023_table_catalog import (  # noqa: E402
    GOST_SECTIONS,
    TABLE_CATALOG,
)

JOINT_TYPES.update(JOINT_TYPES_EXT)

for _code, _dims in RTF_DIMENSIONS.items():
    if _code in JOINT_TYPES and not JOINT_TYPES[_code].get('dimensions'):
        JOINT_TYPES[_code]['dimensions'] = _dims

# Индекс таблиц ГОСТ: (код, material_scope) → запись TABLE_CATALOG
JOINT_TABLE_INDEX: dict[tuple[str, str], dict] = {}
for _entry in TABLE_CATALOG:
    for _code in _entry.get('joint_codes', []):
        JOINT_TABLE_INDEX[(_code, _entry['material_scope'])] = _entry

_SECTION_TABLE_SETS = {
    '5': set(GOST_SECTIONS.get('section_5_steel', [])),
    '6': set(GOST_SECTIONS.get('section_6_austenite', [])),
    '7': set(GOST_SECTIONS.get('section_7_titanium_sheet', []))
         | set(GOST_SECTIONS.get('section_7_titanium_tube', [])),
    '8': set(GOST_SECTIONS.get('section_8_aluminum', [])),
}

JOINT_MATERIAL_ORDER = ('perlit', 'austenite', 'titanium', 'aluminum')
JOINT_TYPE_ORDER = ('butt', 'corner', 'tee')
TITANIUM_SCOPE_ORDER = ('titanium_sheet', 'titanium_tube')
ALUMINUM_SCOPE_ORDER = ('aluminum_butt', 'aluminum_corner_tee')

GOST_ALUMINUM_BUTT_TABLES = frozenset(
    GOST_SECTIONS.get('section_8_aluminum', [])[:9],
)
GOST_ALUMINUM_CORNER_TEE_TABLES = frozenset(
    GOST_SECTIONS.get('section_8_aluminum', [])[9:],
)

# Применимость типов соединений по разделам ГОСТ Р 59023.2-2020 (п. 5–8)
GOST_MATERIAL_SECTIONS = {
    'perlit': {
        'section': '5',
        'label': 'п. 5 — перлитные и высокохромистые стали',
    },
    'austenite': {
        'section': '6',
        'label': 'п. 6 — аустенитные стали и сплавы Fe-Ni',
    },
    'titanium': {
        'section': '7',
        'label': 'п. 7 — титановые сплавы',
        'sheet': 'п. 7 — листовые детали из титановых сплавов (табл. 9.67–9.84)',
        'tube': 'п. 7 — трубные детали из титановых сплавов (табл. 9.85–9.99)',
    },
    'aluminum': {
        'section': '8',
        'label': 'п. 8 — алюминиевые сплавы',
        'butt': 'п. 8 — стыковые соединения из алюминиевых сплавов (табл. 9.100–9.108)',
        'corner_tee': (
            'п. 8 — угловые, тавровые и торцевые соединения '
            'из алюминиевых сплавов (табл. 9.109–9.122)'
        ),
    },
}

JOINT_GROUP_LABELS = {
    ('perlit', 'butt'): '— Стыковые, перлитные стали (п. 5) —',
    ('perlit', 'corner'): '— Угловые, перлитные стали (п. 5) —',
    ('perlit', 'tee'): '— Тавровые, перлитные стали (п. 5) —',
    ('austenite', 'butt'): '— Стыковые, аустенитные стали (п. 6) —',
    ('austenite', 'corner'): '— Угловые, аустенитные стали (п. 6) —',
    ('austenite', 'tee'): '— Тавровые, аустенитные стали (п. 6) —',
    ('titanium', 'titanium_sheet', 'butt'): (
        '— Титан: стыковые, листовые детали (п. 7, табл. 9.67–9.84) —'
    ),
    ('titanium', 'titanium_sheet', 'corner'): (
        '— Титан: угловые, листовые детали (п. 7, табл. 9.67–9.84) —'
    ),
    ('titanium', 'titanium_tube', 'butt'): (
        '— Титан: стыковые, трубные детали (п. 7, табл. 9.85–9.99) —'
    ),
    ('titanium', 'titanium_tube', 'corner'): (
        '— Титан: угловые/тавровые, трубные детали (п. 7, табл. 9.85–9.99) —'
    ),
    ('aluminum', 'aluminum_butt'): (
        '— Алюминий: стыковые (п. 8, табл. 9.100–9.108) —'
    ),
    ('aluminum', 'aluminum_corner_tee'): (
        '— Алюминий: угловые, тавровые и торцевые (п. 8, табл. 9.109–9.122) —'
    ),
}


def _table_num(table_ref: str) -> float | None:
    try:
        return float(table_ref.replace('9.', ''))
    except (TypeError, ValueError):
        return None


def resolve_joint_list_scope(joint_code: str, info: dict) -> str:
    """
    Подгруппа п. 7–8 для группировки в списке типов соединений.

    п. 7: лист (9.67–9.84) / труба (9.85–9.99);
    п. 8: стыковые (9.100–9.108) / угловые, тавровые, торцевые (9.109–9.122).
    """
    material = info.get('material', 'perlit')
    if material == 'titanium':
        if joint_code.startswith(('ТС-', 'ТУ-')):
            return 'titanium_tube'
        table = info.get('gost_table', '')
        num = _table_num(table)
        if num is not None and 85 <= num <= 99:
            return 'titanium_tube'
        if num is not None and 67 <= num <= 84:
            return 'titanium_sheet'
        if (joint_code, 'titanium_tube') in JOINT_TABLE_INDEX:
            if (joint_code, 'titanium_sheet') not in JOINT_TABLE_INDEX:
                return 'titanium_tube'
        return 'titanium_sheet'
    if material == 'aluminum':
        table = info.get('gost_table', '')
        if table in GOST_ALUMINUM_BUTT_TABLES:
            return 'aluminum_butt'
        if table in GOST_ALUMINUM_CORNER_TEE_TABLES:
            return 'aluminum_corner_tee'
        num = _table_num(table)
        if num is not None:
            if num <= 108:
                return 'aluminum_butt'
            if num >= 109:
                return 'aluminum_corner_tee'
        if info.get('joint_type', 'butt') == 'butt':
            return 'aluminum_butt'
        return 'aluminum_corner_tee'
    return material


def get_joint_group_key(joint_code: str, info: dict) -> tuple:
    """Ключ optgroup для выпадающего списка типов соединений."""
    material = info.get('material', 'perlit')
    if material == 'titanium':
        scope = resolve_joint_list_scope(joint_code, info)
        joint_type = info.get('joint_type', 'butt')
        if scope == 'titanium_tube' and joint_type == 'tee':
            joint_type = 'corner'
        return (material, scope, joint_type)
    if material == 'aluminum':
        return (material, resolve_joint_list_scope(joint_code, info))
    return (material, info.get('joint_type', 'butt'))


def joint_group_key_to_str(group_key: tuple) -> str:
    return '|'.join(str(part) for part in group_key)


def get_joint_scoped_applicability(joint_code: str, info: dict | None = None) -> str:
    """Применимость с учётом подраздела п. 7–8 (лист/труба, стыковые/угловые)."""
    info = info or JOINT_TYPES.get(joint_code, {})
    material = info.get('material', 'perlit')
    if material == 'titanium':
        scope = resolve_joint_list_scope(joint_code, info)
        return GOST_MATERIAL_SECTIONS['titanium'][scope.split('_', 1)[1]]
    if material == 'aluminum':
        scope = resolve_joint_list_scope(joint_code, info)
        key = 'butt' if scope == 'aluminum_butt' else 'corner_tee'
        return GOST_MATERIAL_SECTIONS['aluminum'][key]
    return get_joint_material_applicability(material)


def get_joint_applicability_for_display(joint_code: str, info: dict | None = None) -> str:
    """Применимость для подписи в UI — без «чужих» разделов п. 5–8."""
    info = info or JOINT_TYPES.get(joint_code, {})
    material = info.get('material', 'perlit')
    if material in ('titanium', 'aluminum'):
        return get_joint_scoped_applicability(joint_code, info)
    tables = get_joint_table_numbers(joint_code)
    labels = []
    if tables & _SECTION_TABLE_SETS['5']:
        labels.append(GOST_MATERIAL_SECTIONS['perlit']['label'])
    if tables & _SECTION_TABLE_SETS['6']:
        labels.append(GOST_MATERIAL_SECTIONS['austenite']['label'])
    return '; '.join(labels)


def get_joint_material_applicability(material: str) -> str:
    """Текст применимости типа соединения по п. 5–8 ГОСТ Р 59023.2-2020."""
    return GOST_MATERIAL_SECTIONS.get(material, {}).get('label', '')


def resolve_catalog_material_scope(joint_code: str, material_class: str | None) -> str:
    """Ключ material_scope в TABLE_CATALOG для кода и класса металла."""
    if joint_code.startswith(('ТС-', 'ТУ-')):
        return 'titanium_tube'
    if material_class == 'titanium':
        if (joint_code, 'titanium_tube') in JOINT_TABLE_INDEX:
            return 'titanium_tube'
        return 'titanium_sheet'
    if material_class == 'aluminum':
        return 'aluminum'
    return 'steel'


def get_joint_table_numbers(joint_code: str) -> set[str]:
    return {
        entry['table']
        for entry in TABLE_CATALOG
        if joint_code in entry.get('joint_codes', [])
    }


def get_joint_applicable_material_classes(joint_code: str) -> list[str]:
    """
    Классы металла (п. 5–8), для которых тип соединения допустим по таблицам ГОСТ.

    Используется для предупреждения о несоответствии материала объекта.
    """
    tables = get_joint_table_numbers(joint_code)
    classes: list[str] = []
    if tables & _SECTION_TABLE_SETS['5']:
        classes.append('perlit')
    if tables & _SECTION_TABLE_SETS['6']:
        classes.append('austenite')
    if tables & _SECTION_TABLE_SETS['7']:
        classes.append('titanium')
    if tables & _SECTION_TABLE_SETS['8']:
        classes.append('aluminum')
    if not classes:
        material = JOINT_TYPES.get(joint_code, {}).get('material')
        if material:
            classes.append(material)
    return classes


def get_joint_applicability_text(joint_code: str) -> str:
    """Применимость типа соединения по п. 5–8 на основании таблиц раздела 9."""
    tables = get_joint_table_numbers(joint_code)
    labels = []
    if tables & _SECTION_TABLE_SETS['5']:
        labels.append(GOST_MATERIAL_SECTIONS['perlit']['label'])
    if tables & _SECTION_TABLE_SETS['6']:
        labels.append(GOST_MATERIAL_SECTIONS['austenite']['label'])
    if tables & _SECTION_TABLE_SETS['7']:
        labels.append(GOST_MATERIAL_SECTIONS['titanium']['label'])
    if tables & _SECTION_TABLE_SETS['8']:
        labels.append(GOST_MATERIAL_SECTIONS['aluminum']['label'])
    return '; '.join(labels)


def resolve_joint_profile(
    joint_code: str,
    material_class: str | None = None,
) -> dict:
    """
    Профиль типа соединения с учётом класса металла (п. 5–8).

    Для кодов с вариантами (С-1 для стали/Ti/Al) выбирается таблица
    соответствующего material_scope.
    """
    base = dict(JOINT_TYPES.get(joint_code, {}))
    if not base:
        return base
    scope = resolve_catalog_material_scope(joint_code, material_class)
    catalog_entry = JOINT_TABLE_INDEX.get((joint_code, scope))
    if catalog_entry:
        base = dict(base)
        base['gost_table'] = catalog_entry['table'].replace('9.', '9.')
        if catalog_entry.get('methods'):
            base['methods'] = list(catalog_entry['methods'])
    base['material_scope'] = scope
    base['applicability'] = get_joint_applicability_for_display(joint_code, base)
    if material_class in ('titanium', 'aluminum'):
        base['applicability'] = get_joint_scoped_applicability(joint_code, base)
    if joint_code in MATERIAL_VARIANTS:
        base['material_variants'] = MATERIAL_VARIANTS[joint_code]
    sketch_bead = get_sketch_inner_bead(joint_code)
    if sketch_bead:
        base['sketch_inner_bead'] = sketch_bead
    return base


def format_joint_choice_label(code: str, info: dict) -> str:
    """Подпись пункта списка типов соединений с указанием применимости."""
    table_ref = info.get('gost_table')
    table_suffix = f', табл. {table_ref}' if table_ref else ''
    applicability = info.get('applicability') or get_joint_applicability_for_display(code, info)
    applicability_suffix = f' [{applicability}]' if applicability else ''
    return (
        f"{code} — {info['name']}{table_suffix}{applicability_suffix}"
    )


def _joint_code_sort_key(code: str) -> tuple:
    m = re.match(r'^(ТС|ТУ|[СУТ])-(\d+(?:-\d+)?)$', code)
    if not m:
        return (code, 0, 0)
    prefix, num_part = m.group(1), m.group(2)
    parts = [int(p) for p in num_part.split('-')]
    return (prefix, parts[0], parts[1] if len(parts) > 1 else 0)


def _joint_sort_key(code: str) -> tuple:
    info = JOINT_TYPES.get(code, {})
    group = get_joint_group_key(code, info)
    material_idx = (
        JOINT_MATERIAL_ORDER.index(group[0])
        if group[0] in JOINT_MATERIAL_ORDER else 99
    )
    sub_idx = 99
    type_idx = 99
    if group[0] == 'titanium' and len(group) == 3:
        sub_idx = (
            TITANIUM_SCOPE_ORDER.index(group[1])
            if group[1] in TITANIUM_SCOPE_ORDER else 99
        )
        type_idx = (
            JOINT_TYPE_ORDER.index(group[2])
            if group[2] in JOINT_TYPE_ORDER else 99
        )
    elif group[0] == 'aluminum' and len(group) == 2:
        sub_idx = (
            ALUMINUM_SCOPE_ORDER.index(group[1])
            if group[1] in ALUMINUM_SCOPE_ORDER else 99
        )
    elif len(group) == 2:
        type_idx = (
            JOINT_TYPE_ORDER.index(group[1])
            if group[1] in JOINT_TYPE_ORDER else 99
        )
    table_num = _table_num(info.get('gost_table', '')) or 999.0
    return (material_idx, sub_idx, type_idx, table_num, _joint_code_sort_key(code))


def _enrich_joint_metadata() -> None:
    from normative.gost_59023_wall import get_joint_wall_meta

    for code, info in JOINT_TYPES.items():
        info['list_scope'] = resolve_joint_list_scope(code, info)
        info['group_key'] = joint_group_key_to_str(get_joint_group_key(code, info))
        info['applicability'] = get_joint_applicability_for_display(code, info)
        tables = get_joint_table_numbers(code)
        if tables and not info.get('gost_tables_all'):
            info['gost_tables_all'] = sorted(tables, key=lambda t: float(t.split('.')[1]))
        wall_meta = get_joint_wall_meta(code)
        info['has_internal_boring'] = wall_meta['has_internal_boring']
        info['s_equals_s1'] = wall_meta['s_equals_s1']
        info['wall_thickness_mode'] = wall_meta['wall_thickness_mode']
        info['wall_note'] = wall_meta['wall_note']
        if wall_meta['boring_rows']:
            info['boring_rows'] = wall_meta['boring_rows']
            info['boring_gost_table'] = wall_meta['boring_gost_table']


def get_joint_group_labels_for_ui() -> dict[str, str]:
    """Подписи optgroup для передачи в шаблон (JSON)."""
    return {joint_group_key_to_str(key): label for key, label in JOINT_GROUP_LABELS.items()}


ALL_JOINT_CODES = sorted(JOINT_TYPES.keys(), key=_joint_sort_key)
_enrich_joint_metadata()


def get_joint_thickness_ranges(joint_code: str) -> list[tuple[float, float]]:
    """Диапазоны номинальной толщины S из таблицы ГОСТ для типа соединения."""
    info = JOINT_TYPES.get(joint_code, {})
    return [(row[0], row[1]) for row in info.get('dimensions', [])]


def is_joint_thickness_allowed(joint_code: str, thickness_mm: float) -> bool:
    """True, если S попадает в один из рядов таблицы ГОСТ для данного типа."""
    ranges = get_joint_thickness_ranges(joint_code)
    if not ranges:
        return True
    return any(s_min <= thickness_mm <= s_max for s_min, s_max in ranges)


def format_joint_thickness_ranges(joint_code: str) -> str:
    """Краткая строка допустимых S для сообщения об ошибке (напр. «2; 3; 4 мм»)."""
    ranges = get_joint_thickness_ranges(joint_code)
    if not ranges:
        return ''
    parts = []
    for s_min, s_max in ranges:
        if abs(s_min - s_max) < 1e-9:
            parts.append(f'{s_min:g}'.replace('.', ','))
        else:
            parts.append(
                f'{s_min:g}–{s_max:g}'.replace('.', ',')
            )
    return '; '.join(parts) + ' мм'


def resolve_material_class(material: str = '', material_custom: str = '') -> str | None:
    if material == MATERIAL_TITANIUM:
        return 'titanium'
    if material == MATERIAL_ALUMINUM:
        return 'aluminum'
    grade = (material_custom or material or '').upper()
    austenite_markers = ('08Х', '12Х18', '10Х17', '03Х18', 'Х18', 'Х19')
    if any(marker in grade for marker in austenite_markers):
        return 'austenite'
    if material and material not in (MATERIAL_TITANIUM, MATERIAL_ALUMINUM):
        return 'perlit'
    return None


def iter_joint_codes(
    material_class: str | None = None,
    wall_thickness_mm: float | None = None,
) -> list[str]:
    codes = []
    for code in sorted(JOINT_TYPES.keys(), key=_joint_sort_key):
        info = JOINT_TYPES[code]
        if material_class and info.get('material') != material_class:
            continue
        if wall_thickness_mm is not None:
            dims = info.get('dimensions') or []
            if dims and not any(row[0] <= wall_thickness_mm <= row[1] for row in dims):
                continue
        codes.append(code)
    return codes


def get_joint_type_choices(
    material_class: str = None,
    wall_thickness_mm: float | None = None,
):
    """
    Возвращает список кортежей типов соединений для выпадающего списка.

    По умолчанию включает все типы из ГОСТ Р 59023.2-2020.
    Сортировка: класс металла → тип (С/У/Т) → таблица ГОСТ → код.
    В подписи каждого пункта — применимость по п. 5–8 стандарта.
    """
    choices = [('', '— Выберите тип сварного соединения —')]
    last_group = None
    for code in iter_joint_codes(material_class, wall_thickness_mm):
        info = JOINT_TYPES[code]
        group = get_joint_group_key(code, info)
        if group != last_group and len(choices) > 1:
            label = JOINT_GROUP_LABELS.get(group)
            if label:
                choices.append((f'__group_{code}__', label))
            last_group = group
        choices.append((code, format_joint_choice_label(code, info)))
    return choices


def get_joint_info(joint_code: str, material_class: str | None = None) -> dict:
    """Возвращает полную информацию о типе соединения."""
    from normative.gost_59023_wall import get_joint_wall_meta

    info = resolve_joint_profile(joint_code, material_class)
    if info:
        info['image'] = get_joint_image_path(joint_code)
        info.update(get_joint_wall_meta(joint_code))
    return info


# ------------------------------------------------------------------
# Ширина шва (e) — по таблицам ГОСТ Р 59023.2-2020
# ------------------------------------------------------------------

def _default_e_tolerance_mm(e_mm: float) -> float:
    """Типовой допуск ширины валика по таблицам ГОСТ Р 59023.2-2020."""
    if e_mm >= 10:
        return 4.0
    if e_mm >= 6:
        return 2.0
    return 1.5


def format_dimension_with_tolerance(value_mm: float, tolerance_mm: float) -> str:
    """Форматирует размер для техкарты: «15,0 ±4,0»."""
    return (
        f'{value_mm:.1f}'.replace('.', ',')
        + f' ±{tolerance_mm:.1f}'.replace('.', ',')
    )


def _parse_dimension_row(row: tuple, bead_mode: str = 'equal') -> dict:
    """
    Разбирает строку таблицы ГОСТ Р 59023.2-2020.

    Форматы:
        (S_min, S_max, e, g)
        (S_min, S_max, e, g, g_min, g_max)
        (S_min, S_max, e, e1, g, g_min, g_max) — отдельные e и e1
        (S_min, S_max, e, g, g_min, g_max, e_tol) — допуск e (табл. 9.29)
    """
    if len(row) < 4:
        raise ValueError(f'Некорректная строка dimensions: {row}')

    s_min, s_max, e = row[0], row[1], row[2]
    e_tol = None
    e1 = e
    g_nom = row[3]
    g_min = max(0.0, g_nom - 1.5)
    g_max = g_nom + 1.5

    if len(row) >= 7 and row[3] >= 4 and row[4] >= 0.5:
        # (S, e, e1, g, g_min, g_max)
        e1 = row[3]
        g_nom = row[4]
        g_min = row[5]
        g_max = row[6]
    elif len(row) >= 7:
        g_nom = row[3]
        g_min = row[4]
        g_max = row[5]
        e_tol = row[6]
    elif len(row) >= 6:
        g_nom = row[3]
        g_min = row[4]
        g_max = row[5]

    if bead_mode == 'equal':
        e1 = e
    elif bead_mode == 'outer_only':
        e1 = 0.0
    elif bead_mode == 'dual' and len(row) < 7:
        # Отдельный e1 задан в 7-элементной строке; иначе e1 не известен — берём e
        pass

    return {
        's_min': s_min,
        's_max': s_max,
        'e_mm': e,
        'e1_mm': e1,
        'g_nom': g_nom,
        'g_min_mm': g_min,
        'g_max_mm': g_max,
        'e_tol_mm': e_tol,
    }


def get_weld_width(
    joint_code: str,
    thickness_mm: float,
    material_class: str | None = None,
    *,
    outer_diameter_mm: float | None = None,
) -> dict:
    """
    Возвращает ширину шва (e), высоту усиления (g_nom, g_min, g_max)
    для заданного типа соединения и толщины стенки.

    Данные берутся из таблиц ГОСТ Р 59023.2-2020.
    Формат кортежа dimensions:
        4 элемента: (S_min, S_max, e, g_nom)  — g_min/g_max рассчитываются по умолчанию
        6 элементов: (S_min, S_max, e, g_nom, g_min, g_max) — точные значения
        7 элементов: (S_min, S_max, e, e1, g_nom, g_min, g_max) — e1 ≠ e
                     (S_min, S_max, e, g_nom, g_min, g_max, e_tol) — e_tol при g_nom < 4

    Для С-23-2 (табл. 9.30, с расточкой) при заданном Dн размеры берутся
    из строки типоразмера Dн×S.

    :param joint_code: условное обозначение соединения
    :param thickness_mm: номинальная толщина стенки S, мм
    :return: словарь с e_mm, g_nom, g_min_mm, g_max_mm, note
    """
    from normative.gost_59023_wall import (
        joint_has_internal_boring,
        lookup_gost_boring_row,
    )

    info = resolve_joint_profile(joint_code, material_class)
    if not info:
        return {
            'e_mm': None, 'g_nom': 2.0,
            'g_min_mm': 0.5, 'g_max_mm': 3.5,
            'note': f'Тип {joint_code} не найден в справочнике',
        }

    boring_row = None
    if joint_has_internal_boring(joint_code) and outer_diameter_mm:
        boring_row = lookup_gost_boring_row(
            joint_code, outer_diameter_mm, thickness_mm,
        )

    if boring_row and boring_row.get('e_mm'):
        e = float(boring_row['e_mm'])
        e1 = e
        e_tol = boring_row.get('e_tol_mm')
        g_nom = float(boring_row['g_nom']) if boring_row.get('g_nom') else 2.0
        g_min = max(0.0, g_nom - 1.5)
        g_max = g_nom + 1.5
        g1_nom = boring_row.get('g1_max_mm')
        g1_min = 0.0 if g1_nom is not None else None
        g1_max = g1_nom
        bead_mode = info.get('bead_mode', 'equal')
        match_row = (
            thickness_mm, thickness_mm, e, g_nom,
        )
        sketch_bead = None
        table_ref = info.get('gost_table') or '9.30'
        note = (
            f'По табл. {table_ref} ГОСТ Р 59023.2-2020 для {joint_code}, '
            f'Dн×S = {boring_row["dn_mm"]:g}×{boring_row["s_mm"]:g} мм, '
            f'S1 = {boring_row["s1_mm"]:g} мм'
        )
        if e_tol is None:
            e_tol = _default_e_tolerance_mm(e)
        e1_tol = e_tol
        e_max = round(e + e_tol, 1)
        e1_max = e_max
        return {
            'e_mm': e,
            'e_max_mm': e_max,
            'e1_mm': e1,
            'e1_max_mm': e1_max,
            'effective_e_mm': e,
            'effective_e_max_mm': e_max,
            'e_tol_mm': e_tol,
            'e1_tol_mm': e1_tol,
            'bead_mode': bead_mode,
            'e_display': format_dimension_with_tolerance(e, e_tol),
            'e1_display': format_dimension_with_tolerance(e1, e1_tol),
            'g_nom': g_nom,
            'g_min_mm': round(g_min, 1),
            'g_max_mm': round(g_max, 1),
            'g1_nom': g1_nom,
            'g1_min_mm': round(g1_min, 1) if g1_min is not None else None,
            'g1_max_mm': round(g1_max, 1) if g1_max is not None else None,
            'g1_display': (
                f'≤{g1_nom:g}'.replace('.', ',')
                if g1_nom is not None else None
            ),
            'sketch_bead_source': None,
            'g_display': (
                f'{g_nom:g}±{g_max - g_nom:g}'.replace('.', ',')
                if abs((g_max - g_nom) - (g_nom - g_min)) < 0.05 and g_nom > 0 else
                f'{g_nom:.1f} ({g_min:.1f}–{g_max:.1f})'.replace('.', ',')
            ),
            'note': note,
            'boring_row': boring_row,
        }

    dims = info.get('dimensions', [])
    match_row = None
    for row in dims:
        s_min, s_max = row[0], row[1]
        if s_min <= thickness_mm <= s_max:
            match_row = row
            break

    # Вне диапазона ГОСТ — не подставлять «ближайший» ряд молча (раньше С-14 + S=5
    # брало размеры ряда S=4 и писало «приближённо»).
    if match_row is None and dims:
        table_ref = info.get('gost_table', '')
        ranges_txt = format_joint_thickness_ranges(joint_code)
        table_part = f'табл. {table_ref} ' if table_ref else ''
        return {
            'e_mm': None,
            'e_max_mm': None,
            'e1_mm': None,
            'e1_max_mm': None,
            'effective_e_mm': None,
            'effective_e_max_mm': None,
            'e_tol_mm': None,
            'e1_tol_mm': None,
            'bead_mode': info.get('bead_mode', 'equal'),
            'e_display': '—',
            'e1_display': '—',
            'g_nom': None,
            'g_min_mm': None,
            'g_max_mm': None,
            'g_display': '—',
            'g1_nom': None,
            'g1_min_mm': None,
            'g1_max_mm': None,
            'g1_display': None,
            'out_of_range': True,
            'is_approximate': False,
            'note': (
                f'Для {joint_code} по {table_part}ГОСТ Р 59023.2-2020 '
                f'допустима толщина S: {ranges_txt}. '
                f'Задано S={thickness_mm:g} мм — вне диапазона.'
            ),
        }

    if match_row is None:
        return {
            'e_mm': None, 'g_nom': 2.0,
            'g_min_mm': 0.5, 'g_max_mm': 3.5,
            'note': 'Нет данных',
            'out_of_range': True,
        }

    bead_mode = info.get('bead_mode', 'equal')
    parsed = _parse_dimension_row(match_row, bead_mode)
    e = parsed['e_mm']
    e1 = parsed['e1_mm']
    e_tol = parsed['e_tol_mm']
    g_nom = parsed['g_nom']
    g_min = parsed['g_min_mm']
    g_max = parsed['g_max_mm']
    g1_nom = None
    g1_min = None
    g1_max = None

    sketch_bead = info.get('sketch_inner_bead') or get_sketch_inner_bead(joint_code)
    # Размеры с эскиза по умолчанию — числа без e1/g1 (см. gost_59023_sketch_beads)
    labeled_as_e1 = False
    labeled_as_g1 = False
    if bead_mode == 'dual' and sketch_bead:
        if e1 is None or abs(e1 - e) < 0.01:
            e1 = sketch_bead['e1_mm']
        g1_nom = sketch_bead.get('g1_nom')
        g1_min = sketch_bead.get('g1_min_mm')
        g1_max = sketch_bead.get('g1_max_mm')
        labeled_as_e1 = bool(sketch_bead.get('labeled_as_e1', False))
        labeled_as_g1 = bool(sketch_bead.get('labeled_as_g1', False))

    if e_tol is None:
        e_tol = _default_e_tolerance_mm(e)
    if sketch_bead and bead_mode == 'dual':
        e1_tol = sketch_bead.get('e1_tol_mm', _default_e_tolerance_mm(e1))
    else:
        e1_tol = _default_e_tolerance_mm(e1) if e1 else 0.0

    table_ref = info.get('gost_table', '')
    if table_ref:
        note = (
            f'По табл. {table_ref} ГОСТ Р 59023.2-2020 для {joint_code}, '
            f'S={thickness_mm} мм'
        )
    else:
        note = f'По таблице ГОСТ Р 59023.2-2020 для {joint_code}, S={thickness_mm} мм'
    if match_row[0] > thickness_mm or match_row[1] < thickness_mm:
        note = (
            f'Приближённо для {joint_code}, S={thickness_mm} мм '
            f'(ближайший диапазон {match_row[0]}–{match_row[1]} мм)'
        )

    e_max = round(e + e_tol, 1)
    e1_max = round(e1 + e1_tol, 1) if e1 else 0.0

    g_face_display = (
        f'{g_nom:g}±{g_max - g_nom:g}'.replace('.', ',')
        if abs((g_max - g_nom) - (g_nom - g_min)) < 0.05 and g_nom > 0 else
        f'{g_nom:.1f} ({g_min:.1f}–{g_max:.1f})'.replace('.', ',')
    )
    g1_display = None
    if g1_nom is not None:
        g1_tol = None
        if sketch_bead and sketch_bead.get('g1_tol_mm') is not None:
            g1_tol = float(sketch_bead['g1_tol_mm'])
        elif g1_max is not None:
            g1_tol = g1_max - g1_nom
        if g1_tol is not None:
            g1_display = format_dimension_with_tolerance(g1_nom, g1_tol)

    # e / e1: если ширина обратного валика с эскиза без обозначения e1 — «по эскизу»
    e_face_display = format_dimension_with_tolerance(e, e_tol)
    e1_raw = format_dimension_with_tolerance(e1, e1_tol) if e1 else None
    if e1_raw and sketch_bead and not labeled_as_e1:
        e1_display = f'по эскизу: {e1_raw}'
        e_label_inner = 'внутренней поверхности (по эскизу)'
    elif e1_raw and labeled_as_e1:
        e1_display = f'e1 = {e1_raw}'
        e_label_inner = 'внутренней поверхности (e1)'
    else:
        e1_display = e1_raw or '—'
        e_label_inner = 'внутренней поверхности'

    # g / g1: не писать «g=g1», если на эскизе нет обозначения g1
    if g1_display and labeled_as_g1:
        if (
            abs(g_nom - g1_nom) < 0.05
            and g1_max is not None
            and abs(g_max - g1_max) < 0.05
            and g1_min is not None
            and abs(g_min - g1_min) < 0.05
        ):
            g_display = f'g = g1 = {g_face_display}'
            g_label = '4.2.3. Высота валика усиления (g = g1)'
        else:
            g_display = f'g = {g_face_display}; g1 = {g1_display}'
            g_label = '4.2.3. Высота валика усиления (g, g1)'
    elif g1_display and not labeled_as_g1:
        g_display = (
            f'g = {g_face_display}; '
            f'обратный валик (по эскизу) = {g1_display}'
        )
        g_label = '4.2.3. Высота валика усиления (g)'
    else:
        g_display = g_face_display
        g_label = '4.2.3. Высота валика усиления (g)'

    return {
        'e_mm': e,
        'e_max_mm': e_max,
        'e1_mm': e1,
        'e1_max_mm': e1_max,
        'effective_e_mm': max(e, e1),
        'effective_e_max_mm': max(e_max, e1_max),
        'e_tol_mm': e_tol,
        'e1_tol_mm': e1_tol,
        'bead_mode': bead_mode,
        'e_display': e_face_display,
        'e1_display': e1_display,
        'e_label_inner': e_label_inner,
        'labeled_as_e1': labeled_as_e1,
        'g_nom': g_nom,
        'g_min_mm': round(g_min, 1),
        'g_max_mm': round(g_max, 1),
        'g1_nom': g1_nom,
        'g1_min_mm': round(g1_min, 1) if g1_min is not None else None,
        'g1_max_mm': round(g1_max, 1) if g1_max is not None else None,
        'g1_display': g1_display,
        'labeled_as_g1': labeled_as_g1,
        'sketch_bead_source': sketch_bead.get('source') if sketch_bead else None,
        'g_face_display': g_face_display,
        'g_display': g_display,
        'g_label': g_label,
        'note': note,
    }


# ------------------------------------------------------------------
# Ширина околошовной зоны и контролируемой зоны
# ------------------------------------------------------------------
# По ГОСТ Р 50.05.07-2018 п. 6.3.13 и НП-105-18:
# Ширина снимка должна обеспечивать изображение шва + прилегающей зоны:
# - S ≤ 5 мм  → не менее ширины шва (e)
# - 5 < S ≤ 20 мм → не менее ширины свариваемых кромок (примерно e + 5 мм с кажд. стороны)
# - S > 20 мм → не менее 20 мм с каждой стороны
# - Для ЭШС   → не менее 50 мм
#
# Ширина ОКОЛОШОВНОЙ ЗОНЫ (a) для РГК (НП-105-18):
# Стандартное значение a = 5 мм для категорий I–III
# ------------------------------------------------------------------

HAZ_WIDTH_MM = 5.0   # Ширина околошовной зоны для РГК, мм

# Соединения и способы сварки с подкладкой (остающейся подкладкой / кольцом)
BACKING_JOINT_CODES = frozenset({'С-1-1', 'С-16'})
BACKING_WELDING_METHODS = frozenset({'32', '42'})


def joint_uses_backing(joint_code: str, welding_method: str = '30') -> bool:
    """True, если в шве применяется остающаяся подкладка или подкладное кольцо."""
    if joint_code in BACKING_JOINT_CODES:
        return True
    return welding_method in BACKING_WELDING_METHODS


def get_inspection_zone(
    joint_code: str,
    thickness_mm: float,
    welding_method: str = '30',
    *,
    material_type: str = 'steel',
    material_class: str | None = None,
    material: str = '',
    outer_diameter_mm: float | None = None,
    s1_override_mm: float | None = None,
    reinforcement_removed: bool = False,
    has_backing_ring: bool | None = None,
    backing_ring_thickness_mm: float | None = None,
) -> dict:
    """
    Рассчитывает геометрические параметры контролируемой зоны
    и радиационной толщины для РГК.

    Поля 4.2.2 / 4.2.4 / 4.2.5 технологической карты.

    :param joint_code: условное обозначение типа соединения
    :param thickness_mm: номинальная толщина стенки S, мм
    :param welding_method: код способа сварки
    :return: словарь с параметрами зоны контроля
    """
    from normative.gost_59023_wall import resolve_joint_wall_thickness

    if material_class is None:
        if material_type == 'titanium':
            material_class = 'titanium'
        elif material_type == 'aluminum':
            material_class = 'aluminum'
        else:
            material_class = resolve_material_class(material) or 'perlit'

    wall = resolve_joint_wall_thickness(
        joint_code,
        thickness_mm,
        outer_diameter_mm=outer_diameter_mm,
        s1_override_mm=s1_override_mm,
    )
    weld = get_weld_width(
        joint_code,
        thickness_mm,
        material_class,
        outer_diameter_mm=outer_diameter_mm,
    )
    e = weld.get('e_mm') or (thickness_mm * 1.5)
    e_tol = weld.get('e_tol_mm', _default_e_tolerance_mm(e))
    e_max = weld.get('e_max_mm', round(e + e_tol, 1))
    e1 = weld.get('e1_mm', e)
    e1_max = weld.get('e1_max_mm', round(e1 + weld.get('e1_tol_mm', _default_e_tolerance_mm(e1)), 1))
    effective_e = weld.get('effective_e_mm', max(e, e1))
    effective_e_max = weld.get('effective_e_max_mm', max(e_max, e1_max))
    bead_mode = weld.get('bead_mode', 'equal')
    g_nom = weld.get('g_nom') or 2.0
    g_min = weld.get('g_min_mm', max(0.0, g_nom - 1.5))
    g_max = weld.get('g_max_mm', g_nom + 1.5)

    if reinforcement_removed:
        g_nom = 0.0
        g_min = 0.0
        g_max = 0.0

    # Ширина валика на поверхности (e — лицевая сторона; e1 — обратная при dual)
    bead_width_surface = e

    # Ширина ОШЗ (4.2.4) — по НП-105-18 и ГОСТ Р 50.05.07-2018
    if welding_method == '20':   # ЭШС — зона шире
        haz_width = max(20.0, thickness_mm * 0.5)
    elif thickness_mm <= 5:
        haz_width = HAZ_WIDTH_MM
    elif thickness_mm <= 20:
        haz_width = max(HAZ_WIDTH_MM, thickness_mm * 0.3)
    else:
        haz_width = max(HAZ_WIDTH_MM, min(20.0, thickness_mm * 0.25))

    haz_width = round(haz_width, 1)

    if material_type == 'titanium':
        from normative.np_104_18 import (
            DOCUMENT_CODE as NP104_CODE,
            get_titanium_min_edge_zone_width_mm,
        )
        min_haz = get_titanium_min_edge_zone_width_mm(welding_method)
        haz_width = max(haz_width, min_haz)
        haz_width = round(haz_width, 1)

    # Ширина контролируемой зоны (4.2.5): max(e_max, e1_max) + 2×a
    zone_width = effective_e_max + 2 * haz_width

    # Минимальная ширина снимка по ГОСТ Р 50.05.07-2018 п.6.3.13
    if welding_method == '20':
        film_width_min = max(50.0, zone_width)
    elif thickness_mm <= 5:
        film_width_min = effective_e
    elif thickness_mm <= 20:
        film_width_min = effective_e + 10
    else:
        film_width_min = effective_e + 40

    auto_backing = joint_uses_backing(joint_code, welding_method)
    user_backing = bool(has_backing_ring)
    has_backing = user_backing or auto_backing

    if has_backing:
        if backing_ring_thickness_mm and backing_ring_thickness_mm > 0:
            backing_thickness = float(backing_ring_thickness_mm)
        else:
            backing_thickness = thickness_mm
    else:
        backing_thickness = 0.0

    ref = 'ГОСТ Р 50.05.07-2018, п. 6.3.13; НП-105-18'
    if material_type == 'titanium':
        ref += f'; {NP104_CODE}, п. 84'

    return {
        # 4.2.2 — ширина валика и высота усиления
        'bead_width_mm': round(bead_width_surface, 1),
        'bead_width_inner_mm': round(e1, 1),
        'effective_e_mm': round(effective_e, 1),
        'effective_e_max_mm': round(effective_e_max, 1),
        'bead_mode': bead_mode,
        'e_display': weld.get('e_display', format_dimension_with_tolerance(e, weld.get('e_tol_mm', 1.5))),
        'e1_display': weld.get('e1_display', format_dimension_with_tolerance(e1, weld.get('e1_tol_mm', 1.5))),
        'bead_height_mm': round(g_nom, 1),
        'g_display': weld.get('g_display', f'{g_nom:.1f}'.replace('.', ',')),
        'g_label': weld.get('g_label', '4.2.3. Высота валика усиления (g)'),
        'g_face_display': weld.get('g_face_display'),
        'labeled_as_g1': weld.get('labeled_as_g1', False),
        'labeled_as_e1': weld.get('labeled_as_e1', False),
        'e_label_inner': weld.get('e_label_inner'),
        'g_min_mm': round(g_min, 1),
        'g_max_mm': round(g_max, 1),
        'g1_display': weld.get('g1_display'),
        'g1_min_mm': weld.get('g1_min_mm'),
        'g1_max_mm': weld.get('g1_max_mm'),
        'sketch_bead_source': weld.get('sketch_bead_source'),
        'reinforcement_removed': reinforcement_removed,
        'backing_thickness_mm': round(backing_thickness, 1),
        'has_backing': has_backing,
        # 4.2.4 — ширина ОШЗ
        'haz_width_mm': haz_width,
        # 4.2.5 — ширина контролируемой зоны
        'zone_width_mm': round(zone_width, 1),
        # Ширина снимка
        'film_width_min_mm': round(film_width_min, 1),
        # Детали расчёта
        'weld_note': weld.get('note', ''),
        'ref': ref,
        # S / S1 (ГОСТ Р 59023.2-2020)
        's_mm': wall['s_mm'],
        's1_mm': wall['s1_mm'],
        's_eff_mm': wall['s_eff_mm'],
        'dp_mm': wall.get('dp_mm'),
        's_equals_s1': wall['s_equals_s1'],
        's_equals_s1_actual': wall['s_equals_s1_actual'],
        'has_internal_boring': wall['has_internal_boring'],
        'wall_thickness_mode': wall['wall_thickness_mode'],
        'wall_summary': wall['wall_summary'],
        'wall_note': wall['wall_note'],
        'wall_resolve_source': wall['wall_resolve_source'],
        'boring_row': wall.get('boring_row'),
    }


# ------------------------------------------------------------------
# Клас металла для отображения в форме
# ------------------------------------------------------------------

MATERIAL_CLASS_CHOICES = [
    ('perlit', 'Перлитные и высокохромистые стали (С-1...С-42)'),
    ('austenite', 'Аустенитные стали и Fe-Ni сплавы (С-11...С-42)'),
    ('titanium', 'Титановые сплавы (ТС-1…ТУ-19; табл. 9.67–9.84 лист, 9.85–9.99 труба)'),
    ('aluminum', 'Алюминиевые сплавы (С-1…У-15; табл. 9.100–9.108 стыковые, 9.109–9.122 прочие)'),
]

# ------------------------------------------------------------------
# Старые данные (совместимость)
# ------------------------------------------------------------------

# Типоразмеры трубопроводов (Ду, Dн, толщины)
PIPE_SIZES = [
    (15, 21.3, [2.0, 2.5, 3.0]),
    (20, 26.8, [2.5, 3.0, 4.0]),
    (25, 33.5, [3.0, 3.5, 4.0]),
    (32, 42.3, [3.5, 4.0, 5.0]),
    (40, 48.3, [3.5, 4.0, 5.0]),
    (50, 60.3, [3.5, 4.0, 5.0, 6.0]),
    (65, 76.1, [4.0, 5.0, 6.0, 7.0]),
    (80, 88.9, [4.0, 5.0, 6.0, 7.0, 8.0]),
    (100, 114.3, [5.0, 6.0, 7.0, 8.0, 10.0]),
    (125, 139.7, [5.0, 6.0, 7.0, 8.0, 10.0]),
    (150, 168.3, [5.0, 6.0, 8.0, 10.0, 12.0]),
    (200, 219.1, [6.0, 7.0, 8.0, 10.0, 12.0, 14.0]),
    (250, 273.0, [7.0, 8.0, 10.0, 12.0, 14.0, 16.0]),
    (300, 323.9, [8.0, 10.0, 12.0, 14.0, 16.0]),
    (350, 355.6, [8.0, 10.0, 12.0, 14.0, 16.0]),
    (400, 406.4, [10.0, 12.0, 14.0, 16.0, 18.0]),
    (500, 508.0, [10.0, 12.0, 14.0, 16.0, 18.0, 20.0]),
    (600, 610.0, [12.0, 14.0, 16.0, 18.0, 20.0, 22.0]),
    (800, 820.0, [14.0, 16.0, 18.0, 20.0, 22.0, 25.0]),
    (1000, 1020.0, [14.0, 16.0, 18.0, 20.0, 22.0, 25.0, 28.0]),
]


def get_pipe_diameters():
    """Список наружных диаметров труб для выбора в форме."""
    return [(str(size[1]), f'Ду{size[0]} (Dн={size[1]} мм)') for size in PIPE_SIZES]


# Марки сталей (обновлённый список)
ALL_STEEL_GRADES = [
    # Перлитные
    'Ст20', 'Ст22К', 'Ст15К', 'Ст20К',
    '09Г2С', '16ГС', '17Г1С', '10Г2С1',
    '15ХМ', '12ХМ', '12Х1МФ', '15Х1МФА', '10Х2М1', '15Х2МФА',
    # Специальные для АЭУ (перлитные)
    '10ГН2МФА', '15Х2НМФА', '15Х2НМФА-А', 'АЭ-44',
    # Аустенитные
    '08Х18Н10Т', '12Х18Н10Т', '10Х17Н13М2Т',
    '08Х17Н15М3Т', '12Х18Н9', '03Х18Н11',
    # Высокохромистые (перлит/мартенсит)
    '12Х13', '20Х13', '14Х17Н2',
]


MATERIAL_TITANIUM = '__titanium__'
MATERIAL_ALUMINUM = '__aluminum__'


def get_controlled_object_material_choices():
    """Список материалов контролируемого объекта для выпадающего списка."""
    choices = [(g, g) for g in sorted(ALL_STEEL_GRADES)]
    choices.append((MATERIAL_TITANIUM, 'Сплавы на основе титана'))
    choices.append((MATERIAL_ALUMINUM, 'Сплавы на основе алюминия'))
    return choices


def resolve_material_type(material: str) -> str:
    """
    Определяет тип материала для выбора источника излучения (табл. Б.1–Б.3).

    :return: 'steel', 'aluminum' или 'titanium'
    """
    if material == MATERIAL_TITANIUM:
        return 'titanium'
    if material == MATERIAL_ALUMINUM:
        return 'aluminum'
    return 'steel'


def requires_material_grade(material: str) -> bool:
    """Нужно ли вводить марку основного металла вручную."""
    return material in (MATERIAL_TITANIUM, MATERIAL_ALUMINUM)


def get_material_display_name(material: str, material_grade: str = '') -> str:
    """Возвращает отображаемое название материала."""
    grade = (material_grade or '').strip()
    if material == MATERIAL_TITANIUM:
        base = 'Сплавы на основе титана'
    elif material == MATERIAL_ALUMINUM:
        base = 'Сплавы на основе алюминия'
    else:
        return material
    return f'{base}, марка {grade}' if grade else base


def get_material_choices():
    """Список марок сталей для выпадающего списка."""
    return [(g, g) for g in sorted(ALL_STEEL_GRADES)]


def get_welding_material_choices():
    """Список марок сварочных материалов для п. 1.10 техкарты."""
    return [('', '— Как основной металл (п. 1.9) —')] + get_material_choices()


def resolve_welding_material(
    welding_material: str,
    welding_material_custom: str,
    base_material_display: str,
) -> str:
    """Определяет марку сварочного материала для техкарты (п. 1.10)."""
    custom = (welding_material_custom or '').strip()
    if custom:
        return custom
    selected = (welding_material or '').strip()
    if not selected or selected == 'same_as_base':
        return base_material_display
    display = get_material_display_name(selected, '')
    return display or selected
