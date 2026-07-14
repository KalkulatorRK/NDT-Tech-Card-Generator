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
    if set_no is None or wire_no is None:
        # запрос про "сколько проволок / сколько типоразмеров"
        if re.search(r"сколько (всего )?типоразмер|предусмотрено таблиц", text, re.IGNORECASE):
            from normative import gost_7512 as M7512
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
        return ToolResult(matched=False)
    from normative import gost_7512 as M7512
    try:
        d = M7512.get_wire_iqi(set_no, wire_no)
    except Exception:
        d = None
    if d:
        return ToolResult(
            matched=True,
            answer=(
                f"Диаметр проволоки №{wire_no} в эталоне типоразмера №{set_no} "
                f"по ГОСТ 7512-82 составляет Ø {d:g} мм."
            ),
            citation="[ГОСТ 7512-82, табл. 2]",
        )
    return ToolResult(matched=False)


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

_HANDLERS = [_try_sensitivity, _try_wire_iqi, _try_methods]


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
