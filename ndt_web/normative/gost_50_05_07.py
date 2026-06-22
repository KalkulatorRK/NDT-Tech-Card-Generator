"""
Данные ГОСТ Р 50.05.07-2018 «Система экспертной оценки и подтверждения
соответствия объектов использования атомной энергии. Неразрушающий контроль.
Радиографический контроль».

Модуль содержит:
- таблицы чувствительности;
- источники излучения и диапазоны применимости;
- требования к радиографическим плёнкам;
- требования к усиливающим экранам;
- формулы и ограничения по геометрическим параметрам;
- схемы просвечивания;
- условия химической обработки плёнки.

Источник: ГОСТ Р 50.05.07-2018.

ВАЖНО: Данные введены на основании текста нормативного документа.
При внесении изменений в стандарт необходимо актуализировать этот модуль.
"""

from math import sqrt

# ------------------------------------------------------------------
# Идентификатор документа
# ------------------------------------------------------------------
DOCUMENT_CODE = 'ГОСТ Р 50.05.07-2018'
DOCUMENT_FULL_NAME = (
    'ГОСТ Р 50.05.07-2018 «Система экспертной оценки и подтверждения соответствия '
    'объектов использования атомной энергии. Неразрушающий контроль. '
    'Радиографический контроль»'
)

# ------------------------------------------------------------------
# Чувствительность контроля K
#
# ВНИМАНИЕ: Требуемая чувствительность K определяется по НП-105-18,
# Таблица N 4.8/4.9 в зависимости от категории шва и толщины.
# Функция get_sensitivity() ниже — СПРАВОЧНАЯ, для предварительного
# выбора источника и плёнки. Для оценки качества используйте
# normative.np_105_18.get_required_sensitivity().
# ------------------------------------------------------------------

def get_sensitivity(thickness_mm: float, category_or_class: str) -> float:
    """
    Возвращает требуемую чувствительность контроля K (мм) по
    НП-105-18, Таблица N 4.8/4.9.

    Принимает категорию сварного шва (I/II/III/Iн/IIн).

    :param thickness_mm: номинальная толщина свариваемых деталей, мм
    :param category_or_class: категория ('I','II','III','Iн','IIн')
    :return: требуемая чувствительность K, мм
    """
    from normative.np_105_18 import get_required_sensitivity

    category = category_or_class

    K = get_required_sensitivity(category, thickness_mm)
    return K if K else 0.20   # Значение по умолчанию


def get_sensitivity_mm(thickness_mm: float, category_or_class: str) -> float:
    """
    Возвращает требуемую чувствительность K в мм.
    Синоним get_sensitivity() для обратной совместимости.
    """
    return get_sensitivity(thickness_mm, category_or_class)


# ------------------------------------------------------------------
# Источники ионизирующего излучения
# ------------------------------------------------------------------
XRAY_SOURCE_CODES = ['X-100kV', 'X-200kV', 'X-300kV', 'X-400kV']

