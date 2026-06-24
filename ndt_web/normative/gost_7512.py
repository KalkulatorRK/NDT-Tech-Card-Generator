"""
ГОСТ 7512-82 — проволочные эталоны чувствительности (ИКИ) и условная запись дефектов.

Таблица 2: четыре типоразмера эталонов, в каждом семь проволок.
Маркировка (п. 2.13): первая цифра — материал, следующие 1–2 цифры — номер эталона.
Приложение 5–6: сокращённая запись дефектов при расшифровке снимков.
"""

from __future__ import annotations

# Таблица 2 ГОСТ 7512-82: {номер_эталона: [(номер_проволоки, d_мм), ...]}
WIRE_IQI_SETS: dict[int, list[tuple[int, float]]] = {
    1: [
        (1, 0.20), (2, 0.16), (3, 0.125), (4, 0.10),
        (5, 0.08), (6, 0.063), (7, 0.05),
    ],
    2: [
        (1, 0.40), (2, 0.32), (3, 0.25), (4, 0.20),
        (5, 0.16), (6, 0.125), (7, 0.10),
    ],
    3: [
        (1, 1.25), (2, 1.00), (3, 0.80), (4, 0.63),
        (5, 0.50), (6, 0.40), (7, 0.32),
    ],
    4: [
        (1, 4.00), (2, 3.20), (3, 2.50), (4, 2.00),
        (5, 1.60), (6, 1.25), (7, 1.00),
    ],
}

# Диапазоны радиационной толщины для выбора типоразмера эталона (табл. 2, h).
SET_THICKNESS_MAX_MM = {
    1: 12.0,
    2: 25.0,
    3: 140.0,
    4: 400.0,
}

# п. 2.13: условные обозначения материала эталона
IQI_MATERIAL_CODES = {
    'steel': 1,      # сплавы на основе железа
    'aluminum': 2,   # алюминий и магний
    'titanium': 3,   # титан
    'copper': 4,     # медь
    'nickel': 5,     # никель
}

IQI_MATERIAL_LABELS = {
    1: 'сплавы на основе железа',
    2: 'алюминий и магний',
    3: 'титан',
    4: 'медь',
    5: 'никель',
}

SIDE_SOURCE = 'source'
SIDE_FILM = 'film'

WIRE_IQI_TYPE = {
    'code': 'wire',
    'name': 'Проволочный эталон',
    'standard': 'ГОСТ 7512-82',
}


def map_material_to_iqi_code(material_type: str) -> int:
    """Код материала эталона (1–5) по типу контролируемого материала."""
    return IQI_MATERIAL_CODES.get(material_type, 1)


def format_iqi_marking(material_code: int, set_number: int) -> str:
    """
    Маркировка проволочного ИКИ: 2–3 цифры.

    Первая цифра — материал, следующие — номер эталона (1–4).
    Примеры: 11, 12, 14.
    """
    return f'{material_code}{set_number}'


def select_iqi_set_number(radiation_thickness_mm: float) -> int:
    """Подбирает номер проволочного эталона (1–4) по радиационной толщине."""
    for set_no, max_t in SET_THICKNESS_MAX_MM.items():
        if radiation_thickness_mm <= max_t:
            return set_no
    return 4


