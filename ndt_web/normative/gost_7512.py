"""
ГОСТ 7512-82 — проволочные эталоны чувствительности (ИКИ).

Таблица 2: четыре типоразмера эталонов, в каждом семь проволок.
Номер проволоки 1 — наибольший диаметр, 7 — наименьший.
"""

from __future__ import annotations

from typing import Optional

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

SIDE_SOURCE = 'source'
SIDE_FILM = 'film'


def _all_wires() -> list[tuple[int, int, float]]:
    wires: list[tuple[int, int, float]] = []
    for set_no, items in WIRE_IQI_SETS.items():
        for wire_no, diameter in items:
            wires.append((set_no, wire_no, diameter))
    return wires


def select_iqi_set_number(radiation_thickness_mm: float) -> int:
    """Подбирает номер проволочного эталона (1–4) по радиационной толщине."""
    for set_no, max_t in SET_THICKNESS_MAX_MM.items():
        if radiation_thickness_mm <= max_t:
            return set_no
    return 4


def get_wire_iqi(
    radiation_thickness_mm: float,
    k_mm: float,
    shift_steps: int = 0,
) -> dict:
    """
    Определяет типоразмер эталона и номер проволоки по ГОСТ 7512-82.

    Требуемая чувствительность K — наименьший диаметр проволоки, который
    должен быть виден на снимке. Выбирается проволока с d ≤ K; при сдвиге
    на одну ступень жёстче берётся следующая (более тонкая) проволока.

    :param radiation_thickness_mm: радиационная толщина в месте установки ИКИ
    :param k_mm: требуемая чувствительность K, мм (НП-105-18)
    :param shift_steps: сдвиг на N ступеней жёстче (для ИКИ со стороны плёнки)
    """
    set_no = select_iqi_set_number(radiation_thickness_mm)
    wires = WIRE_IQI_SETS[set_no]

    # Проволока с d ≤ K, начиная с наименьшего диаметра в наборе.
    candidates = [w for w in wires if w[1] <= k_mm + 1e-9]
    if not candidates:
        wire_no, diameter = wires[-1]
    else:
        wire_no, diameter = max(candidates, key=lambda w: w[1])

    if shift_steps:
        idx = next(i for i, w in enumerate(wires) if w[0] == wire_no)
        idx = min(idx + shift_steps, len(wires) - 1)
        wire_no, diameter = wires[idx]

    return {
        'set_number': set_no,
        'wire_number': wire_no,
        'wire_diameter_mm': diameter,
        'label': f'№{set_no}, проволока {wire_no} (Ø {diameter:g} мм)',
        'standard': 'ГОСТ 7512-82, табл. 2',
    }


def resolve_iqi_placement(
    scheme_code: str,
    wall_count: int,
    film_side_decode: bool = True,
) -> dict:
    """
    Сторона установки ИКИ по ГОСТ Р 50.05.07-2018, п. 6.1.11.

  - По умолчанию — со стороны источника.
  - Для трубопроводов при просвечивании через две стенки (схемы 3в, 3г, 3д)
    допускается установка со стороны плёнки; чувствительность сдвигается
    на одну ступень жёстче.
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
