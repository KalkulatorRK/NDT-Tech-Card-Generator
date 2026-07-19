"""
СНиП 3.05.05-84 «Технологическое оборудование и технологические трубопроводы».

Нормативный документ для строительства (не АЭУ). Оценка качества сварных
соединений стальных трубопроводов при радиографическом контроле — в баллах
(прил. 4), с порогами браковки по категории / давлению (п. 4.12).

Модуль содержит:
- категории трубопроводов и объём РК/УЗК (п. 4.11);
- классы чувствительности по ГОСТ 7512-82 (п. 4.13);
- таблицу баллов прил. 4 (включения/поры, скопления);
- пороги браковки и логику доработки / удвоения объёма (п. 4.12);
- требования п. 4.10 (предшествующий контроль, подрезы).

Источник: текст СНиП 3.05.05-84 (в т.ч. прил. 4, п. 4.10–4.13).
"""

from __future__ import annotations

from typing import Optional

DOCUMENT_CODE = 'СНиП 3.05.05-84'
DOCUMENT_FULL_NAME = (
    'СНиП 3.05.05-84 «Технологическое оборудование и технологические трубопроводы»'
)

# Давление, при котором режим как для «высокого» (п. 4.10–4.13)
HIGH_PRESSURE_MPA = 10.0  # Py > 10 МПа (100 кгс/см²)

# ------------------------------------------------------------------
# Категории трубопроводов (строительные)
# ------------------------------------------------------------------
# Код HIGH — Py свыше 10 МПа (выделенный режим)
PIPELINE_CATEGORIES = {
    'HIGH': {
        'code': 'HIGH',
        'name': 'Py свыше 10 МПа (100 кгс/см²)',
        'control_volume_pct': 100,
        'reject_score_min': 2,
        'sensitivity_class_gost7512': 2,
        'undercut_allowed_mm': 0.0,  # подрезы не допускаются
        'pre_rt_surface_ndt': True,  # МПД/КК до РК/УЗК
        'score_4_no_repair_doubles': None,
        'score_5_no_repair_doubles': None,
    },
    'I': {
        'code': 'I',
        'name': 'Категория I',
        'control_volume_pct': 20,
        'reject_score_min': 3,
        'sensitivity_class_gost7512': 2,
        'undercut_allowed_mm': 0.5,
        'pre_rt_surface_ndt': False,
        'score_4_no_repair_doubles': None,
        'score_5_no_repair_doubles': None,
    },
    'II': {
        'code': 'II',
        'name': 'Категория II',
        'control_volume_pct': 10,
        'reject_score_min': 3,
        'sensitivity_class_gost7512': 2,
        'undercut_allowed_mm': 0.5,
        'pre_rt_surface_ndt': False,
        'score_4_no_repair_doubles': None,
        'score_5_no_repair_doubles': None,
    },
    'III': {
        'code': 'III',
        'name': 'Категория III',
        'control_volume_pct': 2,
        'reject_score_min': 5,
        'sensitivity_class_gost7512': 3,
        'undercut_allowed_mm': 0.5,
        'pre_rt_surface_ndt': False,
        # балл 4 — не ремонтируют, удваивают объём у сварщика
        'score_4_no_repair_doubles': True,
        'score_5_no_repair_doubles': None,
    },
    'IV': {
        'code': 'IV',
        'name': 'Категория IV',
        'control_volume_pct': 1,
        'reject_score_min': 6,
        'sensitivity_class_gost7512': 3,
        'undercut_allowed_mm': 0.5,
        'pre_rt_surface_ndt': False,
        'score_4_no_repair_doubles': None,
        # балл 5 — не ремонтируют, удваивают объём
        'score_5_no_repair_doubles': True,
    },
}