RADIATION_SOURCES = [
    {
        'code': 'Yb-169',
        'name': 'Иттербий-169 (Yb-169)',
        'type': 'isotope',
        'energy_kev': '50–300',
        'energy_display': '0,05–0,30 МэВ',
        'half_life': '32,0 сут',
        'notes': 'Радионуклидный источник для малых толщин',
    },
    {
        'code': 'Tm-170',
        'name': 'Тулий-170 (Tm-170)',
        'type': 'isotope',
        'energy_kev': '84',
        'energy_display': '0,084 МэВ',
        'half_life': '128,6 сут',
        'notes': 'Радионуклидный источник для малых и средних толщин',
    },
    {
        'code': 'Se-75',
        'name': 'Селен-75 (Se-75)',
        'type': 'isotope',
        'energy_kev': '66–400',
        'energy_display': '0,066–0,40 МэВ',
        'half_life': '119,8 сут',
        'notes': 'Радионуклидный источник для средних толщин',
    },
    {
        'code': 'Ir-192',
        'name': 'Иридий-192 (Ir-192)',
        'type': 'isotope',
        'energy_kev': '310–604',
        'energy_display': '0,31–0,60 МэВ',
        'half_life': '73,8 сут',
        'notes': 'Наиболее применяемый изотоп для промышленного РГК',
    },
    {
        'code': 'Co-60',
        'name': 'Кобальт-60 (Co-60)',
        'type': 'isotope',
        'energy_kev': '1173–1332',
        'energy_display': '1,17–1,33 МэВ',
        'half_life': '5,27 лет',
        'notes': 'Радионуклидный источник для больших толщин',
    },
    {
        'code': 'X-100kV',
        'name': 'Рентгеновский аппарат 100 кВ',
        'type': 'xray',
        'energy_kev': '≤100',
        'energy_display': 'до 100 кВ',
        'half_life': '—',
        'notes': 'Рентгеновский аппарат для малых толщин',
    },
    {
        'code': 'X-200kV',
        'name': 'Рентгеновский аппарат 200 кВ',
        'type': 'xray',
        'energy_kev': '100–200',
        'energy_display': '100–200 кВ',
        'half_life': '—',
        'notes': 'Рентгеновский аппарат для малых и средних толщин',
    },
    {
        'code': 'X-300kV',
        'name': 'Рентгеновский аппарат 300 кВ',
        'type': 'xray',
        'energy_kev': '200–300',
        'energy_display': '200–300 кВ',
        'half_life': '—',
        'notes': 'Рентгеновский аппарат для средних толщин',
    },
    {
        'code': 'X-400kV',
        'name': 'Рентгеновский аппарат 400 кВ',
        'type': 'xray',
        'energy_kev': '300–400',
        'energy_display': '300–400 кВ',
        'half_life': '—',
        'notes': 'Рентгеновский аппарат для больших толщин',
    },
]


# ------------------------------------------------------------------
# Применимость источников по материалу и толщине
# (ГОСТ Р 50.05.07-2018, Приложение Б, таблицы Б.1–Б.3)
# ------------------------------------------------------------------
TABLE_B_SOURCE_RANGES = {
    'steel': [
        (0, 5, XRAY_SOURCE_CODES + ['Yb-169', 'Tm-170']),
        (5, 20, XRAY_SOURCE_CODES + ['Tm-170', 'Se-75', 'Ir-192']),
        (20, 30, XRAY_SOURCE_CODES + ['Se-75', 'Ir-192']),
        (30, 80, XRAY_SOURCE_CODES + ['Ir-192', 'Co-60']),
        (80, 100, XRAY_SOURCE_CODES + ['Co-60', 'Ir-192']),
        (100, 150, ['Co-60']),
    ],
    'aluminum': [
        (0, 5, XRAY_SOURCE_CODES + ['Yb-169']),
        (5, 15, XRAY_SOURCE_CODES + ['Yb-169', 'Tm-170']),
        (15, 40, XRAY_SOURCE_CODES + ['Tm-170', 'Se-75']),
        (40, 60, XRAY_SOURCE_CODES + ['Tm-170', 'Se-75', 'Ir-192']),
        (60, 90, XRAY_SOURCE_CODES + ['Ir-192']),
        (90, 150, XRAY_SOURCE_CODES + ['Ir-192']),
    ],
    'titanium': [
        (0, 5, XRAY_SOURCE_CODES + ['Yb-169']),
        (5, 10, XRAY_SOURCE_CODES + ['Yb-169', 'Tm-170']),
        (10, 40, XRAY_SOURCE_CODES + ['Tm-170', 'Se-75', 'Ir-192']),
        (40, 60, XRAY_SOURCE_CODES + ['Ir-192']),
        (60, 100, XRAY_SOURCE_CODES + ['Ir-192', 'Co-60']),
        (100, 120, ['Ir-192', 'Co-60']),
    ],
}

MATERIAL_TYPES = ('steel', 'aluminum', 'titanium')

TABLE_B_REF = {
    'steel': 'Б.1',
    'aluminum': 'Б.2',
    'titanium': 'Б.3',
}