def get_wire_iqi(
    radiation_thickness_mm: float,
    k_mm: float,
    material_type: str = 'steel',
    shift_steps: int = 0,
) -> dict:
    """
    Определяет проволочный ИКИ по ГОСТ 7512-82.

    :param radiation_thickness_mm: радиационная толщина в месте установки ИКИ
    :param k_mm: требуемая чувствительность K, мм (НП-105-18)
    :param material_type: steel / aluminum / titanium (→ код материала 1–3)
    :param shift_steps: сдвиг на N ступеней жёстче (ИКИ со стороны плёнки)
    """
    material_code = map_material_to_iqi_code(material_type)
    set_no = select_iqi_set_number(radiation_thickness_mm)
    wires = WIRE_IQI_SETS[set_no]

    candidates = [w for w in wires if w[1] <= k_mm + 1e-9]
    if not candidates:
        wire_no, diameter = wires[-1]
    else:
        wire_no, diameter = max(candidates, key=lambda w: w[1])

    if shift_steps:
        idx = next(i for i, w in enumerate(wires) if w[0] == wire_no)
        idx = min(idx + shift_steps, len(wires) - 1)
        wire_no, diameter = wires[idx]

    marking = format_iqi_marking(material_code, set_no)
    material_label = IQI_MATERIAL_LABELS.get(material_code, '')

    return {
        'type': 'wire',
        'material_code': material_code,
        'material_label': material_label,
        'set_number': set_no,
        'wire_number': wire_no,
        'wire_diameter_mm': diameter,
        'marking': marking,
        'label': (
            f'проволочный эталон {marking}, проволока {wire_no} '
            f'(Ø {diameter:g} мм)'
        ),
        'standard': 'ГОСТ 7512-82, п. 2.10, табл. 2; маркировка п. 2.13',
    }


def resolve_iqi_placement(
    scheme_code: str = '',
    wall_count: int = 1,
    iqi_side: str = SIDE_SOURCE,
) -> dict:
    """
    Сторона установки ИКИ по ГОСТ Р 50.05.07-2018, п. 6.1.11.

    :param iqi_side: выбор пользователя — ``source`` (по умолчанию) или ``film``
    """
    if iqi_side == SIDE_FILM:
        return {
            'side': SIDE_FILM,
            'side_label': 'со стороны плёнки',
            'shift_steps': 1,
            'note': (
                'ИКИ со стороны плёнки: проволочный эталон на одну ступень '
                'жёстче относительно требуемой чувствительности K (п. 6.1.11).'
            ),
        }

    return {
        'side': SIDE_SOURCE,
        'side_label': 'со стороны источника',
        'shift_steps': 0,
        'note': 'ИКИ устанавливается со стороны источника излучения (п. 6.1.11).',
    }


# ------------------------------------------------------------------
# Приложение 5–6: условная запись дефектов
# ------------------------------------------------------------------

NOTATION_REFERENCE = 'ГОСТ 7512-82, приложение 5'

# Отдельное / цепочка / скопление (русский алфавит, табл. прил. 5)
NOTATION_KIND = {
    'pore': {'single': 'П', 'chain': 'ЦП', 'cluster': 'СП'},
    'slag': {'single': 'Ш', 'chain': 'ЦШ', 'cluster': 'СШ'},
    'tungsten': {'single': 'В', 'chain': 'ЦВ', 'cluster': 'СВ'},
}

NOTATION_LINEAR = {
    'crack': 'Т',
    'incomplete_penetration': 'Н',
    'undercut': 'Пдр',
    'excess_penetration': 'Впк',
}

NOTATION_FULL_NAME = {
    'lack_of_fusion': 'Несплавление',
    'surface_defect': 'Поверхностный дефект',
}


def _fmt_gost_mm(value: float) -> str:
    """Форматирует размер, мм, как в примерах приложения 6 (десятичная запятая)."""
    if value is None or value <= 0:
        return ''
    rounded = round(float(value), 3)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    return f'{rounded:g}'.replace('.', ',')


def _count_prefix(count: int) -> str:
    return str(count) if count and count > 1 else ''


def _inclusion_size_suffix(
    size_1: float,
    size_2: float,
    *,
    elongated: bool,
) -> str:
    """Размеры включения после кода (п. 3–4 приложения 5)."""
    if elongated and size_1 > 0 and size_2 > 0:
        return f'{_fmt_gost_mm(size_1)}x{_fmt_gost_mm(size_2)}'
    if size_1 > 0:
        return _fmt_gost_mm(size_1)
    return ''


def format_sigma_notation(total_length_mm: float) -> str:
    """Σ — максимальная суммарная длина дефектов на участке 100 мм (п. 2, 6)."""
    if total_length_mm <= 0:
        return ''
    return f'Σ{_fmt_gost_mm(total_length_mm)}'