# Относительная чувствительность по классу ГОСТ 7512-82 (доля от S),
# типичная инженерная интерпретация классов 2 и 3 для СНиП.
SENSITIVITY_CLASS_FRACTION = {
    2: 0.025,  # класс 2 ≈ 2,5 % толщины
    3: 0.040,  # класс 3 ≈ 4 % толщины
}

# Включения ≤ 0,2 мм не учитывают (прим. 1 к прил. 4), если не образуют скопление/сетку
PORE_IGNORE_LENGTH_MM = 0.2

CONTROL_VOLUME_OPTIONS_SNIP = (100, 20, 10, 2, 1)

# ------------------------------------------------------------------
# Приложение 4 — оценка в баллах (включения/поры и скопления)
# Запись: (t_min, t_max, width_mm, length_mm, cluster_mm, sum_100_mm)
# t_max = None → «св. t_min»
# ------------------------------------------------------------------
_SCORE_1_ROWS = [
    (0, 3, 0.5, 1.0, 2.0, 3.0),
    (3, 5, 0.6, 1.2, 2.5, 4.0),
    (5, 8, 0.8, 1.5, 3.0, 5.0),
    (8, 11, 1.0, 2.0, 4.0, 6.0),
    (11, 14, 1.2, 2.5, 5.0, 8.0),
    (14, 20, 1.5, 3.0, 6.0, 10.0),
    (20, 26, 2.0, 4.0, 8.0, 12.0),
    (26, 34, 2.5, 5.0, 10.0, 15.0),
    (34, None, 3.0, 6.0, 10.0, 20.0),
]

_SCORE_2_ROWS = [
    (0, 3, 0.6, 2.0, 3.0, 6.0),
    (3, 5, 0.8, 2.5, 4.0, 8.0),
    (5, 8, 1.0, 3.0, 5.0, 10.0),
    (8, 11, 1.2, 3.5, 6.0, 12.0),
    (11, 14, 1.5, 5.0, 8.0, 15.0),
    (14, 20, 2.0, 6.0, 10.0, 20.0),
    (20, 26, 2.5, 8.0, 12.0, 25.0),
    (26, 34, 2.5, 8.0, 12.0, 30.0),
    (34, 45, 3.0, 10.0, 15.0, 30.0),
    (45, None, 3.5, 12.0, 15.0, 40.0),
]

_SCORE_3_ROWS = [
    (0, 3, 0.8, 3.0, 5.0, 8.0),
    (3, 5, 1.0, 4.0, 6.0, 10.0),
    (5, 8, 1.2, 5.0, 7.0, 12.0),
    (8, 11, 1.5, 6.0, 9.0, 15.0),
    (11, 14, 2.0, 8.0, 12.0, 20.0),
    (14, 20, 2.5, 10.0, 15.0, 25.0),
    (20, 26, 3.0, 12.0, 20.0, 30.0),
    (26, 34, 3.5, 12.0, 20.0, 35.0),
    (34, 45, 4.0, 15.0, 25.0, 40.0),
    (45, None, 4.5, 15.0, 30.0, 45.0),
]

SCORE_TABLES = {
    1: _SCORE_1_ROWS,
    2: _SCORE_2_ROWS,
    3: _SCORE_3_ROWS,
}


def normalize_pipeline_category(raw: str) -> str:
    """Приводит категорию к ключу PIPELINE_CATEGORIES."""
    if not raw:
        return 'III'
    s = str(raw).strip().upper().replace(' ', '')
    aliases = {
        'HIGH': 'HIGH',
        'PY>10': 'HIGH',
        'P>10': 'HIGH',
        'СВ.10МПА': 'HIGH',
        'I': 'I',
        'II': 'II',
        'III': 'III',
        'IV': 'IV',
        '1': 'I',
        '2': 'II',
        '3': 'III',
        '4': 'IV',
    }
    return aliases.get(s, s if s in PIPELINE_CATEGORIES else 'III')


def get_pipeline_category_info(category: str) -> dict:
    return PIPELINE_CATEGORIES[normalize_pipeline_category(category)]