def _format_table_b_range_label(t_min: float, t_max: float) -> str:
    """Человекочитаемая подпись диапазона радиационной толщины из табл. Б."""
    if t_min == 0:
        return f'не более {t_max:g} мм'
    if t_max >= 9999:
        return f'св. {t_min:g} мм'
    return f'св. {t_min:g} до {t_max:g} мм включ.'


def _matched_table_b_rows(material_type: str, thickness_mm: float) -> list:
    """Возвращает строки таблицы Б, соответствующие толщине."""
    ranges = TABLE_B_SOURCE_RANGES.get(material_type, TABLE_B_SOURCE_RANGES['steel'])
    matched = []
    for t_min, t_max, row_codes in ranges:
        if _thickness_in_table_range(thickness_mm, t_min, t_max):
            matched.append({
                't_min': t_min,
                't_max': t_max,
                'codes': row_codes,
                'range_label': _format_table_b_range_label(t_min, t_max),
            })
    return matched


def get_table_b_selection_info(thickness_mm: float, material_type: str = 'steel') -> dict:
    """
    Справочная информация о применимости источников по табл. Б.1–Б.3.

    :return: словарь с table_ref, range_label, thickness_mm, material_type
    """
    if material_type not in MATERIAL_TYPES:
        material_type = 'steel'
    rows = _matched_table_b_rows(material_type, thickness_mm)
    if not rows:
        return {
            'table_ref': TABLE_B_REF.get(material_type, 'Б.1'),
            'range_label': 'нет строки таблицы для данной толщины',
            'thickness_mm': thickness_mm,
            'material_type': material_type,
        }
    return {
        'table_ref': TABLE_B_REF.get(material_type, 'Б.1'),
        'range_label': '; '.join(r['range_label'] for r in rows),
        'thickness_mm': thickness_mm,
        'material_type': material_type,
    }


def _thickness_in_table_range(thickness_mm: float, t_min: float, t_max: float) -> bool:
    """Проверяет попадание толщины в диапазон строки таблицы Б."""
    if t_min == 0:
        return thickness_mm <= t_max
    if t_max >= 9999:
        return thickness_mm > t_min
    return t_min < thickness_mm <= t_max


def _source_codes_for_material_thickness(material_type: str, thickness_mm: float) -> set:
    """Возвращает коды источников по таблице Б для материала и толщины."""
    ranges = TABLE_B_SOURCE_RANGES.get(material_type, TABLE_B_SOURCE_RANGES['steel'])
    codes: set = set()
    for t_min, t_max, row_codes in ranges:
        if _thickness_in_table_range(thickness_mm, t_min, t_max):
            codes.update(row_codes)
    return codes


def get_suitable_sources(thickness_mm: float, material_type: str = 'steel') -> list:
    """
    Возвращает список источников излучения, применимых для заданной толщины
    и материала контролируемого объекта (таблицы Б.1–Б.3 ГОСТ Р 50.05.07-2018).

    Диапазоны применимости определяются ТОЛЬКО по TABLE_B_SOURCE_RANGES.
    Справочник RADIATION_SOURCES содержит только паспортные характеристики источников.

    :param thickness_mm: радиационная / номинальная толщина, мм
    :param material_type: 'steel', 'aluminum' или 'titanium'
    :return: список словарей с описанием источников
    """
    if material_type not in MATERIAL_TYPES:
        material_type = 'steel'

    applicable_codes = _source_codes_for_material_thickness(material_type, thickness_mm)
    table_info = get_table_b_selection_info(thickness_mm, material_type)
    suitable = []
    for source in RADIATION_SOURCES:
        if source['code'] not in applicable_codes:
            continue
        source_copy = dict(source)
        source_copy['table_ref'] = table_info['table_ref']
        source_copy['table_range_label'] = table_info['range_label']
        suitable.append(source_copy)
    return suitable


def get_source_choices():
    """Список кортежей источников для выпадающего списка."""
    return [(s['code'], s['name']) for s in RADIATION_SOURCES]


