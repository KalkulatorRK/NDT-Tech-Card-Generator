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

try:
    from normative import gost_50_05_07 as M507
    from normative import gost_50_05_09 as M509
    from normative import gost_7512 as M7512
    from normative import np_105_18 as M105
    from normative import np_104_18 as M104
except Exception:
    M507 = M509 = M7512 = M105 = M104 = None

# --- регулярные шаблоны -------------------------------------------------

_RE_CATEGORY = re.compile(
    r"кат(?:егори[яиюей]?|егор|\.)?\s*([IV]{1,3}н?)\b", re.IGNORECASE
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


def fmt(x) -> str:
    """Форматирует число с десятичной ЗАПЯТОЙ (по ГОСТ-стилю, ru-RU)."""
    if x is None:
        return "—"
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    s = f"{x:g}"
    if "." in s:
        s = s.replace(".", ",")
    return s


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
    # не перехватывать геометрические вопросы (приложение Г: f, схемы, экспозиции)
    if re.search(r"схем|3[а-г]|приложен|экспозиц|источник.*излуч|расстоян.*источник", text, re.IGNORECASE):
        return ToolResult(matched=False)
    cat = _parse_category(text)
    th = _parse_thickness(text)
    if th is None:
        return ToolResult(matched=False)
    lo, hi = th
    t = hi if hi else lo  # для диапазона берём верхнюю границу как типичный запрос

    from normative import np_105_18 as M105

    # НП-105-18: проверка существования категории
    valid_categories = {'I', 'II', 'III', 'Iн', 'IIн', 'IIIн'}
    if cat and cat not in valid_categories:
        return ToolResult(
            matched=True,
            answer=(
                f"Категория сварного соединения «{cat}» не существует в НП-105-18. "
                f"Таблица 4.8 НП-105-18 содержит нормы только для категорий "
                f"«I, II, III (и Iн, IIн)». Для других категорий (включая IV) "
                f"таблица 4.8 не применяется: для IV обязателен только ВИК по НП-104-18."
            ),
            citation="[НП-105-18, табл. 4.8]",
        )

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
            span = f"{fmt(rng[0])}–{fmt(rng[1])}"
        else:
            span = f"{fmt(lo)}" if (lo == hi or hi is None) else f"{fmt(lo)}–{fmt(hi)}"
        return ToolResult(
            matched=True,
            answer=(
                f"Требуемая чувствительность контроля K для категории {cat} "
                f"при толщине {span} мм составляет {fmt(k)} мм (не более)."
            ),
            citation="[НП-105-18, табл. 4.8]",
        )
    # не нашли в таблице (вне диапазона) -> честно
    return ToolResult(
        matched=True,
        answer=(
            f"По таблице 4.8 НП-105-18 для категории {cat} при толщине {fmt(lo)} мм "
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
        if re.search(r"сколько (всего )?(проволок|типоразмер)|предусмотрено таблиц|количество проволок|число проволок", text, re.IGNORECASE):
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
                        f"применяется для радиационной толщины h до {fmt(max_t)} мм "
                        f"(от минимальной до {fmt(max_t)} мм)."
                    ),
                    citation="[ГОСТ 7512-82, табл. 2]",
                )
        return ToolResult(matched=False)
    wires = M7512.WIRE_IQI_SETS.get(set_no, [])
    d = None
    if 1 <= wire_no <= len(wires):
        d = wires[wire_no - 1][1]
    if d is not None:
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
                        f"диаметром Ø {fmt(thin[1])} мм."
                    ),
                    citation="[ГОСТ 7512-82, табл. 2]",
                )
        return ToolResult(
            matched=True,
            answer=(
                f"Диаметр проволоки №{wire_no} в эталоне типоразмера №{set_no} "
                f"по ГОСТ 7512-82 составляет Ø {fmt(d)} мм."
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
                f"для радиационной толщины h до {fmt(max_t)} мм."
            ),
            citation="[ГОСТ 7512-82, табл. 2]",
        )
    return ToolResult(matched=False)


def _try_xray_voltage(text: str) -> ToolResult:
    """Макс. напряжение по номограмме (ГОСТ Р 50.05.07-2018, п. 6.3.2, рис. 6)."""
    if not re.search(r"напряжен|вольт|кв\b|рентген|просвеч", text, re.IGNORECASE):
        return ToolResult(matched=False)
    # не перехватывать геометрические вопросы (приложение Г: f, схемы, экспозиции)
    if re.search(r"схем[аеы]?\s*3[гд]|приложен.*г|экспозиц|расстоян.*источник|f\b", text, re.IGNORECASE):
        return ToolResult(matched=False)
    th = _parse_thickness(text)
    if th is None:
        return ToolResult(matched=False)
    lo, hi = th
    t = hi or lo
    # определяем материал по тексту
    from normative import gost_50_05_07 as M507
    material = 'steel'
    if re.search(r"алюмин|al\b", text, re.IGNORECASE):
        material = 'aluminum'
    elif re.search(r"титан|titanium", text, re.IGNORECASE):
        material = 'titanium'
    try:
        r = M507.get_max_xray_voltage_kv(t, material)
        u = r['max_voltage_kv']
    except Exception:
        return ToolResult(matched=False)
    curve_label = {'steel': 'стали', 'aluminum': 'алюминиевого сплава', 'titanium': 'титанового сплава'}
    return ToolResult(
        matched=True,
        answer=(
            f"По номограмме (рис. 6, кривая для {curve_label[material]}) ГОСТ Р 50.05.07-2018 "
            f"максимальное напряжение рентгеновского аппарата при просвечиваемой "
            f"толщине {curve_label[material]} {fmt(t)} мм составляет примерно {fmt(u)} кВ "
            f"(допустимый диапазон ±10%)."
        ),
        citation="[ГОСТ Р 50.05.07-2018, п. 6.3.2, рис. 6]",
    )


def _try_xray_standard_types(text: str) -> ToolResult:
    """Стандартные типоразмеры рентгеновских аппаратов (100/200/300/400 кВ).
    ТОЛЬКО для источников излучения/аппаратов, НЕ для эталонов ИКИ и НЕ для геометрии."""
    if not re.search(r"стандартн|рентгеновск.*аппарат|источник.*излуч|типоразмер.*(аппарат|источник|рентген)", text, re.IGNORECASE):
        return ToolResult(matched=False)
    if re.search(r"эталон|\bики\b|проволок|чувствительн", text, re.IGNORECASE):
        return ToolResult(matched=False)  # это про ИКИ -> _try_wire_iqi / _try_iqi_range
    if re.search(r"схем[аеы]?\s*3[гд]|приложен.*г|экспозиц|расстоян.*источник", text, re.IGNORECASE):
        return ToolResult(matched=False)  # это геометрия -> _try_geometry_f
    if re.search(r"напряжен|кв\b|вольт|номограмм|рис\.?\s*6|толщин", text, re.IGNORECASE):
        return ToolResult(matched=False)  # это номограмма -> _try_xray_voltage
    # не перехватывать вопросы про изотопы/радионуклиды (идут в RAG)
    if re.search(r"изотоп|радионуклид|гамма|иттербий|тулий|селен|ирридий|кобальт|se\b|yb\b|tm\b|co\b|ir\b", text, re.IGNORECASE):
        return ToolResult(matched=False)
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
    if not re.search(r"метод|нк\b|вик|ргк|узк|мпд|кк\b|обязатель|объём|процент", text, re.IGNORECASE):
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


