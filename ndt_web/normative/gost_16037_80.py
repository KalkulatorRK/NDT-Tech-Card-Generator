"""
Данные ГОСТ 16037-80 «Соединения сварные стальных трубопроводов.
Основные типы, конструктивные элементы и размеры».

Используется совместно со СНиП 3.05.05-84 (строительные трубопроводы).

Источник данных: `_gost_16037_extract.json` (извлечение из PDF ГОСТ 16037-80).
Эскизы: `static/techcards/joints/gost_16037/<CODE>.png`.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

DOCUMENT_CODE = 'ГОСТ 16037-80'
DOCUMENT_FULL_NAME = (
    'ГОСТ 16037-80 «Соединения сварные стальных трубопроводов. '
    'Основные типы, конструктивные элементы и размеры»'
)

_EXTRACT_PATH = Path(__file__).resolve().parent / '_gost_16037_extract.json'
_STATIC_JOINTS_REL = 'techcards/joints/gost_16037'
_STATIC_ROOT = Path(__file__).resolve().parent.parent / 'static'

HAZ_WIDTH_MM = 5.0

# Порядок групп для UI / сортировки
_JOINT_TYPE_ORDER = ('butt', 'corner', 'lap')
_PREFIX_ORDER = {'С': 0, 'У': 1, 'Н': 2}

JOINT_GROUP_LABELS = {
    'steel_pipeline|butt': '— Стыковые (С), ГОСТ 16037-80 —',
    'steel_pipeline|corner': '— Угловые (У), ГОСТ 16037-80 —',
    'steel_pipeline|lap': '— Нахлёсточные (Н), ГОСТ 16037-80 —',
}


def _load_extract() -> dict:
    with open(_EXTRACT_PATH, encoding='utf-8') as fh:
        return json.load(fh)


_EXTRACT = _load_extract()

WELDING_PROCESSES: dict[str, dict] = {
    code: {
        'code': code,
        'name': info['name'],
        'iso_ref': info.get('iso_ref', ''),
    }
    for code, info in _EXTRACT.get('welding_processes', {}).items()
}


def _strip_runtime_fields(info: dict) -> dict:
    """Убирает тяжёлые поля извлечения, сохраняет путь к эскизу."""
    cleaned = copy.deepcopy(info)
    cleaned.pop('sketch_source', None)
    sketch = cleaned.get('sketch') or ''
    if not sketch and cleaned.get('sketch_file'):
        # sketch_file: static/techcards/... → relative to STATIC root
        sf = cleaned['sketch_file'].replace('\\', '/')
        if sf.startswith('static/'):
            sketch = sf[len('static/'):]
        else:
            sketch = sf
        cleaned['sketch'] = sketch
    return cleaned


def _joint_type_to_group_suffix(joint_type: str) -> str:
    mapping = {
        'butt': 'butt',
        'corner': 'corner',
        'lap': 'lap',
        'tee': 'tee',
    }
    return mapping.get(joint_type, joint_type or 'butt')


def get_joint_group_key(joint_code: str, info: dict | None = None) -> str:
    """Ключ optgroup: steel_pipeline|butt|corner|lap."""
    info = info if info is not None else JOINT_TYPES.get(joint_code, {})
    jt = info.get('joint_type') or _infer_joint_type_from_code(joint_code)
    return f'steel_pipeline|{_joint_type_to_group_suffix(jt)}'


def _infer_joint_type_from_code(code: str) -> str:
    if code.startswith('У'):
        return 'corner'
    if code.startswith('Н'):
        return 'lap'
    return 'butt'


def _enrich_joint(code: str, info: dict) -> dict:
    info = _strip_runtime_fields(info)
    info.setdefault('code', code)
    info.setdefault('material', 'steel_pipeline')
    if not info.get('joint_type'):
        info['joint_type'] = _infer_joint_type_from_code(code)
    info['group_key'] = get_joint_group_key(code, info)
    if not info.get('sketch'):
        info['sketch'] = f'{_STATIC_JOINTS_REL}/{code}.png'
    return info


JOINT_TYPES: dict[str, dict] = {
    code: _enrich_joint(code, info)
    for code, info in _EXTRACT.get('JOINT_TYPES', {}).items()
}


def _joint_code_sort_key(code: str) -> tuple:
    """С* → У* → Н*, внутри — по номеру."""
    m = re.match(r'^([СУН])(\d+)$', code)
    if not m:
        return (99, 0, code)
    prefix, num = m.group(1), int(m.group(2))
    return (_PREFIX_ORDER.get(prefix, 99), num, code)


def _joint_sort_key(code: str) -> tuple:
    info = JOINT_TYPES.get(code, {})
    jt = info.get('joint_type') or _infer_joint_type_from_code(code)
    type_idx = _JOINT_TYPE_ORDER.index(jt) if jt in _JOINT_TYPE_ORDER else 99
    return (type_idx, _joint_code_sort_key(code))


ALL_JOINT_CODES = sorted(JOINT_TYPES.keys(), key=_joint_sort_key)


def is_gost_16037_joint(code: str) -> bool:
    """True, если код есть в каталоге ГОСТ 16037-80."""
    return code in JOINT_TYPES


def get_joint_group_labels_for_ui() -> dict[str, str]:
    """Подписи optgroup для передачи в шаблон (JSON)."""
    return dict(JOINT_GROUP_LABELS)


def format_joint_choice_label(code: str, info: dict) -> str:
    """Подпись пункта списка типов соединений."""
    table_ref = info.get('gost_table')
    table_suffix = f', табл. {table_ref}' if table_ref else ''
    name = info.get('name') or code
    return f'{code} — {name}{table_suffix}'


def iter_joint_codes() -> list[str]:
    """Коды соединений в порядке С → У → Н."""
    return list(ALL_JOINT_CODES)


def get_joint_type_choices() -> list[tuple[str, str]]:
    """Список кортежей для выпадающего списка типов соединений."""
    choices: list[tuple[str, str]] = [('', '— Выберите тип сварного соединения —')]
    last_group: str | None = None
    for code in ALL_JOINT_CODES:
        info = JOINT_TYPES[code]
        group = info.get('group_key') or get_joint_group_key(code, info)
        if group != last_group:
            label = JOINT_GROUP_LABELS.get(group)
            if label and len(choices) > 1:
                choices.append((f'__group_{code}__', label))
            elif label and len(choices) == 1:
                choices.append((f'__group_{code}__', label))
            last_group = group
        choices.append((code, format_joint_choice_label(code, info)))
    return choices


def get_welding_process_choices() -> list[tuple[str, str]]:
    """Список кортежей для выпадающего списка способов сварки."""
    order = ('ЗП', 'ЗН', 'Р', 'Ф', 'Г')
    choices = []
    for code in order:
        info = WELDING_PROCESSES.get(code)
        if info:
            choices.append((code, f'{code} — {info["name"]}'))
    for code, info in WELDING_PROCESSES.items():
        if code not in order:
            choices.append((code, f'{code} — {info["name"]}'))
    return choices


def get_welding_process_choices_for_joint(joint_code: str) -> list[tuple[str, str]]:
    """Допустимые способы сварки для типа соединения."""
    info = JOINT_TYPES.get(joint_code, {})
    allowed = info.get('methods') or list(WELDING_PROCESSES.keys())
    choices: list[tuple[str, str]] = [('', '— Выберите способ сварки —')]
    for code, label in get_welding_process_choices():
        if code in allowed:
            choices.append((code, label))
    return choices


def get_joint_image_path(joint_code: str) -> str:
    """
    Относительный путь к эскизу от STATIC root,
    напр. ``techcards/joints/gost_16037/С17.png``.
    """
    info = JOINT_TYPES.get(joint_code, {})
    sketch = (info.get('sketch') or '').replace('\\', '/')
    if sketch:
        if sketch.startswith('static/'):
            return sketch[len('static/'):]
        return sketch
    return f'{_STATIC_JOINTS_REL}/{joint_code}.png'


def get_joint_image_abs_path(joint_code: str) -> Path | None:
    """Абсолютный путь к PNG на диске или None, если файла нет."""
    rel = get_joint_image_path(joint_code)
    if not rel:
        return None
    abs_path = _STATIC_ROOT / Path(rel)
    if abs_path.is_file():
        return abs_path
    fallback = _STATIC_ROOT / _STATIC_JOINTS_REL / f'{joint_code}.png'
    if fallback.is_file():
        return fallback
    return None


def get_joint_info(joint_code: str) -> dict:
    """Полная информация о типе соединения (копия) + image."""
    info = JOINT_TYPES.get(joint_code)
    if not info:
        return {}
    result = copy.deepcopy(info)
    result['image'] = get_joint_image_path(joint_code)
    result['group_key'] = result.get('group_key') or get_joint_group_key(joint_code, result)
    return result


def _row_s_bounds(row: dict) -> tuple[float | None, float | None]:
    if 's' in row and row['s'] is not None:
        s = float(row['s'])
        return s, s
    s_min = row.get('s_min')
    s_max = row.get('s_max')
    if s_min is None and s_max is None:
        return None, None
    if s_min is None:
        s_min = s_max
    if s_max is None:
        s_max = s_min
    return float(s_min), float(s_max)


def get_joint_thickness_ranges(joint_code: str) -> list[dict]:
    """
    Диапазоны толщины для UI (JSON-friendly).

    Приоритет: methods_limits → thickness_range → уникальные s из dimensions.
    """
    info = JOINT_TYPES.get(joint_code, {})
    result: list[dict] = []

    methods_limits = info.get('methods_limits') or {}
    if methods_limits:
        for method, lim in methods_limits.items():
            s_min = lim.get('s_min')
            s_max = lim.get('s_max')
            if s_min is None and s_max is None:
                continue
            entry: dict[str, Any] = {
                'method': method,
                's_min': float(s_min if s_min is not None else s_max),
                's_max': float(s_max if s_max is not None else s_min),
            }
            if lim.get('dn_min') is not None:
                entry['dn_min'] = lim['dn_min']
            if lim.get('dn_max') is not None:
                entry['dn_max'] = lim['dn_max']
            result.append(entry)
        return result

    tr = info.get('thickness_range') or {}
    if tr.get('s_min') is not None or tr.get('s_max') is not None:
        return [{
            's_min': float(tr.get('s_min') if tr.get('s_min') is not None else tr.get('s_max')),
            's_max': float(tr.get('s_max') if tr.get('s_max') is not None else tr.get('s_min')),
        }]

    seen: set[tuple[float, float]] = set()
    for row in info.get('dimensions') or []:
        s_min, s_max = _row_s_bounds(row)
        if s_min is None:
            continue
        key = (s_min, s_max)
        if key in seen:
            continue
        seen.add(key)
        result.append({'s_min': s_min, 's_max': s_max})
    return result


def format_joint_thickness_ranges(joint_code: str) -> str:
    """Краткая строка допустимых S (напр. «2–5; 4–6 мм»)."""
    ranges = get_joint_thickness_ranges(joint_code)
    if not ranges:
        return ''
    parts: list[str] = []
    seen: set[str] = set()
    for r in ranges:
        s_min, s_max = r['s_min'], r['s_max']
        if abs(s_min - s_max) < 1e-9:
            part = f'{s_min:g}'.replace('.', ',')
        else:
            part = f'{s_min:g}–{s_max:g}'.replace('.', ',')
        if part not in seen:
            seen.add(part)
            parts.append(part)
    return '; '.join(parts) + ' мм'


def is_joint_thickness_allowed(
    joint_code: str,
    thickness_mm: float,
    method: str | None = None,
    dn_mm: float | None = None,
) -> bool:
    """
    True, если S (и при необходимости способ / Ду) допустимы для соединения.
    """
    info = JOINT_TYPES.get(joint_code, {})
    if not info:
        return False

    methods_limits = info.get('methods_limits') or {}
    if method and method in methods_limits:
        lim = methods_limits[method]
        s_min = lim.get('s_min')
        s_max = lim.get('s_max')
        if s_min is not None and thickness_mm < float(s_min) - 1e-9:
            return False
        if s_max is not None and thickness_mm > float(s_max) + 1e-9:
            return False
        if dn_mm is not None:
            dn_min = lim.get('dn_min')
            dn_max = lim.get('dn_max')
            if dn_min is not None and dn_mm < float(dn_min) - 1e-9:
                return False
            if dn_max is not None and dn_mm > float(dn_max) + 1e-9:
                return False
        return True

    if method and methods_limits and method not in methods_limits:
        # способ не заявлен для соединения
        allowed_methods = info.get('methods') or []
        if allowed_methods and method not in allowed_methods:
            return False

    tr = info.get('thickness_range') or {}
    if tr.get('s_min') is not None or tr.get('s_max') is not None:
        s_min = float(tr['s_min']) if tr.get('s_min') is not None else None
        s_max = float(tr['s_max']) if tr.get('s_max') is not None else None
        if s_min is not None and thickness_mm < s_min - 1e-9:
            return False
        if s_max is not None and thickness_mm > s_max + 1e-9:
            return False
        return True

    ranges = get_joint_thickness_ranges(joint_code)
    if not ranges:
        return True
    return any(
        r['s_min'] - 1e-9 <= thickness_mm <= r['s_max'] + 1e-9
        for r in ranges
    )


def _parse_tol_mm(tol: Any) -> float | None:
    """Извлекает числовой допуск из строки вида «+2», «±0,5», «+1»."""
    if tol is None:
        return None
    if isinstance(tol, (int, float)):
        return abs(float(tol))
    s = str(tol).strip().replace(',', '.').replace('±', '').replace('+', '').replace('−', '-')
    s = s.replace('-', '')
    try:
        return abs(float(s))
    except ValueError:
        return None


def _estimate_e_mm(thickness_mm: float) -> float:
    return float(round(max(4.0, 1.2 * thickness_mm)))


def _estimate_g_mm(thickness_mm: float) -> float:
    if thickness_mm <= 3:
        return 1.0
    if thickness_mm <= 6:
        return 1.5
    if thickness_mm <= 12:
        return 2.0
    return 2.5


def _row_matches_method(row: dict, method: str | None) -> bool:
    if not method:
        return True
    methods = row.get('methods') or []
    if not methods:
        return True
    return method in methods


def _row_matches_thickness(row: dict, thickness_mm: float) -> bool:
    s_min, s_max = _row_s_bounds(row)
    if s_min is None:
        return False
    return s_min - 1e-9 <= thickness_mm <= s_max + 1e-9


def lookup_dimensions(
    joint_code: str,
    thickness_mm: float,
    method: str,
) -> dict:
    """
    Ищет строку dimensions по методу и толщине.

    Возвращает e_nom, g_nom, b_nom и tol-поля; при отсутствии — оценку
    с флагом ``approximate=True``.
    """
    info = JOINT_TYPES.get(joint_code, {})
    table_ref = info.get('gost_table') or ''
    rows = info.get('dimensions') or []

    matched: dict | None = None
    # 1) точное совпадение method + S
    for row in rows:
        if _row_matches_method(row, method) and _row_matches_thickness(row, thickness_mm):
            matched = row
            break
    # 2) любой method при совпадении S
    if matched is None:
        for row in rows:
            if _row_matches_thickness(row, thickness_mm):
                matched = row
                break

    if matched is not None:
        e_nom = matched.get('e_nom')
        g_nom = matched.get('g_nom')
        if e_nom is None:
            e_nom = _estimate_e_mm(thickness_mm)
        if g_nom is None:
            g_nom = _estimate_g_mm(thickness_mm)
        result = {
            'e_nom': float(e_nom),
            'g_nom': float(g_nom),
            'b_nom': matched.get('b_nom'),
            'e_tol': matched.get('e_tol'),
            'g_tol': matched.get('g_tol'),
            'b_tol': matched.get('b_tol'),
            'e_tol_mm': _parse_tol_mm(matched.get('e_tol')),
            'g_tol_mm': _parse_tol_mm(matched.get('g_tol')),
            'b_tol_mm': _parse_tol_mm(matched.get('b_tol')),
            'approximate': False,
            'gost_table': table_ref,
            'source_row': copy.deepcopy(matched),
        }
        # доп. поля из строки (K, delta, c, …)
        for key in ('K', 'K_min', 'K1', 'c', 'delta', 'a', 'B', 'l', 'f', 'Dn'):
            if key in matched:
                result[key] = matched[key]
        return result

    e_nom = _estimate_e_mm(thickness_mm)
    g_nom = _estimate_g_mm(thickness_mm)
    note_table = f'табл. {table_ref}' if table_ref else 'таблицам ГОСТ'
    return {
        'e_nom': e_nom,
        'g_nom': g_nom,
        'b_nom': None,
        'e_tol': None,
        'g_tol': None,
        'b_tol': None,
        'e_tol_mm': None,
        'g_tol_mm': None,
        'b_tol_mm': None,
        'approximate': True,
        'gost_table': table_ref,
        'source_row': None,
        'note': (
            f'Размеры e/g оценены приближённо (нет строки dimensions для S={thickness_mm:g} мм); '
            f'уточнить по ГОСТ 16037-80, {note_table}'
        ),
    }


def format_dimension_with_tolerance(value_mm: float, tolerance_mm: float | None = None) -> str:
    """Форматирует размер: «15,0» или «15,0 ±2,0» / «15,0 +2,0»."""
    base = f'{value_mm:.1f}'.replace('.', ',')
    if tolerance_mm is None or tolerance_mm <= 0:
        return base
    return base + f' ±{tolerance_mm:.1f}'.replace('.', ',')


def joint_uses_backing(joint_code: str, welding_method: str = 'Р') -> bool:
    """True, если в описании шва указана остающаяся / съёмная подкладка."""
    info = JOINT_TYPES.get(joint_code, {})
    text = ' '.join([
        str(info.get('weld_character') or ''),
        str(info.get('name') or ''),
        str(info.get('notes') or ''),
    ]).lower()
    return 'подклад' in text


def get_inspection_zone(
    joint_code: str,
    thickness_mm: float,
    welding_method: str = 'Р',
    *,
    material_type: str = 'steel',
    s1_override_mm: float | None = None,
    reinforcement_removed: bool = False,
    has_backing_ring: bool | None = None,
    backing_ring_thickness_mm: float | None = None,
    outer_diameter_mm: float | None = None,
    dn_mm: float | None = None,
    **_kwargs: Any,
) -> dict:
    """
    Геометрия контролируемой зоны и валика для техкарты / AJAX.

    Ключи совместимы с ``gost_59023_2.get_inspection_zone``.
    """
    info = JOINT_TYPES.get(joint_code, {})
    dims = lookup_dimensions(joint_code, thickness_mm, welding_method)

    e = float(dims['e_nom'])
    e_tol = dims.get('e_tol_mm')
    if e_tol is None:
        e_tol = 2.0 if e >= 6 else 1.5
    e_max = round(e + e_tol, 1)
    e1 = e
    e1_tol = e_tol
    e1_max = e_max
    effective_e = e
    effective_e_max = e_max
    bead_mode = 'equal'

    g_nom = float(dims['g_nom'])
    g_tol = dims.get('g_tol_mm')
    if g_tol is not None:
        g_min = max(0.0, g_nom - g_tol)
        g_max = g_nom + g_tol
    else:
        g_min = max(0.0, g_nom - 1.5)
        g_max = g_nom + 1.5

    if reinforcement_removed:
        g_nom = 0.0
        g_min = 0.0
        g_max = 0.0

    table_ref = dims.get('gost_table') or info.get('gost_table') or ''
    if dims.get('approximate'):
        weld_note = dims.get('note') or (
            f'Ориентировочные e/g по ГОСТ 16037-80'
            + (f', табл. {table_ref}' if table_ref else '')
        )
    else:
        weld_note = (
            f'По ГОСТ 16037-80'
            + (f', табл. {table_ref}' if table_ref else '')
        )
        if info.get('dimensions_notes'):
            weld_note += f'. {info["dimensions_notes"]}'

    # ОШЗ / зона контроля (инженерная оценка, совместимая с АЭУ-логикой)
    if thickness_mm <= 5:
        haz_width = HAZ_WIDTH_MM
    elif thickness_mm <= 20:
        haz_width = max(HAZ_WIDTH_MM, thickness_mm * 0.3)
    else:
        haz_width = max(HAZ_WIDTH_MM, min(20.0, thickness_mm * 0.25))
    haz_width = round(haz_width, 1)

    zone_width = effective_e_max + 2 * haz_width

    if thickness_mm <= 5:
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
            # delta из строки dimensions, если есть
            delta = dims.get('delta')
            backing_thickness = float(delta) if delta is not None else float(thickness_mm)
    else:
        backing_thickness = 0.0

    s_mm = float(thickness_mm)
    s1_mm = float(s1_override_mm) if s1_override_mm is not None else s_mm
    s_equals_s1 = abs(s_mm - s1_mm) < 1e-9
    s_eff_mm = max(s_mm, s1_mm)

    wall_summary = (
        f'S = {s_mm:g} мм'
        if s_equals_s1
        else f'S = {s_mm:g} мм, S1 = {s1_mm:g} мм'
    )
    wall_note = 'Толщина стенки трубы по ГОСТ 16037-80 (S).'
    wall_thickness_mode = 'equal' if s_equals_s1 else 'unequal'

    e_display = format_dimension_with_tolerance(e, e_tol)
    e1_display = format_dimension_with_tolerance(e1, e1_tol)
    g_display = f'{g_nom:.1f}'.replace('.', ',')

    ref = f'{DOCUMENT_CODE}'
    if table_ref:
        ref += f', табл. {table_ref}'
    ref += '; СНиП 3.05.05-84; ГОСТ 7512-82'

    return {
        'bead_width_mm': round(e, 1),
        'bead_width_inner_mm': round(e1, 1),
        'effective_e_mm': round(effective_e, 1),
        'effective_e_max_mm': round(effective_e_max, 1),
        'bead_mode': bead_mode,
        'e_display': e_display,
        'e1_display': e1_display,
        'bead_height_mm': round(g_nom, 1),
        'g_display': g_display,
        'g_label': '4.2.3. Высота валика усиления (g)',
        'g_face_display': None,
        'labeled_as_g1': False,
        'labeled_as_e1': False,
        'e_label_inner': None,
        'g_min_mm': round(g_min, 1),
        'g_max_mm': round(g_max, 1),
        'g1_display': None,
        'g1_min_mm': None,
        'g1_max_mm': None,
        'sketch_bead_source': None,
        'reinforcement_removed': reinforcement_removed,
        'backing_thickness_mm': round(backing_thickness, 1),
        'has_backing': has_backing,
        'haz_width_mm': haz_width,
        'zone_width_mm': round(zone_width, 1),
        'film_width_min_mm': round(film_width_min, 1),
        'weld_note': weld_note,
        'ref': ref,
        's_mm': round(s_mm, 2),
        's1_mm': round(s1_mm, 2),
        's_eff_mm': round(s_eff_mm, 2),
        'dp_mm': outer_diameter_mm or dn_mm,
        's_equals_s1': s_equals_s1,
        's_equals_s1_actual': s_equals_s1,
        'has_internal_boring': False,
        'wall_thickness_mode': wall_thickness_mode,
        'wall_summary': wall_summary,
        'wall_note': wall_note,
        'wall_resolve_source': 'gost_16037_80',
        'boring_row': None,
        # доп. поля модуля
        'e_nom': e,
        'g_nom': g_nom,
        'b_nom': dims.get('b_nom'),
        'dimensions_approximate': bool(dims.get('approximate')),
        'gost_table': table_ref,
        'joint_code': joint_code,
        'welding_method': welding_method,
        'material_type': material_type,
    }