# ------------------------------------------------------------------
# Усиливающие и защитные экраны
#
# Данные из ГОСТ Р 50.05.07-2018:
# Таблица 2 — Толщина усиливающих экранов (передние / front)
# Таблица 3 — Толщина защитных экранов (задние / back)
#
# Таблица 2 (усиливающие, свинцовые):
#   Рентген ≤100 кВ : без экранов
#   Рентген 100–300 кВ: 0,02–0,09 мм
#   Рентген >300 кВ : 0,09–0,16 мм
#   Иттербий-169   : без экранов
#   Тулий-170      : 0,02–0,09 мм
#   Селен-75       : 0,09–0,16 мм
#   Иридий-192     : 0,09–0,20 мм
#   Кобальт-60     : 0,20–0,50 мм
#
# Таблица 3 (защитные, задние):
#   Рентген ≤200 кВ, Yb-169, Tm-170, Se-75: не менее 0,5 мм
#   Рентген >200 кВ, Ir-192, Co-60        : не менее 1,0 мм
#   Ускоритель электронов                  : не менее 1,5 мм
# ------------------------------------------------------------------
SCREEN_REQUIREMENTS = {
    'Yb-169': {
        'front_mm': 'без экранов',
        'back_mm': '0,5',
        'material': 'Свинцовые (Pb)',
        'note': '',
    },
    'Tm-170': {
        'front_mm': '0,02–0,09',   # Таблица 2: тулий-170
        'back_mm': '0,5',           # Таблица 3: ≤200 кВ группа
        'material': 'Свинцовые (Pb)',
        'note': '',
    },
    'Se-75': {
        'front_mm': '0,09–0,16',   # Таблица 2: селен-75
        'back_mm': '0,5',           # Таблица 3: ≤200 кВ группа
        'material': 'Свинцовые (Pb)',
        'note': '',
    },
    'Ir-192': {
        'front_mm': '0,09–0,20',   # Таблица 2: иридий-192
        'back_mm': '1,0',           # Таблица 3: >200 кВ группа
        'material': 'Свинцовые (Pb)',
        'note': '',
    },
    'Co-60': {
        'front_mm': '0,20–0,50',   # Таблица 2: кобальт-60
        'back_mm': '1,0',           # Таблица 3: >200 кВ группа
        'material': (
            'Свинцовые (Pb) или медно-латунные/стальные '
            '(допускается для E ≥ 1 МэВ)'
        ),
        'note': 'При применении медных/стальных экранов толщина может быть увеличена.',
    },
    'X-100kV': {
        'front_mm': 'без экранов', # Таблица 2: рентген ≤100 кВ
        'back_mm': '0,5',           # Таблица 3
        'material': 'Свинцовые (Pb)',
        'note': 'Усиливающие экраны не применяются при напряжении ≤100 кВ.',
    },
    'X-200kV': {
        'front_mm': '0,02–0,09',   # Таблица 2: рентген 100–300 кВ
        'back_mm': '0,5',           # Таблица 3: ≤200 кВ
        'material': 'Свинцовые (Pb)',
        'note': '',
    },
    'X-300kV': {
        'front_mm': '0,02–0,09',   # Таблица 2: рентген 100–300 кВ
        'back_mm': '1,0',           # Таблица 3: >200 кВ
        'material': 'Свинцовые (Pb)',
        'note': '',
    },
    'X-400kV': {
        'front_mm': '0,09–0,16',   # Таблица 2: рентген >300 кВ
        'back_mm': '1,0',           # Таблица 3: >200 кВ
        'material': 'Свинцовые (Pb)',
        'note': '',
    },
}