def _try_geometry_f(text: str) -> ToolResult:
    """Расчёт расстояния f (источник→шов) и числа экспозиций по приложению Г
    ГОСТ Р 50.05.07-2018 (схемы 3а/3б/3г/3д/4а/4б, табл. Г.1–Г.4)."""
    tl = text.lower()
    # не перехватывать вопросы про ТИПЫ источников (рентген/изотоп) —
    # их берёт _try_xray_standard_types
    if re.search(r"стандартн|рентгеновск.*аппарат|типоразмер.*аппарат|какие источник|тип.*источник", text, re.IGNORECASE):
        return ToolResult(matched=False)
    # не перехватывать вопросы про выбор плёнки/экранов (это не геометрия f)
    if re.search(r"плён|экран|класс.*плён|сенсибил|радиографическ\w* плён", text, re.IGNORECASE):
        return ToolResult(matched=False)
    # не перехватывать вопросы про ВРЕМЯ экспозиции / ток трубки (это не f)
    if re.search(r"время\s+экспозиц|экспозиц\w*\s+(время|ток|режим)|ток\s+(трубки|аппарата)|режим\s+(трубки|аппарата|рентген)|минут\w*\s+экспоз", text, re.IGNORECASE):
        return ToolResult(matched=False)
    if not ('f' in tl or 'приложен' in tl or 'схем' in tl
            or ('источник' in tl and 'расстоян' in tl) or 'расстоян' in tl):
        return ToolResult(matched=False)
    if M507 is None:
        return ToolResult(matched=False)
    # определяем схему
    scheme = None
    for s in ['3г', '3д', '3а', '3б', '4а', '4б', '4в', '4г']:
        if s in tl:
            scheme = s
            break
    # извлекаем параметры
    focal = k_sens = D = d = Rt = None
    m = re.search(r"фокус\w*\s*(?:пятн\w*)?\s*[=:\s]*(\d+[.,]?\d*)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"пятн\w*\s*[=:\s]*(\d+[.,]?\d*)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"[φΦ]\s*[=:]\s*(\d+[.,]?\d*)", text, re.IGNORECASE)
    if m:
        focal = float(m.group(1).replace(',', '.'))
    m = re.search(r"\bk\s*[=:]\s*(\d+[.,]?\d*)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"чувствительн\w*\s*(\d+[.,]?\d*)", text, re.IGNORECASE)
    if m:
        k_sens = float(m.group(1).replace(',', '.'))
    m = re.search(r"наружн\w*\s*диаметр\w*\s*[=:\s]*(\d+[.,]?\d*)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"наружн\w*\s*(\d+[.,]?\d*)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"D\s*[=:]\s*(\d+[.,]?\d*)", text)  # заглавная D (без IGNORECASE)
    if m:
        D = float(m.group(1).replace(',', '.'))
    m = re.search(r"внутренн\w*\s*диаметр\w*\s*[=:\s]*(\d+[.,]?\d*)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"внутренн\w*\s*(\d+[.,]?\d*)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"(?<!D)\bd\s*[=:]\s*(\d+[.,]?\d*)", text)  # строчная d, не после D
    if m:
        d = float(m.group(1).replace(',', '.'))
    m = re.search(r"r_t\s*[=:]\s*(\d+[.,]?\d*)", text, re.IGNORECASE)
    if m:
        Rt = float(m.group(1).replace(',', '.'))
    # общая справка, если нет схемы и параметров
    if scheme is None and (focal is None or k_sens is None):
        return ToolResult(
            matched=True,
            answer=(
                "Для расчёта расстояния f (от источника излучения до контролируемого "
                "сварного соединения) и числа экспозиций используйте приложение Г "
                "ГОСТ Р 50.05.07-2018. Основные соотношения (п. Г.1): f ≥ c·h; "
                "L ≤ 0,8·f, где c = 2Φ/K при Φ/K ≥ 2, иначе c = 4 (Φ — размер "
                "фокусного пятна, K — требуемая чувствительность, h — радиационная "
                "толщина). Для конкретной схемы (рис. 3а/3б/3г/3д/4а/4б) расстояние "
                "l определяется по таблице Г.1, а число экспозиций N — по таблицам "
                "Г.2–Г.4 в зависимости от отношения f/D."
            ),
            citation="[ГОСТ Р 50.05.07-2018, приложение Г, п. Г.1, табл. Г.1–Г.4]",
        )
    if scheme is None:
        scheme = '3г'  # по умолчанию (частый запрос про трубы)
    if focal is None or k_sens is None:
        # Формулы для каждой схемы (таблица Г.1)
        formulas = {
            '3а': 'f ≥ 0,7·c·(D − d)',
            '3б': 'f ≥ 0,5·c·D',
            '3г': 'f ≥ 0,5·[1,5·c·(D − d) − D]',
            '3д': 'f ≥ 0,5·[c·(1,4·D − d) − D]',
            '4а': 'f ≥ 0,7·c·(2·Rₜ + d)',
            '4в': 'f ≥ 0,5·[1,5·c·(D* − d) − D*], где D* = d + 2·Rₜ',
            '4г': 'd/D* ≥ 0,8 и Φ ≤ K·d / (2·Rₜ)',
        }
        default_txt = 'Для расчёта расстояния f по схеме {s} используется формула (табл. Г.1):\n' \
                      '{formula}\n\n' \
                      'где c = 2Φ/K при Φ/K ≥ 2, иначе c = 4;\n' \
                      'Φ — размер фокусного пятна (мм);\n' \
                      'K — требуемая чувствительность (мм);\n' \
                      'D, d — наружный и внутренний диаметры (мм);\n' \
                      'Rₜ — расчётная высота углового шва (мм).\n\n' \
                      'Ширина контролируемого за одну экспозицию участка L — по (Г.2):\n' \
                      'L ≤ 0,8·f\n\n' \
                      'Число экспозиций N — по таблицам Г.2–Г.4 в зависимости от f/D.'
        if scheme in formulas:
            answer = default_txt.format(s=scheme, formula=formulas[scheme])
        else:
            answer = default_txt.format(
                s=scheme,
                formula='определяется по таблице Г.1 для схемы ' + scheme)
        return ToolResult(
            matched=True,
            answer=answer,
            citation="[ГОСТ Р 50.05.07-2018, приложение Г, табл. Г.1, Г.2]",
        )
    try:
        res = M507.calc_source_distance_f(
            scheme, focal_spot_mm=focal, sensitivity_K_mm=k_sens,
            D=D, d=d, Rt=Rt or 0.0)
    except Exception as _exc:
        import traceback as _tb; _tb.print_exc()
        return ToolResult(matched=False)
    if 'error' in res:
        return ToolResult(matched=True, answer=res['error'], citation="[ГОСТ Р 50.05.07-2018, приложение Г]")
    ans = (
        f"По приложению Г ГОСТ Р 50.05.07-2018 для схемы {scheme}: "
        f"расстояние f (источник → сварное соединение) должно быть не менее "
        f"{fmt(res['f_mm_min'])} мм (коэффициент c = {fmt(res['c'])}). "
        f"После выбора f определите отношение f/D и по таблицам Г.2–Г.4 найдите "
        f"число экспозиций N для 100%-ного контроля."
    )
    return ToolResult(
        matched=True,
        answer=ans,
        citation="[ГОСТ Р 50.05.07-2018, приложение Г, табл. Г.1, п. Г.3]",
    )


def _try_iqi_types(text: str) -> ToolResult:
    """Типы эталонов ИКИ по ГОСТ 7512-82."""
    if not re.search(r"(тип|вид|как[ие]?|для чего|для чег|назначени|назнач|разниц|отлич|сравн|чем отлич|в чём)\s*.{0,10}(эталон|ик?и)|какие бывают эталон|как[ие]?.*ики|как[аяя]?.*эталон.*использ|виды.*ики|ики.*тип", text, re.IGNORECASE):
        return ToolResult(matched=False)
    # сравнение канавочного и проволочного
    if re.search(r"(канавочн.*проволочн|проволочн.*канавочн|разниц|отлич|сравн)", text, re.IGNORECASE):
        return ToolResult(
            matched=True,
            answer=(
                "Разница между типами эталонов:\n"
                "— Канавочный эталон: пластина с канавками разной глубины; "
                "оценивает КОНТРАСТНУЮ чувствительность по глубине видимой канавки. "
                "Номера: №1–№20 (глубина = номер/100 мм). [ГОСТ 7512-82, п. 2.6, 3.9]\n"
                "— Проволочный эталон: набор проволок разного диаметра; "
                "оценивает КОЛИЧЕСТВЕННУЮ чувствительность по видимости проволок. "
                "Номера: №1–№4 (типоразмеры). [ГОСТ Р 50.05.07-2018, п. 6.1.16]\n"
                "Оба применяются для оценки чувствительности радиографического контроля."
            ),
            citation="[ГОСТ 7512-82, п. 2.6, 3.9; ГОСТ Р 50.05.07-2018, п. 6.1.16]",
        )
    return ToolResult(
        matched=True,
        answer=(
            "По ГОСТ 7512-82 (п. 2.6–2.14) применяются следующие типы эталонов "
            "для определения чувствительности радиографического контроля:\n"
            "— проволочные эталоны (набор проволок разного диаметра);\n"
            "— канавочные эталоны (пластины с канавками разной глубины);\n"
            "— пластинчатые (с отверстиями ступенчатого сверления);\n"
            "— дуплекс-эталоны (для определения геометрической нерезкости).\n"
            "По ГОСТ Р 50.05.07-2018 (п. 5.3) дополнительно применяются "
            "дуплекс-эталоны для кат. I."
        ),
        citation="[ГОСТ 7512-82, п. 2.6–2.14; ГОСТ Р 50.05.07-2018, п. 5.3]",
    )


def _try_iqi_number(text: str) -> ToolResult:
    """Номер ИКИ (канавочный или проволочный эталон)."""
    m = re.search(r"(?:ик?и|эталон|канавочн|проволочн)\s*(?:номер|№|ном[её]р)?\s*(\d{1,3})", text, re.IGNORECASE)
    if not m:
        return ToolResult(matched=False)
    num = int(m.group(1))
    # Канавочные эталоны: №1–№20 (глубина канавки = номер/100 мм)
    if 1 <= num <= 20:
        return ToolResult(
            matched=True,
            answer=(
                f"Канавочный эталон №{num} по ГОСТ 7512-82 (п. 2.6) — "
                f"пластина с канавкой глубиной {num/100:.2f} мм. "
                "Используется для оценки контрастной чувствительности "
                "радиографического контроля."
            ),
            citation="[ГОСТ 7512-82, п. 2.6]",
        )
    return ToolResult(matched=False)


def _try_marking_decode(text: str) -> ToolResult:
    """Расшифровка условной записи дефекта (ГОСТ 7512-82 п. 2.10-2.13)."""
    # Цитата из ГОСТ (пользователь вставил текст стандарта)
    if re.search(r"(маркировк[уы]?\s*эталон|свинцовыми\s*цифрами|первая.*цифра.*маркировк|код.*материал.*эталон|сплавы.*основе.*железа.*1.*алюмини)", text, re.IGNORECASE):
        return ToolResult(
            matched=True,
            answer=(
                "Маркировка эталонов чувствительности (ИКИ) по ГОСТ 7512-82 (п. 2.13):\n"
                "Формат: X-Y(-Z), где:\n"
                "— X (первая цифра): КОД МАТЕРИАЛА эталона: "
                "1 = сплавы на основе железа (сталь), "
                "2 = алюминий/магний, "
                "3 = титан, "
                "4 = медь/сплавы, "
                "5 = никель/сплавы;\n"
                "— Y (вторая цифра): номер проволоки в эталоне;\n"
                "— Z (третья цифра, опционально): тип (номер) дефекта."
            ),
            citation="[ГОСТ 7512-82, п. 2.13]",
        )
    # Вопрос про первую/вторую цифру
    if re.search(r"(перв[ая]?|втор[ая]?|треть[я]?|четвёрт[ая]?|цифр[аы]?.*маркировк|маркировк.*цифр)", text, re.IGNORECASE):
        return ToolResult(
            matched=True,
            answer=(
                "Маркировка радиографических снимков по ГОСТ 7512-82 (п. 2.13):\n"
                "Формат: X-Y(-Z), где:\n"
                "— X (первая цифра): марка (тип) материала — "
                "1=сталь, 2=алюминий/магний, 3=титан, 4=медь/сплавы, 5=никель/сплавы;\n"
                "— Y (вторая цифра): номер проволоки в эталоне;\n"
                "— Z (третья цифра, опционально): тип (номер) дефекта."
            ),
            citation="[ГОСТ 7512-82, п. 2.13]",
        )
    m = re.search(r"(\d+)[-–—](\d+)([-–—](\d+))?", text)
    if not m or not re.search(r"(расшифр|маркировк|запис[ьи]|условн|обознач|как чита|что значит|дешифр)", text, re.IGNORECASE):
        return ToolResult(matched=False)
    from normative import gost_7512 as M7512
    parts = [int(x) for x in [m.group(1), m.group(2)]]
    if m.group(4):
        parts.append(int(m.group(4)))
    if len(parts) == 3:
        a, b, c = parts
        mat_names = {1:'сталь', 2:'алюминий', 3:'титан', 4:'медь'}
        set_name = f"типоразмер №{a}"
        if a in mat_names:
            set_name = f"{mat_names[a]} (эталон №{a})"
        return ToolResult(
            matched=True,
            answer=(
                f"Условная запись «{a}-{b}-{c}» по ГОСТ 7512-82 (п. 2.10–2.13):\n"
                f"{a} — материал ({set_name});\n"
                f"{b} — номер проволоки в эталоне;\n"
                f"{c} — тип (номер) дефекта на эталонном снимке."
            ),
            citation="[ГОСТ 7512-82, п. 2.10–2.13]",
        )
    a, b = parts
    mat_names = {1:'сталь', 2:'алюминий', 3:'титан', 4:'медь'}
    return ToolResult(
        matched=True,
        answer=(
            f"Условная запись «{a}-{b}» по ГОСТ 7512-82 (п. 2.10–2.13):\n"
            f"{a} — обозначение материала эталона ({a}={mat_names.get(a, '?')});\n"
            f"{b} — номер типоразмера эталона."
        ),
        citation="[ГОСТ 7512-82, п. 2.10–2.13]",
    )


def _try_evaluate_weld_quality(text: str) -> ToolResult:
    """Оценка годности шва по табл. 4.8 НП-105-18."""
    if not re.search(r"(допустим|годен|оцен|качеств|соответств|норм[аы]|кол?ичеств[оа]|количество.*включ|Sпр|суммар[на]|приведенн)", text, re.IGNORECASE):
        return ToolResult(matched=False)
    cat = _parse_category(text)
    if cat is None or cat not in ('I','II','III'):
        return ToolResult(matched=False)
    # НП-105-18: IV, V, VI не существуют в табл. 4.8-4.11
    if cat in ('IV', 'V', 'VI'):
        return ToolResult(
            matched=True,
            answer=f"Категория сварного соединения «{cat}» не существует в таблицах норм НП-105-18.",
            citation="[НП-105-18, табл. 4.8–4.11]",
        )
    th = _parse_thickness(text)
    if th is None:
        return ToolResult(matched=False)
    lo, hi = th
    t = hi or lo
    from normative import np_105_18 as M105
    row = M105.lookup_acceptance_criteria('steel', cat, t)
    if not row or not row.get('max_inclusion_mm'):
        return ToolResult(
            matched=True,
            answer=(
                f"Для категории {cat} при толщине {fmt(t)} мм таблица 4.8 НП-105-18 "
                f"не содержит норм (толщина вне диапазона таблицы)."
            ),
            citation="[НП-105-18, табл. 4.8]",
        )
    max_inc = row['max_inclusion_mm']
    max_count = row['max_count_100mm']
    max_spr = row['max_total_area_mm2']
    answer_parts = [
        f"Для сварного соединения кат. {cat} при толщине {fmt(lo)}{'-'+fmt(hi) if hi else ''} мм "
        f"по НП-105-18 (табл. 4.8) установлены следующие нормы:"
    ]
    inc_match = re.search(r"(одиночн|включ|дефект).*?(\d+)[,.]?(?:\d+)?\s*(?:мм)", text, re.IGNORECASE)
    if inc_match:
        found_val = float(inc_match.group(2).replace(',','.'))
        if found_val <= max_inc:
            answer_parts.append(f"Размер включения {fmt(found_val)} мм ≤ {fmt(max_inc)} мм — ДОПУСТИМО.")
        else:
            answer_parts.append(f"Размер включения {fmt(found_val)} мм > {fmt(max_inc)} мм — НЕ ДОПУСКАЕТСЯ.")
    else:
        answer_parts.append(f"Макс. размер одиночного включения: не более {fmt(max_inc)} мм.")
    count_match = re.search(r"(\d+)\s*(?:шт|штук|включений)\s*(?:на\s*100|в\s*соедин)", text, re.IGNORECASE)
    if count_match:
        found_cnt = int(count_match.group(1))
        if found_cnt <= max_count:
            answer_parts.append(f"Количество {found_cnt} ≤ {max_count} на 100 мм — ДОПУСТИМО.")
        else:
            answer_parts.append(f"Количество {found_cnt} > {max_count} на 100 мм — НЕ ДОПУСКАЕТСЯ.")
    else:
        answer_parts.append(f"Количество включений и скоплений: не более {max_count} на 100 мм шва.")
    answer_parts.append(f"Суммарная приведённая площадь Sпр: не более {fmt(max_spr)} мм².")
    return ToolResult(
        matched=True,
        answer="\n".join(answer_parts),
        citation=f"[НП-105-18, табл. 4.8, кат. {cat}]",
    )


def _try_defect_cluster(text: str) -> ToolResult:
    """Определение скопления дефектов и Sпр."""
    if not re.search(r"(скоплен|кластер|групп[аы]\s+дефект|Sпр|суммарн[ая]?\s*приведенн)", text, re.IGNORECASE):
        return ToolResult(matched=False)
    return ToolResult(
        matched=True,
        answer=(
            "По НП-105-18 (п. 6.3.5): скопление дефектов — два или более дефекта, "
            "расположенных на расстоянии не более трёхкратного максимального поперечного "
            "размера наибольшего из них. Суммарная приведённая площадь Sпр вычисляется "
            "как сумма произведений длины каждого дефекта на его ширину (в мм²). "
            "Sпр не должна превышать значений, указанных в таблице 4.8 для каждой категории."
        ),
        citation="[НП-105-18, п. 6.3.5, табл. 4.8]",
    )


def _try_geometric_unsharpness(text: str) -> ToolResult:
    """Геометрическая нерезкость Ug для категорий."""
    if not re.search(r"(нерезк|U_?[gг]|геометрическ[ая]?\s*(нерезк|размыт))", text, re.IGNORECASE):
        return ToolResult(matched=False)
    cat = _parse_category(text)
    from normative import gost_50_05_07 as M507
    if cat and cat in M507.MAX_GEOMETRIC_UNSHARPNESS:
        ug = M507.MAX_GEOMETRIC_UNSHARPNESS[cat]
        return ToolResult(
            matched=True,
            answer=(
                f"Максимально допустимая геометрическая нерезкость Ug "
                f"для сварных соединений категории {cat} равна {ug} мм.\n"
                f"Формула расчёта: Ug = Φ · b / (f − b),\n"
                f"где Φ — размер фокусного пятна, b — расстояние от объекта до плёнки,\n"
                f"f — расстояние от источника до плёнки."
            ),
            citation="[ГОСТ Р 50.05.07-2018, приложение А, п. А.3; MAX_GEOMETRIC_UNSHARPNESS]",
        )
    return ToolResult(matched=False)


def _try_optical_density(text: str) -> ToolResult:
    """Оптическая плотность плёнки по категориям."""
    if not re.search(r"(оптическ[ая]?\s*плотност|плотност.*снимк|D.*плёнк|дуплекс)", text, re.IGNORECASE):
        return ToolResult(matched=False)
    cat = _parse_category(text)
    from normative import gost_50_05_07 as M507
    if cat and cat in M507.OPTICAL_DENSITY:
        od = M507.OPTICAL_DENSITY[cat]
        return ToolResult(
            matched=True,
            answer=(
                f"Требования к оптической плотности D радиографического снимка "
                f"для категории {cat}: от {od['min']} до {od['max']}."
            ),
            citation="[ГОСТ Р 50.05.07-2018, п. 6.3.3]",
        )
    # общий вопрос
    if re.search(r"как[аяи]?\s*оптическ|класс.*плёнк|Dmin|Dmax", text, re.IGNORECASE):
        parts = [f"кат. {k}: D = {v['min']}–{v['max']}" for k, v in M507.OPTICAL_DENSITY.items()]
        return ToolResult(
            matched=True,
            answer=(
                "Требования к оптической плотности D радиографического снимка "
                f"(ГОСТ Р 50.05.07-2018, п. 6.3.3):\n" + "\n".join(parts)
            ),
            citation="[ГОСТ Р 50.05.07-2018, п. 6.3.3]",
        )
    return ToolResult(matched=False)


def _try_table_48_lookup(text: str) -> ToolResult:
    """Поиск по таблице 4.8 НП-105-18: материал + категория + толщина."""
    from normative import np_105_18 as M105
    mat = 'steel'
    if re.search(r"алюмин|al", text, re.IGNORECASE):
        mat = 'aluminum'
    elif re.search(r"титан|ti|titan", text, re.IGNORECASE):
        mat = 'titanium'
    cat = _parse_category(text)
    if not cat or cat not in ('I', 'II', 'III'):
        return ToolResult(matched=False)
    t_match = re.search(r"(\d+(?:[.,]\d+)?)\s*мм", text)
    if not t_match:
        return ToolResult(matched=False)
    thickness = float(t_match.group(1).replace(',', '.'))
    try:
        row = M105.lookup_acceptance_criteria(mat, cat, thickness)
    except (KeyError, ValueError, TypeError):
        return ToolResult(matched=False)
    if not row or row.get('error'):
        return ToolResult(matched=False)
    return ToolResult(
        matched=True,
        answer=(
            f"Для {'стали' if mat == 'steel' else mat} толщиной {row['thickness_mm']:.0f} мм, "
            f"категория {cat} (табл. 4.8 НП-105-18):\n"
            f"• чувствительность K ≤ {row['sensitivity_K_mm']} мм;\n"
            f"• одиночные включения ≤ {row['max_inclusion_mm']} мм;\n"
            f"• скопления ≤ {row['max_cluster_mm']} мм;\n"
            f"• число на 100 мм шва ≤ {row['max_count_per_100mm']} шт;\n"
            f"• Sпр ≤ {row['sum_area_mm2']} мм²."
        ),
        citation="[НП-105-18, табл. 4.8]",
    )


def _try_recommended_source(text: str) -> ToolResult:
    """Источник излучения по таблице Б.1-Б.3: материал + толщина."""
    if not re.search(r"(источник|гамма|излучен|радионуклид|изотоп|просвечив|Se-75|Ir-192|Co-60|Tm-170|Yb-169)",
                     text, re.IGNORECASE):
        return ToolResult(matched=False)
    from normative import gost_50_05_07 as M507
    mat = 'steel'
    if re.search(r"алюмин|al", text, re.IGNORECASE):
        mat = 'aluminum'
    elif re.search(r"титан|ti|titan", text, re.IGNORECASE):
        mat = 'titanium'
    t_match = re.search(r"(\d+(?:[.,]\d+)?)\s*мм", text)
    if not t_match:
        return ToolResult(matched=False)
    thickness = float(t_match.group(1).replace(',', '.'))
    sources = M507.get_suitable_sources(thickness, mat)
    if not sources:
        return ToolResult(matched=False)
    lines = [f"— {s['name']} ({s['range_label']})" for s in sources]
    mat_label = {'steel': 'стали', 'aluminum': 'алюминия', 'titanium': 'титана'}.get(mat, mat)
    return ToolResult(
        matched=True,
        answer=(
            f"Допустимые источники излучения для {mat_label} "
            f"толщиной {thickness:.0f} мм (табл. Б.1–Б.3):\n" + "\n".join(lines)
        ),
        citation="[ГОСТ Р 50.05.07-2018, табл. Б.1–Б.3]",
    )


def _try_geometry_formula(text: str) -> ToolResult:
    """Дословные формулы приложения Г (ГОСТ Р 50.05.07-2018) по запросу."""
    if not re.search(r"(формул|геометр|расстоян.*l|фокусн.*расстоян|l\s*[≥≤]|коэффициент\s*c|приложен.*г|таблиц.*г\.1|схем.*3[абгд]|схем.*4[аб])",
                     text, re.IGNORECASE):
        return ToolResult(matched=False)
    from normative import gost_50_05_07 as M507
    F = getattr(M507, 'TABLE_G1_FORMULAS', {})
    if not F:
        return ToolResult(matched=False)
    # Определяем запрошенную схему
    sch = None
    m = re.search(r"схем[аеы]?\s*(3[абгд]|4[аб])", text, re.IGNORECASE)
    if m:
        sch = m.group(1).lower()
    lines = [
        f"• Общая: {F.get('G.1_base')}",
        f"• Длина участка: {F.get('G.1_L_max')}",
        f"• Коэффициент c: {F.get('G.1_c')}",
    ]
    if sch and sch in F:
        lines.append(f"• Для схемы {sch}: {F[sch]}")
    else:
        # все схемы
        for k in ('3a', '3b', '3g', '3d', '4a', '4b'):
            if k in F:
                lines.append(f"• Схема {k}: {F[k]}")
    lines.append(f"• Условие нерезкости (трубы): {F.get('G.2_Ug_tube')}")
    lines.append(f"• Условие нерезкости (угловые): {F.get('G.2_Ug')}")
    return ToolResult(
        matched=True,
        answer=("Формулы приложения Г (ГОСТ Р 50.05.07-2018):\n" + "\n".join(lines)),
        citation="[ГОСТ Р 50.05.07-2018, приложение Г, табл. Г.1]",
    )


def _try_exposure_calc(text: str) -> ToolResult:
    """Пояснение/расчёт времени экспозиции: различает рентген-трубку и изотопный источник.
    Опирается на реальные данные RADIATION_SOURCES (ГОСТ Р 50.05.07-2018, приложение Б)."""
    if not re.search(r"(экспозиц|время.*экспоз|ток.*труб|ток.*увелич|удвоен.*ток|минут|экспозиц.*ток|рассчитай.*экспоз|расчёт.*экспоз|рассчитать.*экспоз|сколько.*экспоз|выдержк)",
                     text, re.IGNORECASE):
        return ToolResult(matched=False)
    # НЕ перехватывать геометрию: число экспозиций N, схемы, f, приложение Г — это не время
    if re.search(r"(число\s+экспоз|количество\s+экспоз|схем[аеы]?\s*3[абгд]|схем[аеы]?\s*4[аб]|приложен.*г|расстоян.*источник|расстояние\s*[lф])", text, re.IGNORECASE):
        return ToolResult(matched=False)

    from normative import gost_50_05_07 as M507
    sources = getattr(M507, 'RADIATION_SOURCES', [])

    # --- Поиск изотопного источника в вопросе ---
    isotope = None
    for src in sources:
        code = src.get('code', '')
        if re.search(r'\b' + re.escape(code) + r'\b', text, re.IGNORECASE):
            isotope = src
            break
    if not isotope and re.search(r'селен', text, re.IGNORECASE):
        for src in sources:
            if src.get('code', '').startswith('Se'):
                isotope = src
                break
    if not isotope and re.search(r'ирид', text, re.IGNORECASE):
        for src in sources:
            if src.get('code', '').startswith('Ir'):
                isotope = src
                break
    if not isotope and re.search(r'кобальт', text, re.IGNORECASE):
        for src in sources:
            if src.get('code', '').startswith('Co'):
                isotope = src
                break
    if not isotope and re.search(r'(ytterb|иттерб)', text, re.IGNORECASE):
        for src in sources:
            if src.get('code', '').startswith('Yb'):
                isotope = src
                break
    if not isotope and re.search(r'(тулий|thulium)', text, re.IGNORECASE):
        for src in sources:
            if src.get('code', '').startswith('Tm'):
                isotope = src
                break

    if isotope:
        name = isotope.get('name', '')
        energy = isotope.get('energy_display') or isotope.get('energy_kev', '')
        hl = isotope.get('half_life', '')
        return ToolResult(
            matched=True,
            answer=(
                f"Для радионуклидного источника {name} время экспозиции рассчитывается иначе, "
                f"чем для рентгеновской трубки: здесь ключевая величина — не ток, а "
                f"АКТИВНОСТЬ источника и расстояние до плёнки.\n\n"
                f"Параметры {name} (ГОСТ Р 50.05.07-2018, приложение Б):\n"
                f"— энергия излучения: {energy};\n"
                f"— период полураспада: {hl}.\n\n"
                f"Базовое соотношение для гамма-дефектоскопии:\n"
                f"мощность экспозиционной дозы у плёнки  P = A·Γ / d²,\n"
                f"где A — активность источника (Ки или Бк), Γ — гамма-постоянная источника "
                f"(зависит от радионуклида), d — расстояние от источника до плёнки.\n\n"
                f"Время экспозиции:\n"
                f"t = (K · d² · 2ⁿ) / (A · Γ),\n"
                f"где K — требуемая экспозиционная доза на плёнку (определяется классом "
                f"плёнки и требуемой оптической плотностью), n — класс чувствительности.\n\n"
                f"Чтобы рассчитать t, нужны: активность A источника (Ки/Бк), расстояние d, "
                f"класс плёнки и требуемая оптическая плотность. Назовёте их — посчитаю."
            ),
            citation="[ГОСТ Р 50.05.07-2018, приложение Б, табл. Б.1–Б.3]",
        )

    # --- Рентгеновская трубка (ток/напряжение) или общий принцип ---
    m_time = re.search(r"(\d+[.,]?\d*)\s*мин", text)
    m_factor = re.search(r"(увелич|удвоен|повысил|возрос|уменьш|сниж|в\s*(\d+[.,]?\d*)\s*раз)", text, re.IGNORECASE)
    if not m_time:
        return ToolResult(
            matched=True,
            answer=(
                "Время экспозиции при рентгенографическом контроле определяется из "
                "условия постоянства экспозиции:\n"
                "E = I · t = const  (при неизменных напряжении на трубке и расстоянии "
                "от источника до плёнки).\n\n"
                "Отсюда при изменении тока трубки I время экспозиции t пересчитывается "
                "обратно пропорционально:\n"
                "t₁ = t₀ · (I₀ / I₁).\n\n"
                "Например: если время экспозиции 10 мин при токе I₀, а ток увеличить "
                "в 2 раза, время сократится до 5 мин (10 / 2 = 5)."
            ),
            citation="[ГОСТ Р 50.05.07-2018, п. 6.3.7 — общий принцип: экспозиция = ток × время]",
        )
    t0 = float(m_time.group(1).replace(',', '.'))
    factor = 1.0
    if m_factor:
        if 'удвоен' in m_factor.group(0).lower() or '2' in (m_factor.group(2) or ''):
            factor = 2.0
        elif m_factor.group(2):
            factor = float(m_factor.group(2).replace(',', '.'))
    if m_factor and ('сниж' in m_factor.group(0).lower() or 'уменьш' in m_factor.group(0).lower()):
        factor = 1.0 / factor
    t1 = t0 / factor
    return ToolResult(
        matched=True,
        answer=(
            f"Время экспозиции обратно пропорционально току трубки "
            f"(экспозиция E = I·t = const при неизменных напряжении и расстоянии).\n"
            f"Было: {t0:.0f} мин при токе I₀.\n"
            f"Ток изменился в {factor:.0f} раз → время: {t1:.0f} мин "
            f"(t = {t0:.0f} / {factor:.0f} = {t1:.0f})."
        ),
        citation="[ГОСТ Р 50.05.07-2018, п. 6.3.7 — общий принцип: экспозиция = ток × время]",
    )


def _try_trap_comparison(text: str) -> ToolResult:
    """Ловушка: сравнение таблиц разных материалов/категорий."""
    if not re.search(r"(сравн|как[ая]?.*строж|как[аяя]?.*разн|разниц[а]?|отлич|чётче|жёстч)", text, re.IGNORECASE):
        return ToolResult(matched=False)
    # Поймать сравнение таблиц 4.8-4.11
    if re.search(r"таблиц[аеы]?\s*(4[.,]?\d)", text, re.IGNORECASE) and \
       re.search(r"(друг[аяой]?|разн[ы]?[еых]?|сравн)", text, re.IGNORECASE) and \
       not re.search(r"вопрос|какой.*метод|норм[а]?.*дефект", text, re.IGNORECASE):
        m = re.search(r"(4[.,]?\d)\s*.*(4[.,]?\d)", text)
        if m:
            return ToolResult(
                matched=True,
                answer=(
                    f"Сравнение таблиц {m.group(1)} и {m.group(2)} некорректно — "
                    f"они относятся к разным материалам или диапазонам толщин. "
                    f"Каждая таблица применяется к своему материалу независимо."
                ),
                citation="[НП-105-18, табл. 4.8–4.11]",
            )
    # Сравнение сталь/алюминий/титан (ловушка)
    if re.search(r"(стал[ьяь].*алюмин|титан.*стал[ьяь]|алюмин.*титан|алюмин.*стал[ьяь]|строж)", text, re.IGNORECASE) and \
       re.search(r"(сравн|как[ая]?.*отлич|разн[иа])", text, re.IGNORECASE):
        return ToolResult(
            matched=True,
            answer=(
                "Некорректно сравнивать нормы для разных материалов: "
                "сталь (табл. 4.8), алюминий (табл. 4.10), титан (табл. 4.11) "
                "имеют разные диапазоны толщин и критерии. "
                "Оценка проводится по каждой таблице независимо."
            ),
            citation="[НП-105-18, табл. 4.8–4.11]",
        )
    return ToolResult(matched=False)

def _try_zone_width(text: str) -> ToolResult:
    """Ширина контролируемой зоны / ОШЗ по ГОСТ Р 50.05.07-2018 п.6.3.13."""
    if not re.search(r"(ОШЗ|околошовн|ширин[ае].*контролируем|ширин[ае].*снимк|ширин[ае].*участк)",
                     text, re.IGNORECASE):
        return ToolResult(matched=False)
    t_match = re.search(r"(\d+)\s*мм", text)
    thickness = int(t_match.group(1)) if t_match else None
    if thickness is None:
        return ToolResult(
            matched=True,
            answer=(
                "Минимальная ширина контролируемой зоны снимка по "
                "ГОСТ Р 50.05.07-2018 п. 6.3.13:\n"
                "- при толщине сваренных кромок от 5 до 20 мм — не менее толщины;\n"
                "- при толщине свыше 20 мм — не менее 20 мм.\n"
                "ОШЗ (околошовная зона): не менее 5 мм в каждую сторону от оси шва."
            ),
            citation="[ГОСТ Р 50.05.07-2018, п. 6.3.13]",
        )
    zone = 5 if thickness <= 5 else (thickness if thickness <= 20 else 20)
    return ToolResult(
        matched=True,
        answer=(
            f"Ширина околошовной зоны (ОШЗ) — не менее 5 мм в каждую сторону.\n"
            f"Минимальная ширина контролируемой зоны снимка "
            f"для толщины {thickness} мм:\n"
            f"- по п. 6.3.13 ГОСТ Р 50.05.07-2018: {zone} мм."
        ),
        citation="[ГОСТ Р 50.05.07-2018, п. 6.3.13]",
    )


# --- точка входа ---------------------------------------------------------

def _try_activity_decay(text: str) -> ToolResult:
    """Расчёт активности радионуклидного источника через спад:
    A = A₀ · 2^(−t / T½). Берёт РЕАЛЬНЫЙ период полураспада из базы (приложение Б)."""
    if not re.search(r"(активн|распад|спад|полураспад|радиоактивн|источник.*излучен|нуклид|источник.*se|источник.*ir|источник.*co)",
                     text, re.IGNORECASE):
        return ToolResult(matched=False)
    # Нужны прошедшее время и начальная активность (или наоборот)
    t_match = re.search(r"(\d+[.,]?\d*)\s*(дн|сут|год|лет|мес|час|ч\b)", text, re.IGNORECASE)
    a_match = re.search(r"(\d+[.,]?\d*)\s*(Ки|ки|Бк|Кюри|кюри|Curie|Ci)", text, re.IGNORECASE)
    if not t_match or not a_match:
        # Данных не хватает — даём формулу и просим недостающее, не выдумывая
        return ToolResult(
            matched=True,
            answer=(
                "Расчёт активности радионуклидного источника выполняется по закону "
                "радиоактивного распада:\n"
                "A(t) = A₀ · 2^(−t / T½),\n"
                "где A₀ — начальная активность, t — прошедшее время, T½ — период "
                "полураспада нуклида.\n\n"
                "Назовите нуклид (например, Se-75, Ir-192, Co-60), начальную активность "
                "и прошедшее время — рассчитаю текущую активность по реальному T½ из "
                "ГОСТ Р 50.05.07-2018 (приложение Б)."
            ),
            citation="[ГОСТ Р 50.05.07-2018, приложение Б, табл. Б.1–Б.3]",
        )
    t_val = float(t_match.group(1).replace(',', '.'))
    unit = t_match.group(2).lower()
    # Приводим к суткам
    if unit in ('год', 'лет'):
        t_days = t_val * 365.25
    elif unit in ('мес',):
        t_days = t_val * 30.44
    elif unit in ('час', 'ч'):
        t_days = t_val / 24.0
    else:  # дн / сут
        t_days = t_val
    a0 = float(a_match.group(1).replace(',', '.'))
    a_unit = 'Ки' if re.search(r'(Ки|ки|Кюри|кюри|Curie|Ci)', a_match.group(0), re.IGNORECASE) else 'Бк'

    from normative import gost_50_05_07 as M507
    sources = getattr(M507, 'RADIATION_SOURCES', [])
    isotope = None
    for src in sources:
        code = src.get('code', '')
        # совпадение кода с возможным пробелом/слитно: Se-75 / Se75 / SE 75
        code_pat = re.escape(code).replace(r'\-', r'\-?')
        if re.search(r'\b' + code_pat + r'\b', text, re.IGNORECASE) \
           or re.search(code_pat.replace('-', ' ?'), text, re.IGNORECASE):
            isotope = src
            break
    if not isotope and re.search(r'селен', text, re.IGNORECASE):
        for src in sources:
            if src.get('code', '').startswith('Se'):
                isotope = src
                break
    if not isotope and re.search(r'ирид', text, re.IGNORECASE):
        for src in sources:
            if src.get('code', '').startswith('Ir'):
                isotope = src
                break
    if not isotope and re.search(r'кобальт', text, re.IGNORECASE):
        for src in sources:
            if src.get('code', '').startswith('Co'):
                isotope = src
                break

    if not isotope:
        return ToolResult(
            matched=True,
            answer=(
                "Укажите нуклид (Se-75, Ir-192, Co-60 и др.), чтобы подставить его "
                "реальный период полураспада из ГОСТ Р 50.05.07-2018 (приложение Б). "
                "Формула спада: A(t) = A₀ · 2^(−t / T½)."
            ),
            citation="[ГОСТ Р 50.05.07-2018, приложение Б]",
        )

    # Парсим период полураспада из строки '119,8 сут' / '5,27 лет' и т.п.
    hl_raw = isotope.get('half_life', '')
    hl_match = re.search(r"(\d+[.,]?\d*)\s*(сут|дн|год|лет|мес)", hl_raw, re.IGNORECASE)
    if not hl_match:
        return ToolResult(
            matched=True,
            answer=(
                f"Для {isotope.get('name','')} в базе не удалось разобрать числовой "
                f"период полураспада (указано: «{hl_raw}»). Назовите его — рассчитаю."
            ),
            citation="[ГОСТ Р 50.05.07-2018, приложение Б]",
        )
    hl_val = float(hl_match.group(1).replace(',', '.'))
    hl_unit = hl_match.group(2).lower()
    if hl_unit in ('год', 'лет'):
        hl_days = hl_val * 365.25
    elif hl_unit in ('мес',):
        hl_days = hl_val * 30.44
    else:  # сут / дн
        hl_days = hl_val

    ratio = 2 ** (-t_days / hl_days)
    a_curr = a0 * ratio
    name = isotope.get('name', '')
    return ToolResult(
        matched=True,
        answer=(
            f"Расчёт активности источника {name} по закону радиоактивного распада "
            f"[ГОСТ Р 50.05.07-2018, приложение Б]:\n\n"
            f"Исходные данные (из вопроса):\n"
            f"— начальная активность A₀ = {a0:g} {a_unit};\n"
            f"— прошедшее время t = {t_val:g} {unit} (~{t_days:.1f} сут);\n"
            f"— период полураспада {name}: T½ = {hl_raw}.\n\n"
            f"Формула: A(t) = A₀ · 2^(−t / T½).\n"
            f"Показатель степени: −t/T½ = −{t_days:.1f} / {hl_days:.1f} = "
            f"{-t_days/hl_days:.4f}.\n"
            f"Коэффициент спада: 2^(−t/T½) = {ratio:.4f}.\n\n"
            f"Текущая активность: A = {a0:g} · {ratio:.4f} = "
            f"{a_curr:.2f} {a_unit}.\n\n"
            f"Ответ: {a_curr:.2f} {a_unit}."
        ),
        citation="[ГОСТ Р 50.05.07-2018, приложение Б, табл. Б.1–Б.3]",
    )


_HANDLERS = [
    _try_activity_decay, _try_exposure_calc, _try_geometry_f, _try_xray_standard_types, _try_sensitivity, _try_wire_iqi,
    _try_iqi_range, _try_xray_voltage, _try_zone_width,
    _try_materials_separate_tables, _try_surface_defect_table,
    _try_methods, _try_iqi_types, _try_iqi_number, _try_marking_decode,
    _try_evaluate_weld_quality, _try_defect_cluster, _try_table_48_lookup,
    _try_geometric_unsharpness, _try_optical_density, _try_recommended_source,
    _try_geometry_formula, _try_trap_comparison,
]


def _try_pt_sensitivity_class(text: str, force_pt: bool = False) -> ToolResult:
    """Классы чувствительности КК — ГОСТ Р 50.05.09, табл. 1."""
    if M509 is None:
        return ToolResult(matched=False)
    q = text.lower()
    has_pt_cue = bool(re.search(
        r"капилляр|пенетрант|\bкк\b|\bpt\b|50\.05\.09|"
        r"чувствительн\w*\s*капилляр|раскрыт\w*\s*(трещин|несплошн|мкм)",
        q,
        re.IGNORECASE,
    ))
    if not has_pt_cue and not force_pt:
        return ToolResult(matched=False)
    if re.search(r"радиограф|ргк|\bрк\b|плёнк|пленк|ики|проволок", q) and not has_pt_cue:
        return ToolResult(matched=False)

    # ширина раскрытия в мкм
    m_um = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(?:мкм|µm|um)\b",
        text,
        re.IGNORECASE,
    )
    if m_um:
        w = float(m_um.group(1).replace(",", "."))
        cls = M509.get_sensitivity_class_by_crack_um(w)
        if not cls:
            return ToolResult(
                matched=True,
                answer=(
                    f"Ширина раскрытия {fmt(w)} мкм вне диапазонов табл. 1 "
                    f"(I: <1,0; II: 1,0–10,0; III: 10,0–100,0 мкм)."
                ),
                citation=f"[{M509.DOCUMENT_CODE}, табл. 1]",
            )
        info = M509.SENSITIVITY_CLASSES[cls]
        return ToolResult(
            matched=True,
            answer=(
                f"По ширине раскрытия {fmt(w)} мкм на контрольном образце "
                f"соответствует класс чувствительности {cls} "
                f"({info['description']})."
            ),
            citation=f"[{M509.DOCUMENT_CODE}, табл. 1]",
        )

    m_cls = re.search(
        r"класс(?:а|у)?\s*(?:чувствительности\s*)?([IiVvХх]{1,3}|[123])\b",
        text,
    )
    if m_cls or re.search(r"класс\w*\s*чувствительн|табл\.?\s*1", q):
        if m_cls:
            info = M509.get_sensitivity_class_info(m_cls.group(1))
            if info:
                return ToolResult(
                    matched=True,
                    answer=(
                        f"Класс чувствительности {info['code']}: "
                        f"{info['description']} "
                        f"(ширина раскрытия несплошности на КО)."
                    ),
                    citation=f"[{M509.DOCUMENT_CODE}, табл. 1]",
                )
        return ToolResult(
            matched=True,
            answer=M509.format_sensitivity_table(),
            citation=f"[{M509.DOCUMENT_CODE}, табл. 1, п. 5.7–5.8]",
        )
    return ToolResult(matched=False)


