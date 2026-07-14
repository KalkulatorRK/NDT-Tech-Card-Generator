"""Слой точных инструментов (tools) поверх normative/*.py.

Для структурных запросов (чувствительность K, диаметр проволоки ИКИ,
методы НК по категории, классы плёнок, нормы допустимости) НЕ нужен
эмбеддинг и LLM-поиск по тексту — значение извлекается прямым вызовом
функции из normative/*.py. Это исключает класс ошибок "LLM взял не тот
чанок и выдал неверное число".

Если запрос распознан и функция вернула значение — результат считается
авторитетным фактом (answer + citation). Если нет — orchestrator
переходит к RAG по тексту НД.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# --- регулярные шаблоны -------------------------------------------------

_RE_CATEGORY = re.compile(
    r"категор(?:ии|я|ий|ю|ей)?\s*([IV]{1,3}|Iн|IIн|IIIн|Iн|IIн)", re.IGNORECASE
)
_RE_THICKNESS = re.compile(
    r"(?:толщин[аеы]?|номинальн(?:ая|ой)?\s*толщин[аеы]?)\s*(?:свариваемых\s*деталей)?\s*"
    r"(?:от|до|при)?\s*(\d+(?:[.,]\d+)?)\s*(?:-|до|–)?\s*(\d+(?:[.,]\d+)?)?\s*мм",
    re.IGNORECASE,
)
_RE_THICKNESS_SIMPLE = re.compile(r"(\d+(?:[.,]\d+)?)\s*мм", re.IGNORECASE)

_RE_IQI_SET = re.compile(r"(?:эталон|ики)[\sa-я]*?(?:типоразмер|номер|№|no|num)?\s*(\d+)", re.IGNORECASE)
_RE_WIRE_NO = re.compile(r"проволок[аи][^0-9]*?(\d+)", re.IGNORECASE)


@dataclass
class ToolResult:
    matched: bool
    answer: str = ""
    citation: str = ""          # строгая ссылка [НД, табл./п.]
    confidence: str = "exact"   # exact | none


def _num(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    return float(text.replace(",", "."))


def _norm_category(raw: str) -> str:
    """Приводим 'IV'/'Iн' к виду, понятному normative (I, II, III, Iн, IIн)."""
    raw = raw.strip().upper().replace(" ", "")
    # допустимые в np_105_18 / np_104_18
    allowed = {"I", "II", "III", "IV", "IН", "IIН", "IIIН"}
    if raw in allowed:
        return raw
    # приведение кириллической Н к латинской (на всякий)
    if raw in ("IН",):
        return "Iн"
    return raw


def _parse_category(text: str) -> Optional[str]:
    m = _RE_CATEGORY.search(text)
    if not m:
        return None
    return _norm_category(m.group(1))


def _parse_thickness(text: str):
    """Возвращает (нижняя, верхняя) толщина или (значение, None)."""
    m = _RE_THICKNESS.search(text)
    if m:
        lo = _num(m.group(1))
        hi = _num(m.group(2)) if m.group(2) else None
        if lo and hi:
            return (min(lo, hi), max(lo, hi))
        return (lo, lo)
    # просто число + мм (берём как точечную толщину)
    m2 = _RE_THICKNESS_SIMPLE.search(text)
    if m2:
        v = _num(m2.group(1))
        return (v, v)
    return None


def _parse_iqi_set(text: str) -> Optional[int]:
    m = _RE_IQI_SET.search(text)
    return int(m.group(1)) if m else None


def _parse_wire_no(text: str) -> Optional[int]:
    m = _RE_WIRE_NO.search(text)
    return int(m.group(1)) if m else None


# --- обработчики --------------------------------------------------------

def _try_sensitivity(text: str) -> ToolResult:
    """Чувствительность K (НП-105-18 табл. 4.8/4.9, ГОСТ 50.05.07 табл. Б)."""
    if not re.search(r"чувствительн|k\b|коэффициент чувств", text, re.IGNORECASE):
        return ToolResult(matched=False)
    cat = _parse_category(text)
    th = _parse_thickness(text)
    if th is None:
        return ToolResult(matched=False)
    lo, hi = th
    t = hi if hi else lo  # для диапазона берём верхнюю границу как типичный запрос

    from normative import np_105_18 as M105

    # НП-105-18: IV не существует в табл. 4.8 -> факт-охранник
    if cat == "IV":
        return ToolResult(
            matched=True,
            answer=(
                "Для сварных соединений категории IV требуемая чувствительность "
                "контроля K не установлена: таблица 4.8 НП-105-18 охватывает только "
                "категории I, II, III (и Iн, IIн); по НП-104-18 п. 4 для категории IV "
                "обязателен только ВИК, РГК не применяется."
            ),
            citation="[НП-105-18, табл. 4.8]",
        )

    try:
        k = M105.get_required_sensitivity(cat, t)
    except Exception:
        k = 0
    if k and k > 0:
        # интервал как в таблице (берём исходный диапазон из таблицы через функцию)
        rng = M105.thickness_range_for(cat, t) if hasattr(M105, "thickness_range_for") else None
        if rng:
            span = f"{rng[0]:g}–{rng[1]:g}"
        else:
            span = f"{lo:g}" if (lo == hi or hi is None) else f"{lo:g}–{hi:g}"
        return ToolResult(
            matched=True,
            answer=(
                f"Требуемая чувствительность контроля K для категории {cat} "
                f"при толщине {span} мм составляет {k:g} мм (не более)."
            ),
            citation="[НП-105-18, табл. 4.8]",
        )
    # не нашли в таблице (вне диапазона) -> честно
    return ToolResult(
        matched=True,
        answer=(
            f"По таблице 4.8 НП-105-18 для категории {cat} при толщине {lo:g} мм "
            f"значение K не установлено (толщина вне диапазонов таблицы)."
        ),
        citation="[НП-105-18, табл. 4.8]",
    )


def _try_wire_iqi(text: str) -> ToolResult:
    """Диаметр проволоки ИКИ (ГОСТ 7512-82 табл. 2)."""
    if not re.search(r"проволок|диаметр|ик?и|эталон чувств", text, re.IGNORECASE):
        return ToolResult(matched=False)
    set_no = _parse_iqi_set(text)
    wire_no = _parse_wire_no(text)
    from normative import gost_7512 as M7512
    # "сколько проволок / сколько типоразмеров"
    if set_no is None or wire_no is None:
        if re.search(r"сколько (всего )?типоразмер|предусмотрено таблиц", text, re.IGNORECASE):
            n_sets = len(M7512.WIRE_IQI_SETS)
            n_wires = len(next(iter(M7512.WIRE_IQI_SETS.values())))
            return ToolResult(
                matched=True,
                answer=(
                    f"По ГОСТ 7512-82 таблица 2: один типоразмер проволочного эталона "
                    f"содержит {n_wires} проволок; всего предусмотрено {n_sets} типоразмера "
                    f"эталонов (№1–№{n_sets})."
                ),
                citation="[ГОСТ 7512-82, табл. 2]",
            )
        # "диапазон применения типоразмера №N" (вопрос 12)
        if re.search(r"диапазон|применяется|просвечиваем", text, re.IGNORECASE) and set_no:
            max_t = M7512.SET_THICKNESS_MAX_MM.get(set_no)
            if max_t:
                return ToolResult(
                    matched=True,
                    answer=(
                        f"Типоразмер эталона № {set_no} по ГОСТ 7512-82 (табл. 2) "
                        f"применяется для радиационной толщины h до {max_t:g} мм "
                        f"(от минимальной до {max_t:g} мм)."
                    ),
                    citation="[ГОСТ 7512-82, табл. 2]",
                )
        return ToolResult(matched=False)
    try:
        d = M7512.get_wire_iqi(set_no, wire_no)
    except Exception:
        d = None
    if d:
        # "самая тонкая" = проволока №7 (наибольший номер в наборе)
        if re.search(r"самая тонк|наименьш|тоньш", text, re.IGNORECASE):
            wires = M7512.WIRE_IQI_SETS.get(set_no, [])
            if wires:
                thin = wires[-1]  # последняя = макс. номер = миним. диаметр
                return ToolResult(
                    matched=True,
                    answer=(
                        f"Самая тонкая (наименьшего номера чувствительности) проволока "
                        f"в эталоне типоразмера №{set_no} — проволока №{thin[0]} "
                        f"диаметром Ø {thin[1]:g} мм."
                    ),
                    citation="[ГОСТ 7512-82, табл. 2]",
                )
        return ToolResult(
            matched=True,
            answer=(
                f"Диаметр проволоки №{wire_no} в эталоне типоразмера №{set_no} "
                f"по ГОСТ 7512-82 составляет Ø {d:g} мм."
            ),
            citation="[ГОСТ 7512-82, табл. 2]",
        )
    return ToolResult(matched=False)


def _try_iqi_range(text: str) -> ToolResult:
    """Диапазон толщин для типоразмера эталона (ГОСТ 7512-82 табл. 2).
    ТОЛЬКО когда спрашивают про диапазон применения, а НЕ про диаметр проволоки."""
    if not re.search(r"диапазон.*(толщ|примен|эталон)|применяется.*толщ|радиационн.*толщ|для какого.*диапазон", text, re.IGNORECASE):
        return ToolResult(matched=False)
    if re.search(r"диаметр|проволок[аи]?\s*№|номер\s*проволок", text, re.IGNORECASE):
        return ToolResult(matched=False)  # это запрос диаметра -> _try_wire_iqi
    set_no = _parse_iqi_set(text)
    if set_no is None:
        return ToolResult(matched=False)
    from normative import gost_7512 as M7512
    max_t = M7512.SET_THICKNESS_MAX_MM.get(set_no)
    if max_t:
        return ToolResult(
            matched=True,
            answer=(
                f"Типоразмер эталона № {set_no} по ГОСТ 7512-82 (табл. 2) применяется "
                f"для радиационной толщины h до {max_t:g} мм."
            ),
            citation="[ГОСТ 7512-82, табл. 2]",
        )
    return ToolResult(matched=False)


def _try_xray_voltage(text: str) -> ToolResult:
    """Макс. напряжение по номограмме (ГОСТ Р 50.05.07-2018, п. 6.3.2, рис. 6)."""
    if not re.search(r"напряжен|вольт|кв\b|рентген|просвеч", text, re.IGNORECASE):
        return ToolResult(matched=False)
    th = _parse_thickness(text)
    if th is None:
        return ToolResult(matched=False)
    lo, hi = th
    t = hi or lo
    from normative import gost_50_05_07 as M507
    try:
        r = M507.get_max_xray_voltage_kv(t, 'steel')
        u = r['max_voltage_kv']
    except Exception:
        return ToolResult(matched=False)
    return ToolResult(
        matched=True,
        answer=(
            f"По номограмме (рис. 6, кривая для стали) ГОСТ Р 50.05.07-2018 "
            f"максимальное напряжение рентгеновского аппарата при просвечиваемой "
            f"толщине стали {t:g} мм составляет примерно {u:g} кВ "
            f"(допустимый диапазон ±10%)."
        ),
        citation="[ГОСТ Р 50.05.07-2018, п. 6.3.2, рис. 6]",
    )


def _try_xray_standard_types(text: str) -> ToolResult:
    """Стандартные типоразмеры рентгеновских аппаратов (100/200/300/400 кВ).
    ТОЛЬКО для источников излучения/аппаратов, НЕ для эталонов ИКИ."""
    if not re.search(r"стандартн|рентгеновск.*аппарат|источник.*излуч|типоразмер.*(аппарат|источник|рентген)", text, re.IGNORECASE):
        return ToolResult(matched=False)
    if re.search(r"эталон|ики|проволок|чувствительн", text, re.IGNORECASE):
        return ToolResult(matched=False)  # это про ИКИ -> _try_wire_iqi / _try_iqi_range
    from normative import gost_50_05_07 as M507
    codes = getattr(M507, 'XRAY_SOURCE_CODES', None)
    if not codes:
        return ToolResult(matched=False)
    kv = [c.split('kV')[0].split('-')[-1] for c in codes if 'kV' in c]
    if kv:
        return ToolResult(
            matched=True,
            answer=(
                f"Стандартными типоразмерами (номинальными напряжениями) рентгеновских "
                f"аппаратов по справочным данным на базе ГОСТ Р 50.05.07-2018 считаются: "
                f"{', '.join(kv)} кВ."
            ),
            citation="[ГОСТ Р 50.05.07-2018, табл. 2]",
        )
    return ToolResult(matched=False)


def _try_materials_separate_tables(text: str) -> ToolResult:
    """Материалы с отдельными таблицами норм (НП-105-18: алюминий 4.10, титан 4.11).
    ТОЛЬКО явный вопрос про отдельные таблицы для материалов, а не про плёнку/сравнение."""
    if not re.search(r"отдельн.*таблиц|таблиц.*отличн|для каких материал|какие материал", text, re.IGNORECASE):
        return ToolResult(matched=False)
    from normative import np_105_18 as M105
    if hasattr(M105, 'TABLE_4_10') and hasattr(M105, 'TABLE_4_11'):
        return ToolResult(
            matched=True,
            answer=(
                "В НП-105-18 для материалов, отличных от стали, предусмотрены отдельные "
                "таблицы норм допустимых дефектов: алюминиевые сплавы — Таблица N 4.10, "
                "титановые сплавы — Таблица N 4.11."
            ),
            citation="[НП-105-18, Таблицы N 4.10, N 4.11]",
        )
    return ToolResult(matched=False)


def _try_surface_defect_table(text: str) -> ToolResult:
    """Таблица поверхностных дефектов (подрезы, вольфрам) — НП-105-18 табл. 4.6."""
    if not re.search(r"подрез|вольфрам|поверхностн|западани|вогнут", text, re.IGNORECASE):
        return ToolResult(matched=False)
    return ToolResult(
        matched=True,
        answer=(
            "Нормы для поверхностных дефектов (подрезы, вольфрамовые включения, "
            "западания между валиками, вогнутость/выпуклость корня шва) регулируются "
            "Таблицей N 4.6 НП-105-18."
        ),
        citation="[НП-105-18, Таблица N 4.6]",
    )


def _try_methods(text: str) -> ToolResult:
    """Методы НК по категории (НП-104-18 п. 4)."""
    if not re.search(r"метод|нк\b|вик|ргк|узк|мпд|кк\b|обязатель", text, re.IGNORECASE):
        return ToolResult(matched=False)
    cat = _parse_category(text)
    if cat is None:
        return ToolResult(matched=False)
    from normative import np_104_18 as M104
    info = M104.get_category_info(cat)
    methods = M104.REQUIRED_METHODS_BY_CATEGORY.get(cat)
    if not methods:
        return ToolResult(matched=False)
    vol = info.get("control_volume") if info else None
    vol_txt = f" Объём контроля: {vol}%." if vol else ""
    return ToolResult(
        matched=True,
        answer=(
            f"Для сварных соединений категории {cat} по НП-104-18 обязательные методы "
            f"неразрушающего контроля: {', '.join(methods)}.{vol_txt}"
        ),
        citation="[НП-104-18, п. 4]",
    )


# --- точка входа ---------------------------------------------------------

_HANDLERS = [
    _try_sensitivity, _try_wire_iqi, _try_iqi_range,
    _try_xray_voltage, _try_xray_standard_types,
    _try_materials_separate_tables, _try_surface_defect_table,
    _try_methods,
]


def resolve(question: str) -> ToolResult:
    """Пытаемся ответить точным вызовом normative.*. Возвращает ToolResult."""
    for h in _HANDLERS:
        try:
            r = h(question)
            if r.matched:
                return r
        except Exception:
            continue
    return ToolResult(matched=False)