# ------------------------------------------------------------------
# Радиографические плёнки (по ГОСТ ИСО 11699-1)
# ------------------------------------------------------------------
FILM_CLASSES = [
    {
        'class': 'C1',
        'description': 'Сверхвысококонтрастные, ультрамелкозернистые',
        'examples': 'Kodak AA400, AGFA D2',
        'allowed_for': ['I'],
        'optical_density_min': 2.0,
    },
    {
        'class': 'C2',
        'description': 'Высококонтрастные, мелкозернистые',
        'examples': 'Kodak T200, AGFA D3',
        'allowed_for': ['I', 'II'],
        'optical_density_min': 2.0,
    },
    {
        'class': 'C3',
        'description': 'Высококонтрастные, среднезернистые',
        'examples': 'Kodak T100, AGFA D4',
        'allowed_for': ['I', 'II', 'III'],
        'optical_density_min': 2.0,
    },
    {
        'class': 'C4',
        'description': 'Контрастные, среднезернистые',
        'examples': 'AGFA D5, Fuji IX100',
        'allowed_for': ['II', 'III'],
        'optical_density_min': 1.5,
    },
    {
        'class': 'C5',
        'description': 'Высокочувствительные, крупнозернистые',
        'examples': 'AGFA D7, Fuji IX200',
        'allowed_for': ['III'],
        'optical_density_min': 1.5,
    },
    {
        'class': 'C6',
        'description': 'Очень высокочувствительные',
        'examples': 'AGFA D8',
        'allowed_for': ['III'],
        'optical_density_min': 1.5,
    },
]

# ------------------------------------------------------------------
# Выбор плёнки по материалу и толщине (Таблица Б.1 ГОСТ Р 50.05.07-2018)
# Данные для стали, основной материал в АЭУ.
# ------------------------------------------------------------------
FILM_BY_THICKNESS_STEEL = [
    # (толщ_мин, толщ_макс, источники, плёнки)
    (0, 5,
     'Рентгеновский аппарат, иттербий-169, тулий-170',
     'РТ-14, РТ-15; D2, D3, D4 "Структурикс"; IX25, IX50 "Фуджи"; NDT45 "Дюпонт"'),
    (5, 20,
     'Рентгеновский аппарат, тулий-170, селен-75, иридий-192',
     'РТ-14, РТ-15; D2, D3, D4, D5 "Структурикс"; IX25, IX50, IX80 "Фуджи"; '
     'NDT45, NDT55, NDT65 "Дюпонт"; РТ-4, РТ-5, РТ-К; R4, R5 "Фома"; '
     '"Кодак" М100, МХ125, Т200'),
    (20, 30,
     'Рентгеновский аппарат (все толщины), Se-75/Ir-192 (тонкостенная часть диапазона)',
     'РТ-14, РТ-15; D2–D7 "Структурикс"; IX25–IX100 "Фуджи"; '
     'NDT45–NDT70 "Дюпонт"; РТ-4, РТ-5, РТ-К; R4, R5, R7 "Фома"; '
     '"Кодак" М100, МХ125, Т200, АА400'),
    (30, 80,
     'Рентгеновский аппарат, иридий-192',
     'РТ-14, РТ-15; D2–D7 "Структурикс"; IX25–IX100 "Фуджи"; '
     'NDT45–NDT70 "Дюпонт"; РТ-4, РТ-5, РТ-К; R4, R5, R7 "Фома"'),
]


def get_films_for_thickness(thickness_mm: float) -> str:
    """Возвращает рекомендуемые плёнки для стали заданной толщины."""
    for t_min, t_max, sources, films in FILM_BY_THICKNESS_STEEL:
        if t_min < thickness_mm <= t_max or (t_min == 0 and thickness_mm <= t_max):
            return films
    return 'D2–D7 "Структурикс"; IX50–IX100 "Фуджи"; РТ-4, РТ-5'


# Плёнки для выбора в форме
FILM_NAMES = [
    # Отечественные
    'РТ-14',
    'РТ-15',
    'РТ-4М',
    'РТ-5М',
    'РТ-4В',
    'РТ-5В',
    'РТ-К',
    # AGFA (Структурикс)
    'D2 "Структурикс"',
    'D3 "Структурикс"',
    'D4 "Структурикс"',
    'D5 "Структурикс"',
    'D7 "Структурикс"',
    # Fuji
    'IX25 "Фуджи"',
    'IX50 "Фуджи"',
    'IX80 "Фуджи"',
    'IX100 "Фуджи"',
    # Kodak
    '"Кодак" М100',
    '"Кодак" МХ125',
    '"Кодак" Т200',
    '"Кодак" АА400',
    # DuPont
    'NDT45 "Дюпонт"',
    'NDT55 "Дюпонт"',
    'NDT65 "Дюпонт"',
    'NDT70 "Дюпонт"',
    # Foma
    'R4 "Фома"',
    'R5 "Фома"',
    'R7 "Фома"',
]