def _try_pt_ambient(text: str, force_pt: bool = False) -> ToolResult:
    if M509 is None:
        return ToolResult(matched=False)
    q = text.lower()
    has_pt_cue = bool(re.search(r"капилляр|\bкк\b|пенетрант|50\.05\.09", q))
    topic = bool(re.search(
        r"температур\w*\s*(контрол|окруж|воздух)|влажност|"
        r"не гарантир|раскрыт\w*\s*0[,.]5",
        q,
    ))
    if not ((has_pt_cue and topic) or (force_pt and topic) or (
        has_pt_cue and re.search(r"услови|сред|воздух", q)
    )):
        return ToolResult(matched=False)
    if re.search(r"радиограф|ргк|плёнк|пленк", q) and not has_pt_cue:
        return ToolResult(matched=False)
    return ToolResult(
        matched=True,
        answer=M509.format_ambient_rules(),
        citation=f"[{M509.DOCUMENT_CODE}, п. 5.5–5.6]",
    )


def _try_pt_contact_time(text: str, force_pt: bool = False) -> ToolResult:
    if M509 is None:
        return ToolResult(matched=False)
    q = text.lower()
    topic = bool(re.search(
        r"время\s*контакт|выдержк\w*\s*пенетрант|контакт\w*\s*пенетрант|"
        r"пенетрант\w*.{0,40}(мин|время)|капилляр.{0,40}время",
        q,
    ))
    if not topic:
        if force_pt and re.search(r"(выдержк|контакт).{0,20}(пенетрант|поверхност)", q):
            topic = True
        else:
            return ToolResult(matched=False)
    kind = 'weld'
    if re.search(r"основн\w*\s*металл|без\s*свар", q):
        kind = 'base_metal'
    elif re.search(r"щелоч|кислот", q):
        kind = 'chem'
    mins = M509.get_min_penetrant_contact_min(kind)
    if kind == 'base_metal':
        detail = (
            f"для основного металла — не менее {mins} мин"
        )
    elif kind == 'chem':
        detail = (
            f"после контакта со щелочной или кислой средой рекомендуется "
            f"увеличить время контакта до {mins} мин"
        )
    else:
        detail = (
            f"для сварных соединений (включая околошовную зону) — не менее "
            f"{mins} мин; для основного металла — не менее "
            f"{M509.PENETRANT_CONTACT_MIN_BASE_METAL_MIN} мин"
        )
    return ToolResult(
        matched=True,
        answer=(
            f"Время контакта пенетранта с поверхностью зависит от ДМ и условий, "
            f"но по {M509.DOCUMENT_CODE}, п. 8.2.1.1: {detail}. "
            f"Высыхание пенетранта на поверхности не допускается (п. 8.2.1.2)."
        ),
        citation=f"[{M509.DOCUMENT_CODE}, п. 8.2.1.1–8.2.1.2]",
    )