def get_pipeline_category_choices() -> list[tuple[str, str]]:
    """Выбор категории трубопровода для формы техкарты."""
    order = ('HIGH', 'I', 'II', 'III', 'IV')
    return [(c, PIPELINE_CATEGORIES[c]['name']) for c in order]


def get_weld_category_choices(material_type: str = 'steel') -> list[tuple[str, str]]:
    """Синоним для совместимости с API НП-105 (материал не влияет)."""
    return get_pipeline_category_choices()


def get_default_control_volume_pct(category: str) -> int:
    """Объём контроля РК/УЗК по п. 4.11, %."""
    return int(get_pipeline_category_info(category)['control_volume_pct'])


def normalize_control_volume_pct(value) -> int:
    """Допустимые объёмы для СНиП (п. 4.11) + 100 %."""
    try:
        pct = int(float(value))
    except (TypeError, ValueError):
        return 100
    if pct in CONTROL_VOLUME_OPTIONS_SNIP:
        return pct
    # ближайший допустимый не выше заданного
    allowed = sorted(CONTROL_VOLUME_OPTIONS_SNIP, reverse=True)
    for a in allowed:
        if pct >= a:
            return a
    return 1


def get_sensitivity_class(category: str) -> int:
    """Класс чувствительности по ГОСТ 7512-82 (п. 4.13 СНиП)."""
    return int(get_pipeline_category_info(category)['sensitivity_class_gost7512'])


def get_required_sensitivity_mm(
    thickness_mm: float,
    category: str,
    material_type: str = 'steel',
) -> float:
    """
    Требуемая абсолютная чувствительность K, мм.

    По п. 4.13 класс задаётся ГОСТ 7512-82; абсолютное K принимаем как
    долю от радиационной / номинальной толщины для класса 2 или 3.
    """
    t = max(float(thickness_mm or 0), 0.1)
    cls = get_sensitivity_class(category)
    frac = SENSITIVITY_CLASS_FRACTION.get(cls, 0.04)
    k = t * frac
    # округление до 0,05 мм вверх (практика подбора проволоки)
    import math
    k = math.ceil(k * 20) / 20
    return max(0.1, round(k, 2))


def get_reject_score_min(category: str) -> int:
    """Минимальный суммарный балл, при котором стык бракуют (п. 4.12)."""
    return int(get_pipeline_category_info(category)['reject_score_min'])


def _row_for_thickness(rows: list, thickness_mm: float) -> Optional[tuple]:
    """Подбор строки: «до T» → t≤T; «св. A до B» → A < t ≤ B; «св. A» → t > A."""
    t = float(thickness_mm or 0)
    if t <= 0:
        return rows[0] if rows else None
    for tmin, tmax, w, L, cl, s100 in rows:
        if tmin == 0 and tmax is not None:
            if t <= tmax:
                return (tmin, tmax, w, L, cl, s100)
        elif tmax is None:
            if t > tmin:
                return (tmin, tmax, w, L, cl, s100)
        else:
            if t > tmin and t <= tmax:
                return (tmin, tmax, w, L, cl, s100)
    return rows[-1] if rows else None


def lookup_score_limits(score: int, thickness_mm: float) -> Optional[dict]:
    """Пределы прил. 4 для заданного балла и толщины стенки."""
    rows = SCORE_TABLES.get(int(score))
    if not rows:
        return None
    row = _row_for_thickness(rows, thickness_mm)
    if not row:
        return None
    tmin, tmax, w, L, cl, s100 = row
    return {
        'score': int(score),
        't_min': tmin,
        't_max': tmax,
        'width_mm': w,
        'length_mm': L,
        'cluster_mm': cl,
        'sum_100_mm': s100,
        'standard': f'{DOCUMENT_CODE}, прил. 4',
    }