def get_film_for_category(weld_category: str) -> list:
    """Возвращает рекомендуемые плёнки для категории сварного соединения."""
    return [f for f in FILM_CLASSES if weld_category in f['allowed_for']]


def get_film_for_class(control_class: str) -> list:
    """Синоним get_film_for_category() для обратной совместимости."""
    return get_film_for_category(control_class)


# ------------------------------------------------------------------
# Типовые размеры радиографической плёнки, мм (длина × ширина)
# ------------------------------------------------------------------
STANDARD_FILM_SIZES = [
    {'code': '120x100', 'length_mm': 120, 'width_mm': 100, 'label': '120 × 100'},
    {'code': '240x100', 'length_mm': 240, 'width_mm': 100, 'label': '240 × 100'},
    {'code': '480x100', 'length_mm': 480, 'width_mm': 100, 'label': '480 × 100'},
]


def get_film_size_choices():
    """Список типовых размеров плёнки для выпадающего списка."""
    return [(s['code'], s['label']) for s in STANDARD_FILM_SIZES]


def parse_film_size(film_size_code: str) -> dict:
    """Возвращает длину и ширину плёнки по коду типового размера."""
    for size in STANDARD_FILM_SIZES:
        if size['code'] == film_size_code:
            return size
    # Значение по умолчанию — 240×100
    return STANDARD_FILM_SIZES[1]


def get_film_choices():
    """Список плёнок для выпадающего списка."""
    return [(f, f) for f in FILM_NAMES]


# ------------------------------------------------------------------
# Максимальная геометрическая нерезкость (мм)
# ------------------------------------------------------------------
MAX_GEOMETRIC_UNSHARPNESS = {
    'I': 0.3,
    'II': 0.4,
    'III': 0.5,
}

# ------------------------------------------------------------------
# Оптическая плотность плёнки
# ------------------------------------------------------------------
OPTICAL_DENSITY = {
    'I': {'min': 2.0, 'max': 4.5},
    'II': {'min': 1.5, 'max': 4.5},
    'III': {'min': 1.5, 'max': 4.5},
}

# ------------------------------------------------------------------
# Эталоны чувствительности (проволочные, пластинчатые, канавочные)
# ------------------------------------------------------------------
IQI_TYPES = [
    {
        'code': 'wire',
        'name': 'Проволочный эталон',
        'standard': 'ГОСТ 7512 / ISO 19232-1',
        'preferred_for': ['I', 'II'],
    },
    {
        'code': 'duplex',
        'name': 'Дуплекс-эталон',
        'standard': 'ISO 19232-5',
        'preferred_for': ['I'],
    },
    {
        'code': 'groove',
        'name': 'Канавочный эталон',
        'standard': 'ГОСТ 7512 / ISO 19232-2',
        'preferred_for': ['II', 'III'],
    },
    {
        'code': 'step_hole',
        'name': 'Пластинчатый (ступенчато-дырчатый) эталон',
        'standard': 'ГОСТ 7512 / ISO 19232-3',
        'preferred_for': ['II', 'III'],
    },
]


def get_iqi_choices():
    """Список типов эталонов для выпадающего списка."""
    return [(iqi['code'], iqi['name']) for iqi in IQI_TYPES]


# ------------------------------------------------------------------
# Геометрические расчёты
# ------------------------------------------------------------------