def format_gost_7512_defect_notation(
    defect_type: str,
    size_1: float = 0,
    size_2: float = 0,
    count: int = 1,
    *,
    morphology: str = 'single',
    elongated: bool | None = None,
    max_inclusion_w: float | None = None,
    max_inclusion_l: float | None = None,
) -> str:
    """
    Формирует условную запись дефекта по ГОСТ 7512-82, приложения 5–6.

    :param defect_type: код типа дефекта из модуля оценки качества
    :param size_1: основной размер (диаметр / длина / глубина), мм
    :param size_2: второй размер (ширина удлинённого включения, длина подреза), мм
    :param count: число одинаковых дефектов (п. 5)
    :param morphology: ``single`` | ``chain`` | ``cluster``
    :param elongated: удлинённое включение (ширина × длина); иначе — сферическое
    :param max_inclusion_w: макс. ширина включения в цепочке/скоплении
    :param max_inclusion_l: макс. длина включения в цепочке/скоплении
    """
    count = max(int(count or 1), 1)
    size_1 = float(size_1 or 0)
    size_2 = float(size_2 or 0)

    if defect_type in NOTATION_FULL_NAME:
        name = NOTATION_FULL_NAME[defect_type]
        if size_1 > 0:
            return f'{name} {_fmt_gost_mm(size_1)}'
        return name

    if defect_type == 'cluster':
        morphology = 'cluster'
        defect_type = 'pore'

    if defect_type in NOTATION_KIND:
        morph = morphology if morphology in ('single', 'chain', 'cluster') else 'single'
        kind = NOTATION_KIND[defect_type]['single']
        prefix = _count_prefix(count)

        if morph == 'chain':
            chain_len = _fmt_gost_mm(size_1)
            if not chain_len:
                return ''
            max_l = max_inclusion_l if max_inclusion_l is not None else size_2
            max_w = max_inclusion_w if max_inclusion_w is not None else 0
            if max_l > 0 and max_w > 0:
                incl = f'{kind}{_fmt_gost_mm(max_l)}x{_fmt_gost_mm(max_w)}'
            elif size_2 > 0:
                incl = f'{kind}{_fmt_gost_mm(size_2)}'
            else:
                incl = kind
            return f'{prefix}Ц{chain_len}{incl}'

        if morph == 'cluster':
            cluster_len = _fmt_gost_mm(size_1)
            if not cluster_len:
                return ''
            max_l = max_inclusion_l if max_inclusion_l is not None else 0
            max_w = max_inclusion_w if max_inclusion_w is not None else size_2
            if max_l > 0 and max_w > 0:
                incl = f'{kind}{_fmt_gost_mm(max_l)}x{_fmt_gost_mm(max_w)}'
            elif size_2 > 0:
                incl = f'{kind}{_fmt_gost_mm(size_2)}'
            else:
                incl = ''
            return f'{prefix}С{cluster_len}{incl}'

        code = kind
        is_elongated = elongated if elongated is not None else (size_2 > 0)
        sizes = _inclusion_size_suffix(size_1, size_2, elongated=is_elongated)
        if not sizes:
            return ''
        return f'{prefix}{code}{sizes}'

    if defect_type in NOTATION_LINEAR:
        code = NOTATION_LINEAR[defect_type]
        if defect_type == 'undercut' and size_1 > 0 and size_2 > 0:
            parts = [f'{_count_prefix(count)}{code}{_fmt_gost_mm(size_1)}']
            sigma = format_sigma_notation(size_2)
            if sigma:
                parts.append(sigma)
            return '; '.join(parts)
        length = size_1 or size_2
        if length <= 0:
            return ''
        return f'{_count_prefix(count)}{code}{_fmt_gost_mm(length)}'

    return ''


def format_gost_7512_notation_list(notations: list[str]) -> str:
    """Объединяет записи дефектов через «;» (примеры приложения 6)."""
    items = [n for n in notations if n]
    return '; '.join(items)