def _try_pt_illuminance(text: str, force_pt: bool = False) -> ToolResult:
    if M509 is None:
        return ToolResult(matched=False)
    q = text.lower()
    topic = bool(re.search(
        r"освещ[её]нн|облуч[её]нн|ультрафиолет|\bуф\b|люминесцентн\w*\s*ламп",
        q,
    ))
    has_pt_cue = bool(re.search(r"капилляр|\bкк\b|пенетрант|50\.05\.09", q))
    if not topic:
        return ToolResult(matched=False)
    if not has_pt_cue and not force_pt:
        return ToolResult(matched=False)
    m_cls = re.search(r"класс(?:а|у)?\s*(?:чувствительности\s*)?([IiVv]{1,3}|[123])\b", text)
    cls = m_cls.group(1) if m_cls else 'II'
    info = M509.get_sensitivity_class_info(cls)
    if not info:
        return ToolResult(matched=False)
    ill = M509.get_illuminance(info['code'])
    uv = M509.get_uv_irradiance(info['code'])
    parts = [
        f"Для класса {info['code']} по табл. 2 ({M509.DOCUMENT_CODE}): "
        f"люминесцентные лампы — комбинированная {ill['fluorescent_combined']} лк, "
        f"общая {ill['fluorescent_general']} лк; "
        f"лампы накаливания — комбинированная {ill['incandescent_combined']} лк, "
        f"общая {ill['incandescent_general']} лк."
    ]
    if uv is not None:
        parts.append(
            f"УФ-облучённость контролируемой поверхности (табл. 3) — "
            f"не менее {uv} мкВт/см²."
        )
    return ToolResult(
        matched=True,
        answer=' '.join(parts),
        citation=f"[{M509.DOCUMENT_CODE}, табл. 2–3, п. 8.1.23–8.1.24]",
    )


