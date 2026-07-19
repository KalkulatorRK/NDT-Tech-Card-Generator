"""
Толщина стенки S / S1 для типов соединений ГОСТ Р 59023.2-2020.

Большинство таблиц ГОСТ имеют колонку «S = S1» — номинальная толщина
стенки и толщина в зоне шва совпадают.

Табл. 9.30 объединяет С-22-2 и С-23-2, но по чертежу конструктивных
элементов:
  - С-22-2 — без внутренней расточки, S = S1;
  - С-23-2 — с расточкой: типоразмер Dн×S, диаметр расточки Dр и
    минимальная толщина стенки S1 (S ≠ S1).

Числовые строки С-23-2 в текстовом RTF ГОСТ вшиты в изображения;
ниже воспроизведены по совпадающим строкам НП-104-18 (тот же код
и типоразмеры) и сверены с табл. 9.30 / чертежом ГОСТ Р 59023.2-2020.

Важно: в НП-104-18 для ряда кодов (в т.ч. С-42, С-22-2) колонки Dр/S1
могут заполняться иначе, чем в ГОСТ. Каталог приложения следует ГОСТ.
"""

from __future__ import annotations

# Внутренняя расточка и S1 — только у С-23-2 (чертёж табл. 9.30).
# С-22-2 в той же таблице, но без расточки (S = S1).
GOST_BORED_JOINT_CODES = frozenset({'С-23-2'})

# Строки табл. 9.30 для С-23-2: Dн×S → Dр, S1, e (±)
GOST_BORING_ROWS: dict[str, list[dict]] = {
    'С-23-2': [
        {'dn_mm': 25.0, 's_mm': 3.0, 'dp_mm': 19.0, 's1_mm': 2.5,
         'e_mm': 7.0, 'e_tol_mm': 2.0, 'g1_max_mm': 2.0},
        {'dn_mm': 57.0, 's_mm': 3.0, 'dp_mm': 52.0, 's1_mm': 1.8,
         'e_mm': 7.0, 'e_tol_mm': 2.0, 'g1_max_mm': 2.0},
        {'dn_mm': 57.0, 's_mm': 3.0, 'dp_mm': 51.0, 's1_mm': 1.8,
         'e_mm': 7.0, 'e_tol_mm': 2.0, 'g1_max_mm': 2.0},
        {'dn_mm': 76.0, 's_mm': 3.0, 'dp_mm': 71.0, 's1_mm': 1.8,
         'e_mm': 7.0, 'e_tol_mm': 2.0, 'g1_max_mm': 2.0},
        {'dn_mm': 89.0, 's_mm': 3.5, 'dp_mm': 84.0, 's1_mm': 2.4,
         'e_mm': 8.0, 'e_tol_mm': 2.0, 'g1_max_mm': 2.0},
        {'dn_mm': 89.0, 's_mm': 3.5, 'dp_mm': 84.0, 's1_mm': 2.2,
         'e_mm': 8.0, 'e_tol_mm': 2.0, 'g1_max_mm': 2.0},
        {'dn_mm': 108.0, 's_mm': 4.0, 'dp_mm': 102.0, 's1_mm': 2.4,
         'e_mm': 9.0, 'e_tol_mm': 3.0, 'g1_max_mm': 2.0},
        {'dn_mm': 133.0, 's_mm': 4.0, 'dp_mm': 127.0, 's1_mm': 2.6,
         'e_mm': 9.0, 'e_tol_mm': 3.0, 'g1_max_mm': 2.0},
        {'dn_mm': 159.0, 's_mm': 5.0, 'dp_mm': 151.0, 's1_mm': 3.0,
         'e_mm': 11.0, 'e_tol_mm': 3.0, 'g1_max_mm': 2.0},
    ],
}


def joint_has_internal_boring(joint_code: str) -> bool:
    """True, если по ГОСТ Р 59023.2 для типа задана внутренняя расточка."""
    return joint_code in GOST_BORED_JOINT_CODES