def calc_geometric_unsharpness(focal_spot_mm: float, sfd_mm: float, ofd_mm: float) -> float:
    """
    Расчёт геометрической нерезкости.

    Формула: Ug = d × b / (f - b)
    где:
      d   — размер фокусного пятна источника, мм
      b   — расстояние от объекта контроля до детектора (OFD), мм
      f   — расстояние от источника до детектора (SFD/FRD), мм

    :param focal_spot_mm: размер фокусного пятна, мм
    :param sfd_mm: расстояние источник–детектор (ФРД), мм
    :param ofd_mm: расстояние объект–детектор (ОД), мм
    :return: геометрическая нерезкость, мм
    :raises ValueError: если SFD ≤ OFD
    """
    if sfd_mm <= ofd_mm:
        raise ValueError(
            f"Расстояние источник–детектор (SFD={sfd_mm} мм) должно быть "
            f"больше расстояния объект–детектор (OFD={ofd_mm} мм)."
        )
    unsharpness = focal_spot_mm * ofd_mm / (sfd_mm - ofd_mm)
    return round(unsharpness, 3)


def calc_min_sfd(focal_spot_mm: float, ofd_mm: float, weld_category: str) -> float:
    """
    Расчёт минимального расстояния источник–детектор (SFD) из условия
    ограничения геометрической нерезкости.

    Из условия Ug ≤ Ug_max:
      SFD_min = OFD × (d + Ug_max) / Ug_max

    :param focal_spot_mm: размер фокусного пятна, мм
    :param ofd_mm: расстояние объект–детектор, мм
    :param weld_category: категория сварного соединения (I/II/III)
    :return: минимальное SFD, мм
    """
    ug_max = MAX_GEOMETRIC_UNSHARPNESS.get(weld_category, 0.5)
    min_sfd = ofd_mm * (focal_spot_mm + ug_max) / ug_max
    return round(min_sfd, 1)


# ------------------------------------------------------------------
# Схемы просвечивания
# ------------------------------------------------------------------

def get_exposure_scheme(joint_type: str, outer_diameter_mm: float, wall_thickness_mm: float) -> dict:
    """
    Рекомендуемая схема просвечивания в зависимости от типа соединения и размеров.

    :param joint_type: тип соединения ('butt', 'corner', 'tee', 'flat')
    :param outer_diameter_mm: наружный диаметр трубопровода, мм (0 для плоских деталей)
    :param wall_thickness_mm: толщина стенки, мм
    :return: словарь с описанием схемы
    """
    if joint_type == 'flat' or outer_diameter_mm == 0:
        return {
            'code': 'S1',
            'name': 'Схема 1: Через одну стенку (плоские детали)',
            'description': (
                'Источник излучения и детектор расположены с разных сторон '
                'сварного соединения. Стандартная схема для плоских и '
                'крупногабаритных деталей.'
            ),
            'exposures_formula': 'По ширине шва + перекрытие ≥ 10 мм',
            'n_exposures_min': 1,
        }

    d = outer_diameter_mm

    if d <= 50:
        return {
            'code': 'S2',
            'name': 'Схема 2: Панорамная (малые диаметры)',
            'description': (
                'Источник излучения расположен внутри трубы по оси, '
                'детектор охватывает трубу снаружи (кольцевая кассета). '
                'Применяется для малых диаметров при наличии доступа внутрь.'
            ),
            'exposures_formula': '1 снимок (360°)',
            'n_exposures_min': 1,
        }
    elif d <= 150:
        return {
            'code': 'S3',
            'name': 'Схема 3: Через две стенки, расшифровка одной (эллипс)',
            'description': (
                'Источник вне трубы, детектор — с противоположной стороны. '
                'Источник смещён, чтобы швы двух стенок не перекрывались '
                'на снимке (метод эллипса). Минимум 2 экспозиции.'
            ),
            'exposures_formula': 'min 2 снимка под углом 90°',
            'n_exposures_min': 2,
        }
    elif d <= 400:
        return {
            'code': 'S4',
            'name': 'Схема 4: Через одну стенку (средние и большие диаметры)',
            'description': (
                'Источник снаружи трубы, детектор — на внутренней поверхности '
                'или снаружи с противоположной стороны. Количество экспозиций '
                'определяется длиной детектора и периметром шва.'
            ),
            'exposures_formula': 'n = π × D / (L_кассеты × 0,9)',
            'n_exposures_min': _calc_exposures_large_pipe(d, 350),
        }
    else:
        n = _calc_exposures_large_pipe(d, 350)
        return {
            'code': 'S5',
            'name': 'Схема 5: Через одну стенку (большие диаметры)',
            'description': (
                'Источник снаружи или внутри трубы, несколько экспозиций '
                'по периметру шва с перекрытием ≥ 10 мм.'
            ),
            'exposures_formula': f'n ≈ {n} снимков',
            'n_exposures_min': n,
        }