def _exceeds(limits: dict, width=None, length=None, cluster=None, sum_100=None) -> bool:
    if width is not None and width > limits['width_mm'] + 1e-9:
        return True
    if length is not None and length > limits['length_mm'] + 1e-9:
        return True
    if cluster is not None and cluster > limits['cluster_mm'] + 1e-9:
        return True
    if sum_100 is not None and sum_100 > limits['sum_100_mm'] + 1e-9:
        return True
    return False


def score_inclusions(
    thickness_mm: float,
    width_mm: float = 0,
    length_mm: float = 0,
    cluster_mm: float = 0,
    sum_100_mm: float = 0,
) -> dict:
    """
    Оценка включений/пор в баллах по прил. 4.

    Балл — наихудший (наибольший номер 1→2→3→6), для которого размеры
    ещё укладываются в пределы; если превышают балл 3 — балл 6.
    """
    # прим. 1: ≤0,2 мм не учитывают (одиночные)
    w = float(width_mm or 0)
    L = float(length_mm or 0)
    if L <= PORE_IGNORE_LENGTH_MM and w <= PORE_IGNORE_LENGTH_MM and not cluster_mm:
        return {
            'score': 1,
            'verdict': 'не учитывается (≤0,2 мм)',
            'standard': f'{DOCUMENT_CODE}, прил. 4, прим. 1',
        }

    for score in (1, 2, 3):
        lim = lookup_score_limits(score, thickness_mm)
        if lim and not _exceeds(lim, w, L, cluster_mm, sum_100_mm):
            return {
                'score': score,
                'limits': lim,
                'verdict': f'балл {score}',
                'standard': f'{DOCUMENT_CODE}, прил. 4',
            }

    lim3 = lookup_score_limits(3, thickness_mm)
    return {
        'score': 6,
        'limits': lim3,
        'verdict': 'балл 6 (превышение норм балла 3)',
        'standard': f'{DOCUMENT_CODE}, прил. 4',
    }


def evaluate_joint_score(
    category: str,
    total_score: int,
) -> dict:
    """
    Браковка / ремонт / удвоение объёма по п. 4.12.

    :param total_score: суммарный балл стыка (по прил. 4)
    :return: dict с is_reject, repair, double_volume, notes
    """
    info = get_pipeline_category_info(category)
    reject_min = info['reject_score_min']
    score = int(total_score)
    cat = info['code']

    result = {
        'category': cat,
        'total_score': score,
        'reject_score_min': reject_min,
        'is_reject': score >= reject_min,
        'repair_required': False,
        'double_volume': False,
        'remove_welder_if_100pct_fail': True,
        'notes': [],
        'standard': f'{DOCUMENT_CODE}, п. 4.12',
    }

    if score >= reject_min:
        result['repair_required'] = True
        result['double_volume'] = True
        result['notes'].append(
            f'Стык бракуется при балле ≥ {reject_min} для категории {info["name"]}; '
            f'подлежит исправлению, объём контроля у сварщика удваивается.'
        )
        return result

    # Особые случаи III / IV: балл ниже порога брака, но с удвоением без ремонта
    if cat == 'III' and score == 4:
        result['repair_required'] = False
        result['double_volume'] = True
        result['notes'].append(
            'Категория III, балл 4: стык не исправляют, объём контроля у сварщика '
            'удваивают (п. 4.12).'
        )
    elif cat == 'IV' and score == 5:
        result['repair_required'] = False
        result['double_volume'] = True
        result['notes'].append(
            'Категория IV, балл 5: стык не исправляют, объём контроля у сварщика '
            'удваивают (п. 4.12).'
        )
    else:
        result['notes'].append('Стык соответствует требованиям п. 4.12.')

    return result


def surface_ndt_before_rt_required(category: str) -> bool:
    """Нужны ли МПД/КК до РК/УЗК (п. 4.10) — зона шва + 20 мм."""
    return bool(get_pipeline_category_info(category)['pre_rt_surface_ndt'])