def _try_pt_dm_sets(text: str, force_pt: bool = False) -> ToolResult:
    if M509 is None:
        return ToolResult(matched=False)
    q = text.lower()
    topic = bool(re.search(
        r"набор\w*\s*дм|дефектоскопическ\w*\s*материал|смеш\w*\s*набор|"
        r"пенетрант\w*.{0,30}проявител|прил\.?\s*а|приложение\s*а|"
        r"совместим\w*\s*набор",
        q,
    ))
    has_pt_cue = bool(re.search(r"капилляр|\bкк\b|пенетрант|дм|50\.05\.09", q))
    if not topic:
        return ToolResult(matched=False)
    if not has_pt_cue and not force_pt:
        return ToolResult(matched=False)
    m_cls = re.search(r"класс(?:а|у)?\s*(?:чувствительности\s*)?([IiVv]{1,3}|[123])\b", text)
    answer = M509.format_dm_rules()
    if m_cls:
        kits = M509.kits_for_class(m_cls.group(1))
        if kits:
            names = '; '.join(
                f"{k['name']} ({k['method']}, {k['temp_c'][0]}…{k['temp_c'][1]} °C)"
                for k in kits[:8]
            )
            answer += (
                f" Рекомендуемые наборы для класса {kits[0]['class']} "
                f"(прил. А, табл. А.1): {names}."
            )
    return ToolResult(
        matched=True,
        answer=answer,
        citation=f"[{M509.DOCUMENT_CODE}, п. 6.1.1, прил. А]",
    )