def _calc_exposures_large_pipe(diameter_mm: float, cassette_length_mm: float = 350) -> int:
    """Расчёт количества экспозиций для просвечивания трубы по периметру."""
    import math
    circumference = math.pi * diameter_mm
    effective_length = cassette_length_mm * 0.9   # с учётом перекрытия
    n = math.ceil(circumference / effective_length)
    return max(n, 3)


# ------------------------------------------------------------------
# Условия обработки плёнки
# ------------------------------------------------------------------
FILM_PROCESSING = {
    'developer': {
        'name': 'Проявитель',
        'options': [
            {'name': 'Рентген (стандартный)', 'temp_c': '20±1', 'time_min': '5–8'},
            {'name': 'D-19 (Kodak)', 'temp_c': '20±1', 'time_min': '5–6'},
            {'name': 'G-145 (AGFA)', 'temp_c': '20±1', 'time_min': '5–7'},
            {'name': 'ФД-89 (отечественный)', 'temp_c': '20±1', 'time_min': '6–8'},
        ],
    },
    'fixer': {
        'name': 'Закрепитель',
        'options': [
            {'name': 'Кислый закрепитель стандартный', 'temp_c': '18–25', 'time_min': '10–15'},
            {'name': 'Быстрый закрепитель F-24', 'temp_c': '18–25', 'time_min': '5–8'},
        ],
    },
    'washing': {'time_min': '20–30', 'note': 'Проточная вода'},
    'drying': {'temp_c': '25–40', 'note': 'Сушильный шкаф или воздушная сушка'},
}

# ------------------------------------------------------------------
# Требования к персоналу
# ------------------------------------------------------------------
PERSONNEL_REQUIREMENTS = {
    'I': {
        'level': 'II или III уровень',
        'standard': 'ГОСТ Р ИСО 9712 (EN 473)',
        'method': 'РК (RT)',
        'additional': (
            'Специалист II уровня вправе проводить контроль и интерпретировать результаты. '
            'Специалист III уровня вправе разрабатывать процедуры контроля.'
        ),
    },
    'II': {
        'level': 'II или III уровень',
        'standard': 'ГОСТ Р ИСО 9712 (EN 473)',
        'method': 'РК (RT)',
        'additional': 'Специалист II уровня вправе проводить контроль и интерпретировать результаты.',
    },
    'III': {
        'level': 'II уровень',
        'standard': 'ГОСТ Р ИСО 9712 (EN 473)',
        'method': 'РК (RT)',
        'additional': '',
    },
}

# ------------------------------------------------------------------
# Безопасность при радиографическом контроле
# ------------------------------------------------------------------
SAFETY_REQUIREMENTS = [
    'Наличие лицензии Ростехнадзора на право проведения работ с источниками ионизирующего излучения.',
    'Соблюдение требований НРБ-99/2009 и ОСПОРБ-99/2010.',
    'Обозначение и ограждение контролируемой зоны в соответствии с радиационной обстановкой.',
    'Применение индивидуальных дозиметров персоналом (накопительные и прямопоказывающие).',
    'Контроль мощности дозы в рабочей зоне и за её пределами.',
    'Использование защитных контейнеров и приспособлений для транспортировки источников.',
    'Наличие аварийного плана и комплекта для ликвидации радиационных аварий.',
    'Ведение журнала радиационного контроля.',
    'Радиационный контроль выполняется при минимально необходимой мощности дозы облучения.',
]