def undercut_limit_mm(category: str) -> float:
    """Допустимая глубина подреза, мм (п. 4.10). 0 = не допускаются."""
    return float(get_pipeline_category_info(category)['undercut_allowed_mm'])


def build_acceptance_criteria_docx_data(
    material_type: str,
    category: str,
    thickness_mm: float,
) -> dict:
    """
    Данные для п. 10.2 техкарты: нормы прил. 4 для толщины стенки
    (баллы 1–3) и порог браковки по категории.
    """
    cat = normalize_pipeline_category(category)
    info = get_pipeline_category_info(cat)
    t = float(thickness_mm or 0)
    headers = [
        'Балл',
        'Ширина (диам.) вкл., мм',
        'Длина вкл., мм',
        'Скопление, мм',
        'Σ длина на 100 мм, мм',
    ]
    row_values = []
    for score in (1, 2, 3):
        lim = lookup_score_limits(score, t)
        if not lim:
            continue
        row_values.append([
            str(score),
            _fmt(lim['width_mm']),
            _fmt(lim['length_mm']),
            _fmt(lim['cluster_mm']),
            _fmt(lim['sum_100_mm']),
        ])

    undercut = info['undercut_allowed_mm']
    undercut_txt = (
        'не допускаются'
        if undercut <= 0
        else f'не более {_fmt(undercut)} мм'
    )
    sens_cls = info['sensitivity_class_gost7512']

    intro = (
        f'10.2. Оценка качества сварных соединений стальных трубопроводов '
        f'по {DOCUMENT_CODE}, прил. 4 (в баллах) и п. 4.12. '
        f'Категория / режим: {info["name"]}. '
        f'Толщина стенки {_fmt(t)} мм. '
        f'Стык бракуется при суммарном балле ≥ {info["reject_score_min"]}. '
        f'Чувствительность РК — класс {sens_cls} по ГОСТ 7512-82 (п. 4.13). '
        f'Подрезы: {undercut_txt} (п. 4.10). '
        f'Трещины, прожоги, незаваренные кратеры, грубая чешуйчатость — не допускаются.'
    )
    if info['pre_rt_surface_ndt']:
        intro += (
            ' До РК/УЗК — магнитопорошковый или капиллярный контроль шва '
            'и зоны +20 мм с каждой стороны (п. 4.10).'
        )

    return {
        'table_ref': 'прил. 4',
        'intro': intro,
        'headers': headers,
        'row_values': row_values,
        'not_allowed': False,
        'score_system': True,
        'reject_score_min': info['reject_score_min'],
        'sensitivity_class': sens_cls,
        'control_volume_pct': info['control_volume_pct'],
        'standard': DOCUMENT_CODE,
    }


def build_quality_criteria_summary(category: str, thickness_mm: float) -> str:
    """Краткое резюме для params / PDF."""
    info = get_pipeline_category_info(category)
    k = get_required_sensitivity_mm(thickness_mm, category)
    return (
        f'По {DOCUMENT_CODE}: {info["name"]}; объём РК/УЗК '
        f'{info["control_volume_pct"]} % (п. 4.11); '
        f'чувствительность — класс {info["sensitivity_class_gost7512"]} '
        f'ГОСТ 7512-82 (K ≤ {_fmt(k)} мм при S={_fmt(thickness_mm)} мм); '
        f'браковка при балле ≥ {info["reject_score_min"]} (п. 4.12); '
        f'нормы пор/включений — прил. 4 (баллы 1–3, свыше — балл 6).'
    )


def _fmt(x) -> str:
    if x is None:
        return '—'
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    s = f'{float(x):g}'.replace('.', ',')
    return s


def is_snip_quality_norm(code: str | None) -> bool:
    """Проверка, что выбран СНиП 3.05.05-84."""
    c = (code or '').upper().replace(' ', '')
    return '3.05.05' in c or c.startswith('СНИП3.05.05') or 'SNIP3.05.05' in c