def joint_s_equals_s1(joint_code: str) -> bool:
    """True, если в таблице ГОСТ для типа действует S = S1."""
    return not joint_has_internal_boring(joint_code)


def get_joint_wall_meta(joint_code: str) -> dict:
    """Метаданные S/S1 для типа соединения (без привязки к типоразмеру)."""
    bored = joint_has_internal_boring(joint_code)
    if bored:
        wall_note = (
            'ГОСТ Р 59023.2-2020, табл. 9.30 (С-23-2): '
            'внутренняя расточка на чертеже, S ≠ S1'
        )
    elif joint_code == 'С-22-2':
        wall_note = (
            'ГОСТ Р 59023.2-2020, табл. 9.30 (С-22-2): '
            'на чертеже без расточки, S = S1'
        )
    else:
        wall_note = 'ГОСТ Р 59023.2-2020: в таблице соединений S = S1'
    return {
        'has_internal_boring': bored,
        's_equals_s1': not bored,
        'wall_thickness_mode': 'bored' if bored else 's_equals_s1',
        'boring_gost_table': '9.30' if bored else None,
        'boring_rows': list(GOST_BORING_ROWS.get(joint_code, [])),
        'wall_note': wall_note,
    }


def lookup_gost_boring_row(
    joint_code: str,
    outer_diameter_mm: float | None,
    wall_thickness_mm: float | None,
) -> dict | None:
    """
    Строка табл. 9.30 (С-23-2) по Dн×S.

    При нескольких строках с одним Dн×S (разный Dр) выбирается строка
    с наименьшей S1 (консервативно для РГК).
    """
    rows = GOST_BORING_ROWS.get(joint_code) or []
    if not rows or outer_diameter_mm is None or wall_thickness_mm is None:
        return None
    dn = float(outer_diameter_mm)
    s = float(wall_thickness_mm)
    exact = [
        r for r in rows
        if abs(r['dn_mm'] - dn) < 0.05 and abs(r['s_mm'] - s) < 0.05
    ]
    if exact:
        return min(exact, key=lambda r: r['s1_mm'])
    return min(
        rows,
        key=lambda r: (abs(r['dn_mm'] - dn), abs(r['s_mm'] - s)),
    )


def resolve_joint_wall_thickness(
    joint_code: str,
    wall_thickness_mm: float,
    outer_diameter_mm: float | None = None,
    s1_override_mm: float | None = None,
) -> dict:
    """
    Номинальная S, толщина в зоне шва S1 и эффективная толщина для РГК.

    S_eff = S1 при расточке (или при явном s1_override), иначе S.
    """
    meta = get_joint_wall_meta(joint_code)
    s = float(wall_thickness_mm)
    row = None
    s1 = s
    dp = None
    source = 's_equals_s1'

    if s1_override_mm not in (None, ''):
        s1 = float(s1_override_mm)
        source = 'user_s1_override'
        if abs(s1 - s) > 1e-6:
            meta = dict(meta)
            meta['s_equals_s1'] = False
            meta['has_internal_boring'] = True
            meta['wall_thickness_mode'] = 'bored'
    elif meta['has_internal_boring']:
        row = lookup_gost_boring_row(joint_code, outer_diameter_mm, s)
        if row:
            s1 = float(row['s1_mm'])
            dp = row.get('dp_mm')
            source = 'gost_59023.2_table_9.30'
        else:
            source = 'bored_no_typosize_fallback_s'

    s_eff = s1
    s_equals = abs(s_eff - s) < 1e-6

    return {
        **meta,
        's_mm': round(s, 2),
        's1_mm': round(s1, 2),
        's_eff_mm': round(s_eff, 2),
        'dp_mm': round(dp, 2) if dp is not None else None,
        's_equals_s1_actual': s_equals,
        'boring_row': row,
        'wall_resolve_source': source,
        'wall_summary': (
            f'S = S1 = {s:g} мм'
            if s_equals else
            f'S = {s:g} мм, S1 = {s1:g} мм (расточка'
            + (f', Dр = {dp:g} мм' if dp is not None else '')
            + ')'
        ),
    }
