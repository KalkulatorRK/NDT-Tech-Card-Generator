"""
ГОСТ 7512-82 — проволочные эталоны чувствительности (ИКИ).

Таблица 2: четыре типоразмера эталонов, в каждом семь проволок.
Маркировка (п. 2.13): первая цифра — материал, следующие 1–2 цифры — номер эталона.
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
    scheme_code: str,
    wall_count: int,
    film_side_decode: bool = True,
) -> dict:
    """
    Сторона установки ИКИ по ГОСТ Р 50.05.07-2018, п. 6.1.11.
    """
    two_wall_outside_film = wall_count == 2 and scheme_code in ('5v', '5g', '5d')

    if two_wall_outside_film and film_side_decode:
        return {
            'side': SIDE_FILM,
            'side_label': 'со стороны плёнки',
            'shift_steps': 1,
            'note': (
                'Просвечивание через две стенки: ИКИ со стороны плёнки; '
                'чувствительность на одну ступень жёстче (п. 6.1.11).'
            ),
        }

    return {
        'side': SIDE_SOURCE,
        'side_label': 'со стороны источника',
        'shift_steps': 0,
        'note': 'ИКИ устанавливается со стороны источника излучения (п. 6.1.11).',
    }