def _try_pt_roughness(text: str, force_pt: bool = False) -> ToolResult:
    if M509 is None:
        return ToolResult(matched=False)
    q = text.lower()
    topic = bool(re.search(r"шероховат|ra\s*\d|rz\s*\d|подготовк\w*\s*поверхност", q))
    has_pt_cue = bool(re.search(r"капилляр|\bкк\b|пенетрант|50\.05\.09", q))
    if not topic:
        return ToolResult(matched=False)
    if re.search(r"радиограф|ргк", q) and not has_pt_cue:
        return ToolResult(matched=False)
    if not has_pt_cue and not force_pt:
        return ToolResult(matched=False)
    return ToolResult(
        matched=True,
        answer=(
            f"По {M509.DOCUMENT_CODE}, п. 8.1.5 участки контроля механически обрабатывают "
            f"до шероховатости Ra {fmt(M509.SURFACE_ROUGHNESS_RA_TARGET)} "
            f"(Rz {fmt(M509.SURFACE_ROUGHNESS_RZ_TARGET)}). "
            f"Допускается не более Ra {fmt(M509.SURFACE_ROUGHNESS_RA_MAX_ALLOWED)} "
            f"(Rz {fmt(M509.SURFACE_ROUGHNESS_RZ_MAX_ALLOWED)}) при отсутствии "
            f"недопустимого окрашенного фона. Контроль шероховатости — образцы по "
            f"{M509.SURFACE_ROUGHNESS_STANDARD}."
        ),
        citation=f"[{M509.DOCUMENT_CODE}, п. 8.1.5]",
    )


_PT_HANDLERS = [
    _try_pt_sensitivity_class,
    _try_pt_ambient,
    _try_pt_contact_time,
    _try_pt_illuminance,
    _try_pt_dm_sets,
    _try_pt_roughness,
]


def resolve(question: str, method_scope: Optional[str] = None) -> ToolResult:
    """Пытаемся ответить точным вызовом normative.*. Возвращает ToolResult."""
    scope = (method_scope or '').strip().upper()
    force_pt = scope == 'КК'
    # РГК-tools только в режиме РК (или без scope); PT — только КК.
    # Для УЗК/ВИК/КГ/персонала пока опираемся на RAG по профильным ГОСТ.
    if force_pt:
        handlers = list(_PT_HANDLERS)
    elif scope in ('', 'РК'):
        handlers = list(_PT_HANDLERS) + list(_HANDLERS)
    else:
        return ToolResult(matched=False)

    for h in handlers:
        try:
            # PT-хендлеры принимают force_pt; РГК-хендлеры — только question
            if h in _PT_HANDLERS:
                r = h(question, force_pt=force_pt)
            else:
                r = h(question)
            if r.matched:
                return r
        except Exception:
            continue
    return ToolResult(matched=False)
