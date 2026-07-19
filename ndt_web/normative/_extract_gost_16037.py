# -*- coding: utf-8 -*-
"""
Одноразовый экстрактор данных ГОСТ 16037-80 из скана PDF.
Создаёт:
  - ndt_web/normative_docs/ГОСТ 16037-80.pdf
  - ndt_web/static/techcards/joints/gost_16037/<код>.png
  - ndt_web/normative/_gost_16037_extract.json
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC_PDF = Path(r"c:\Users\torf1\Downloads\gost_16037-80.pdf")
DST_PDF = ROOT / "normative_docs" / "ГОСТ 16037-80.pdf"
PAGES_DIR = ROOT / "_gost16037_pages"
SKETCH_DIR = ROOT / "static" / "techcards" / "joints" / "gost_16037"
OUT_JSON = Path(__file__).resolve().parent / "_gost_16037_extract.json"

# PDF page index (0-based) → file page_XX.png (1-based)
# Table 1 lives on PDF pages 3–8 (files page_03 … page_08)
# Dimensional tables 2–33 on PDF pages 9–22 approx.

WELDING_PROCESSES = {
    "ЗП": {
        "code": "ЗП",
        "name": "Дуговая сварка в защитном газе плавящимся электродом",
        "iso_ref": "GMAW/MIG-MAG",
    },
    "ЗН": {
        "code": "ЗН",
        "name": "Дуговая сварка в защитном газе неплавящимся электродом",
        "iso_ref": "GTAW/TIG",
    },
    "Р": {
        "code": "Р",
        "name": "Ручная дуговая сварка",
        "iso_ref": "SMAW",
    },
    "Ф": {
        "code": "Ф",
        "name": "Дуговая сварка под флюсом",
        "iso_ref": "SAW",
    },
    "Г": {
        "code": "Г",
        "name": "Газовая сварка",
        "iso_ref": "OFW",
    },
}

DIMENSION_SYMBOLS = {
    "s": "толщина стенки свариваемых деталей",
    "s1": "толщина стенки второй детали",
    "b": "зазор между кромками после прихватки",
    "e": "ширина сварного шва",
    "g": "выпуклость сварного шва",
    "delta": "толщина подкладного кольца (δ)",
    "a": "толщина шва",
    "c": "притупление кромки",
    "B": "ширина нахлестки",
    "l": "длина муфты",
    "K": "катет углового шва",
    "K1": "катет углового шва со стороны разъема фланца",
    "Dn": "наружный диаметр трубы",
    "f": "фаска фланца",
}


def _m(
    zp=None, zn=None, r=None, f=None, g=None,
):
    """Build methods_limits: {method: {s_min,s_max,dn_min,dn_max}}."""
    out = {}
    for code, val in (("ЗП", zp), ("ЗН", zn), ("Р", r), ("Ф", f), ("Г", g)):
        if not val:
            continue
        s_range, dn = val
        s_min, s_max = s_range
        if isinstance(dn, (list, tuple)):
            dn_min, dn_max = dn
        else:
            dn_min, dn_max = dn, None
        out[code] = {
            "s_min": s_min,
            "s_max": s_max,
            "dn_min": dn_min,
            "dn_max": dn_max,
        }
    return out


def _joint(
    code: str,
    *,
    name: str,
    joint_type: str,
    groove: str,
    weld_character: str,
    methods_limits: dict,
    gost_table: str,
    connection_kind: str,
    notes: str = "",
    dimensions: list | None = None,
    dimensions_notes: str = "",
    sketch_page: int | None = None,
    uncertain: list | None = None,
):
    methods = list(methods_limits.keys())
    # Aggregate thickness envelope across methods
    s_mins = [v["s_min"] for v in methods_limits.values()]
    s_maxs = [v["s_max"] for v in methods_limits.values()]
    return {
        "code": code,
        "name": name,
        "joint_type": joint_type,  # butt | corner | lap  (tee не применяется в ГОСТ 16037-80)
        "connection_kind": connection_kind,
        "groove": groove,
        "weld_character": weld_character,
        "methods": methods,
        "methods_limits": methods_limits,
        "thickness_range": {
            "s_min": min(s_mins) if s_mins else None,
            "s_max": max(s_maxs) if s_maxs else None,
        },
        "gost_table": gost_table,
        "gost_table_overview": "1",
        "dimensions": dimensions or [],
        "dimensions_notes": dimensions_notes,
        "sketch": f"techcards/joints/gost_16037/{code}.png",
        "sketch_page_table1": sketch_page,
        "material": "steel_pipeline",
        "notes": notes,
        "uncertain": uncertain or [],
    }


# ---------------------------------------------------------------------------
# Табл. 1 — основные типы (проверено по скану PDF + HTML-тексту стандарта)
# ---------------------------------------------------------------------------
JOINTS: dict[str, dict] = {}

# --- Стыковые: труба–труба / труба–арматура ---
JOINTS["С2"] = _joint(
    "С2",
    name="Стыковое соединение трубы с трубой или с арматурой, без скоса кромок, односторонний",
    joint_type="butt",
    connection_kind="труба с трубой или с арматурой",
    groove="Без скоса кромок",
    weld_character="Односторонний",
    methods_limits=_m(
        zp=((2, 5), 25), zn=((2, 3), 10), r=((2, 5), 25), f=((4, 6), 133), g=((1, 3), 150)
    ),
    gost_table="2",
    sketch_page=3,
    dimensions=[
        {"methods": ["ЗП", "Р"], "s": 2.0, "b_nom": 0.5, "b_tol": "+0,5", "e_nom": 4, "e_tol": "+2"},
        {"methods": ["ЗП", "Р"], "s": 3.0, "b_nom": 1.0, "e_nom": 4},
        {"methods": ["ЗП", "Р"], "s_min": 4.0, "s_max": 5.0, "b_nom": 1.5, "e_nom": 4},
        {"methods": ["Ф"], "s": 4.0, "e_nom": 8},
        {"methods": ["Ф"], "s": 6.0, "e_nom": 10},
        {"methods": ["ЗН"], "s_min": 2.0, "s_max": 3.0, "b_nom": 0, "b_tol": "+0,3"},
        {"methods": ["Г"], "s_min": 1.0, "s_max": 1.6, "b_nom": 0.5, "b_tol": "±0,3", "e_nom": 3, "e_tol": "+1", "g_nom": 0.5, "g_tol": "+0,5"},
        {"methods": ["Г"], "s_min": 2.0, "s_max": 3.0, "b_nom": 1.0, "b_tol": "±0,5", "e_nom": 4, "e_tol": "+2", "g_nom": 1.0, "g_tol": "±0,5"},
    ],
)

JOINTS["С4"] = _joint(
    "С4",
    name="Стыковое соединение трубы с трубой или с арматурой, без скоса кромок, односторонний на съемной подкладке",
    joint_type="butt",
    connection_kind="труба с трубой или с арматурой",
    groove="Без скоса кромок",
    weld_character="Односторонний на съемной подкладке",
    methods_limits=_m(zp=((2, 4), 25), zn=((2, 3), 10), r=((2, 3), 25)),
    gost_table="3",
    sketch_page=3,
    dimensions=[
        {"methods": ["Р", "ЗН"], "s_min": 2, "s_max": 3},
        {"methods": ["ЗП"], "s_min": 2, "s_max": 4},
    ],
    dimensions_notes="Размеры b, e, g — по эскизу табл. 3 (детали в основном на чертеже).",
)

JOINTS["С5"] = _joint(
    "С5",
    name="Стыковое соединение трубы с трубой или с арматурой, без скоса кромок, односторонний на остающейся цилиндрической подкладке",
    joint_type="butt",
    connection_kind="труба с трубой или с арматурой",
    groove="Без скоса кромок",
    weld_character="Односторонний на остающейся цилиндрической подкладке",
    methods_limits=_m(zp=((2, 3), 25), r=((2, 3), 25)),
    gost_table="4",
    sketch_page=3,
    dimensions=[{"methods": ["ЗП", "ЗН", "Р"], "s_min": 2, "s_max": 3}],
    notes="В табл. 1 по скану — ЗП/Р 2–3/25; в табл. 4 также указан ЗН.",
    uncertain=["methods_table4_lists_ЗН: табл.4 указывает ЗП;ЗН;Р при s=2-3"],
)

JOINTS["С8"] = _joint(
    "С8",
    name="Стыковое соединение трубы с трубой или с арматурой, со скосом одной кромки, односторонний",
    joint_type="butt",
    connection_kind="труба с трубой или с арматурой",
    groove="Со скосом одной кромки",
    weld_character="Односторонний",
    methods_limits=_m(zp=((3, 20), 25), r=((3, 20), 25)),
    gost_table="5",
    sketch_page=3,
    dimensions=[
        {"methods": ["ЗП", "Р"], "s": 3, "b_nom": 1, "b_tol": "+0,5", "c_nom": 0.5, "c_tol": "+0,5", "e_nom": 8, "e_tol": "+2", "g_nom": 1.5, "g_tol": "+1,5/-1,0"},
        {"methods": ["ЗП", "Р"], "s": 4, "e_nom": 10},
        {"methods": ["ЗП", "Р"], "s": 5, "e_nom": 11},
        {"methods": ["ЗП", "Р"], "s": 6, "e_nom": 12},
        {"methods": ["ЗП", "Р"], "s": 7, "e_nom": 13, "e_tol": "+3"},
        {"methods": ["ЗП", "Р"], "s": 8, "e_nom": 14, "g_nom": 2.0, "g_tol": "+2,0/-1,5"},
        {"methods": ["ЗП", "Р"], "s": 9, "b_nom": 2, "c_nom": 1.0, "c_tol": "±0,5", "e_nom": 16, "e_tol": "+4"},
        {"methods": ["ЗП", "Р"], "s": 10, "e_nom": 18},
        {"methods": ["ЗП", "Р"], "s": 12, "b_tol": "+1,0", "e_nom": 20},
        {"methods": ["ЗП", "Р"], "s": 14, "e_nom": 22, "e_tol": "+5"},
        {"methods": ["ЗП", "Р"], "s": 16, "e_nom": 25},
        {"methods": ["ЗП", "Р"], "s": 18, "e_nom": 27},
        {"methods": ["ЗП", "Р"], "s": 20, "e_nom": 29, "e_tol": "+7"},
    ],
)

JOINTS["С10"] = _joint(
    "С10",
    name="Стыковое соединение трубы с трубой или с арматурой, со скосом одной кромки, односторонний на остающейся цилиндрической подкладке",
    joint_type="butt",
    connection_kind="труба с трубой или с арматурой",
    groove="Со скосом одной кромки",
    weld_character="Односторонний на остающейся цилиндрической подкладке",
    methods_limits=_m(zp=((2, 20), 25), r=((2, 20), 57)),
    gost_table="6",
    sketch_page=3,
    dimensions=[
        {"methods": ["ЗП", "Р"], "s": 2, "b_nom": 2, "b_tol": "+2", "e_nom": 9, "e_tol": "+2", "g_nom": 1.5, "g_tol": "+1,5/-1,0"},
        {"methods": ["ЗП", "Р"], "s": 3, "e_nom": 10},
        {"methods": ["ЗП", "Р"], "s": 4, "e_nom": 11},
        {"methods": ["ЗП", "Р"], "s": 5, "e_nom": 12, "e_tol": "+3"},
        {"methods": ["ЗП", "Р"], "s": 6, "e_nom": 13},
        {"methods": ["ЗП", "Р"], "s": 7, "e_nom": 14, "e_tol": "+4"},
        {"methods": ["ЗП", "Р"], "s": 8, "b_nom": 4, "e_nom": 16, "g_nom": 2.0, "g_tol": "+2,0/-1,0"},
        {"methods": ["ЗП", "Р"], "s": 9, "e_nom": 18},
        {"methods": ["ЗП", "Р"], "s": 10, "e_nom": 19},
        {"methods": ["ЗП", "Р"], "s": 12, "b_nom": 5, "b_tol": "+2/-1", "e_nom": 21, "e_tol": "+5"},
        {"methods": ["ЗП", "Р"], "s": 14, "e_nom": 23, "e_tol": "+6"},
        {"methods": ["ЗП", "Р"], "s": 16, "e_nom": 26},
        {"methods": ["ЗП", "Р"], "s": 18, "e_nom": 28},
        {"methods": ["ЗП", "Р"], "s": 20, "e_nom": 31, "e_tol": "+7"},
    ],
)

JOINTS["С17"] = _joint(
    "С17",
    name="Стыковое соединение трубы с трубой или с арматурой, со скосом кромок, односторонний",
    joint_type="butt",
    connection_kind="труба с трубой или с арматурой",
    groove="Со скосом кромок (V-образная)",
    weld_character="Односторонний",
    methods_limits=_m(
        zp=((3, 20), 25), zn=((3, 20), 14), r=((3, 20), 25), g=((3, 7), [14, 150])
    ),
    gost_table="7",
    sketch_page=3,
    dimensions_notes="Подробные e/g/b/c по s — в табл. 7 (скан); частично OCR-шум в HTML-источнике.",
    uncertain=["dimensions_rows: числовые ряды e/g для всех s — уточнить по скану табл. 7"],
)

JOINTS["С18"] = _joint(
    "С18",
    name="Стыковое соединение трубы с трубой или с арматурой, со скосом кромок, односторонний на съемной подкладке",
    joint_type="butt",
    connection_kind="труба с трубой или с арматурой",
    groove="Со скосом кромок (V-образная)",
    weld_character="Односторонний на съемной подкладке",
    methods_limits=_m(
        zp=((2, 40), 25), zn=((2, 40), 10), r=((2, 40), 25), f=((6, 40), 377)
    ),
    gost_table="8",
    sketch_page=3,
)

JOINTS["С19"] = _joint(
    "С19",
    name="Стыковое соединение трубы с трубой или с арматурой, со скосом кромок, односторонний на остающейся цилиндрической подкладке",
    joint_type="butt",
    connection_kind="труба с трубой или с арматурой",
    groove="Со скосом кромок (V-образная)",
    weld_character="Односторонний на остающейся цилиндрической подкладке",
    methods_limits=_m(zp=((2, 20), 25), zn=((2, 20), 10), r=((2, 20), 25)),
    gost_table="9",
    sketch_page=3,
)

JOINTS["С46"] = _joint(
    "С46",
    name="Стыковое соединение трубы с трубой или с арматурой, со скосом кромок, односторонний с расплавляемой вставкой",
    joint_type="butt",
    connection_kind="труба с трубой или с арматурой",
    groove="Со скосом кромок",
    weld_character="Односторонний с расплавляемой вставкой",
    methods_limits=_m(zp=((4, 20), 25), zn=((4, 20), 25), r=((4, 20), 25)),
    gost_table="10",
    sketch_page=4,
)

JOINTS["С47"] = _joint(
    "С47",
    name="Стыковое соединение трубы с трубой или с арматурой, с криволинейным скосом кромок, односторонний",
    joint_type="butt",
    connection_kind="труба с трубой или с арматурой",
    groove="С криволинейным скосом кромок",
    weld_character="Односторонний",
    methods_limits=_m(zn=((5, 6), 25)),
    gost_table="11",
    sketch_page=4,
)

JOINTS["С48"] = _joint(
    "С48",
    name="Стыковое соединение трубы с трубой или с арматурой, с криволинейным скосом кромок с расточкой, односторонний",
    joint_type="butt",
    connection_kind="труба с трубой или с арматурой",
    groove="С криволинейным скосом кромок с расточкой",
    weld_character="Односторонний",
    methods_limits=_m(zn=((6, 25), 25)),
    gost_table="12",
    sketch_page=4,
)

JOINTS["С49"] = _joint(
    "С49",
    name="Стыковое соединение трубы с трубой или с арматурой, со скосом кромок с расточкой, односторонний на остающейся цилиндрической подкладке",
    joint_type="butt",
    connection_kind="труба с трубой или с арматурой",
    groove="Со скосом кромок с расточкой",
    weld_character="Односторонний на остающейся цилиндрической подкладке",
    methods_limits=_m(zp=((6, 20), 25), zn=((6, 20), 25), r=((6, 20), 57)),
    gost_table="13",
    sketch_page=4,
)

JOINTS["С50"] = _joint(
    "С50",
    name="Стыковое соединение трубы с трубой или с арматурой, со скосом кромок с расточкой, односторонний на остающейся конической подкладке",
    joint_type="butt",
    connection_kind="труба с трубой или с арматурой",
    groove="Со скосом кромок с расточкой",
    weld_character="Односторонний на остающейся конической подкладке",
    methods_limits=_m(zp=((6, 20), 25), zn=((6, 20), 25), r=((6, 20), 57)),
    gost_table="14",
    sketch_page=4,
    notes="В табл. 1 для С50 пределы толщин в отдельной ячейке не заполнены — наследуют ряд со скосом/расточкой; уточнено по табл. 14 и соседним строкам.",
    uncertain=["methods_limits_table1_empty: пределы S/Dn для С50 в табл.1 без чисел — взяты по контексту/табл.14"],
)

JOINTS["С51"] = _joint(
    "С51",
    name="Стыковое соединение трубы с трубой или с арматурой, со скосом кромок с раздачей",
    joint_type="butt",
    connection_kind="труба с трубой или с арматурой",
    groove="Со скосом кромок с раздачей",
    weld_character="Односторонний (на остающейся конической подкладке — по эскизу табл.1/15)",
    methods_limits=_m(zp=((2, 6), 25), zn=((2, 6), 10)),
    gost_table="15",
    sketch_page=4,
    uncertain=["weld_character: формулировка характера шва в табл.1 для С51 частично общая с С50"],
)

JOINTS["С52"] = _joint(
    "С52",
    name="Стыковое соединение трубы с трубой или с арматурой, с криволинейным скосом кромок с расточкой, односторонний на остающейся цилиндрической подкладке",
    joint_type="butt",
    connection_kind="труба с трубой или с арматурой",
    groove="С криволинейным скосом кромок с расточкой",
    weld_character="Односторонний на остающейся цилиндрической подкладке",
    methods_limits=_m(
        zp=((7, 60), 25), zn=((7, 60), 25), r=((7, 60), 57), f=((7, 60), 377)
    ),
    gost_table="16",
    sketch_page=4,
)

JOINTS["С53"] = _joint(
    "С53",
    name="Стыковое соединение трубы с трубой или с арматурой, с криволинейным скосом кромок с расточкой, односторонний на остающейся цилиндрической подкладке (усиленный ряд)",
    joint_type="butt",
    connection_kind="труба с трубой или с арматурой",
    groove="С криволинейным скосом кромок с расточкой",
    weld_character="Односторонний на остающейся цилиндрической подкладке",
    methods_limits=_m(zp=((16, 60), 68), r=((16, 60), 68), f=((16, 60), 377)),
    gost_table="17",
    sketch_page=4,
    notes="Та же форма кромок/шва, что у С52, но другие пределы S и Dn.",
)

JOINTS["С54"] = _joint(
    "С54",
    name="Стыковое соединение секторов колен (отводов), со скосом кромок, двусторонний",
    joint_type="butt",
    connection_kind="секторы колен (отводов)",
    groove="Со скосом кромок",
    weld_character="Двусторонний",
    methods_limits=_m(zp=((3, 25), 108), r=((3, 25), 108)),
    gost_table="18",
    sketch_page=5,
)

JOINTS["С55"] = _joint(
    "С55",
    name="Стыковое соединение секторов колен (отводов), со скосом кромок, односторонний на съемной подкладке",
    joint_type="butt",
    connection_kind="секторы колен (отводов)",
    groove="Со скосом кромок",
    weld_character="Односторонний на съемной подкладке",
    methods_limits=_m(zp=((3, 25), 108), r=((3, 25), 108)),
    gost_table="19",
    sketch_page=5,
    notes="В табл. 1 числовые пределы для С55 объединены с С54 (ЗП/Р 3–25/108).",
)

JOINTS["С56"] = _joint(
    "С56",
    name="Стыковое соединение фланца с трубой, с двумя несимметричными скосами двух кромок, двусторонний",
    joint_type="butt",
    connection_kind="фланец с трубой",
    groove="С двумя несимметричными скосами двух кромок",
    weld_character="Двусторонний",
    methods_limits=_m(zp=((3, 40), 70), r=((3, 40), 70)),
    gost_table="20",
    sketch_page=5,
)

# --- Нахлёсточные (Н2 в стандарте отсутствует) ---
JOINTS["Н1"] = _joint(
    "Н1",
    name="Нахлесточное соединение промежуточного штуцера или ниппеля с трубой, без скоса кромок, односторонний",
    joint_type="lap",
    connection_kind="промежуточный штуцер или ниппель с трубой",
    groove="Без скоса кромок",
    weld_character="Односторонний",
    methods_limits=_m(
        zp=((2, 5), 14), zn=((2, 5), 10), r=((2, 5), 22), g=((1, 5), [6, 150])
    ),
    gost_table="21",
    sketch_page=5,
    dimensions=[
        {"methods": ["Г"], "s": 1.0, "K": 2},
        {"methods": ["Г"], "s": 1.5, "K": 2},
        {"methods": ["ЗП", "ЗН", "Р", "Г"], "s": 2.0, "K": 3},
        {"methods": ["ЗП", "ЗН", "Р", "Г"], "s": 2.5, "K": 3},
        {"methods": ["ЗП", "ЗН", "Р", "Г"], "s": 3.0, "K": 4},
        {"methods": ["ЗП", "ЗН", "Р", "Г"], "s": 3.5, "K": 5},
        {"methods": ["ЗП", "ЗН", "Р", "Г"], "s": 4.0, "K": 5},
        {"methods": ["ЗП", "ЗН", "Р", "Г"], "s": 5.0, "K": 7},
    ],
    dimensions_notes="Допускается применение штуцеров и ниппелей с фаской (прим. к табл. 21).",
)

JOINTS["Н3"] = _joint(
    "Н3",
    name="Нахлесточное соединение труб с раздачей одного конца трубы, без скоса кромок, односторонний",
    joint_type="lap",
    connection_kind="трубы с раздачей одного конца",
    groove="Без скоса кромок",
    weld_character="Односторонний",
    methods_limits=_m(zp=((2, 20), 14), r=((2, 20), 25), g=((1.6, 7), [14, 150])),
    gost_table="22",
    sketch_page=5,
    dimensions=[
        {
            "methods": ["ЗП", "Р"],
            "s_min": 2,
            "s_max": 20,
            "K": "s+1",
            "B_max_by_Dn": [
                {"dn_max": 32, "B_max": 30},
                {"dn_min": 32, "dn_max": 108, "B_max": 40},
                {"dn_min": 108, "B_max": 50},
            ],
        },
        {"methods": ["Г"], "s_min": 1.6, "s_max": 7.0},
    ],
    notes="Обозначение Н2 в ГОСТ 16037-80 отсутствует (после Н1 сразу Н3).",
)

JOINTS["Н4"] = _joint(
    "Н4",
    name="Нахлесточное соединение труб муфтой, без скоса кромок, односторонний двойной",
    joint_type="lap",
    connection_kind="трубы муфтой",
    groove="Без скоса кромок",
    weld_character="Односторонний двойной",
    methods_limits=_m(zp=((2, 20), 14), r=((2, 20), 25), g=((1.6, 7), [14, 150])),
    gost_table="23",
    sketch_page=6,
    dimensions=[
        {
            "methods": ["ЗП", "Р"],
            "s_min": 2,
            "s_max": 20,
            "K": "1,3s+1",
            "l_by_Dn": [
                {"dn_max": 32, "l": 40},
                {"dn_min": 32, "dn_max": 108, "l": 50},
                {"dn_min": 108, "l": 60},
            ],
            "l_tol": "±5",
        },
        {"methods": ["Г"], "s_min": 1.6, "s_max": 7.0},
    ],
)

# --- Угловые ---
JOINTS["У15"] = _joint(
    "У15",
    name="Угловое соединение фланца или кольца с трубой, со скосом одной кромки, односторонний с раздачей и развальцовкой",
    joint_type="corner",
    connection_kind="фланец или кольцо с трубой",
    groove="Со скосом одной кромки",
    weld_character="Односторонний с раздачей и развальцовкой",
    methods_limits=_m(zp=((2, 12), 14), r=((2, 12), 14)),
    gost_table="24",
    sketch_page=6,
    dimensions=[
        {"methods": ["ЗП", "Р"], "Dn_min": 14, "Dn_max": 25, "f": "K-1", "K_min": 3, "b_max": 0.05},
        {"methods": ["ЗП", "Р"], "Dn_min": 32, "Dn_max": 57, "K_min": 4},
        {"methods": ["ЗП", "Р"], "Dn_min": 76, "Dn_max": 159, "K_min": 5},
        {"methods": ["ЗП", "Р"], "Dn": 194, "K_min": 6},
    ],
    dimensions_notes="Значение K определяется при проектировании (прим. к табл. 24).",
)

JOINTS["У5"] = _joint(
    "У5",
    name="Угловое соединение фланца или кольца с трубой, без скоса кромок, двусторонний",
    joint_type="corner",
    connection_kind="фланец или кольцо с трубой",
    groove="Без скоса кромок",
    weld_character="Двусторонний",
    methods_limits=_m(zp=((2, 15), 14), r=((2, 15), 14)),
    gost_table="25",
    sketch_page=6,
)

JOINTS["У7"] = _joint(
    "У7",
    name="Угловое соединение фланца или кольца с трубой, со скосом одной кромки, двусторонний",
    joint_type="corner",
    connection_kind="фланец или кольцо с трубой",
    groove="Со скосом одной кромки",
    weld_character="Двусторонний",
    methods_limits=_m(zp=((2, 15), 14), r=((2, 15), 14)),
    gost_table="26",
    sketch_page=6,
)

JOINTS["У8"] = _joint(
    "У8",
    name="Угловое соединение фланца или кольца с трубой, с симметричным скосом одной кромки, двусторонний",
    joint_type="corner",
    connection_kind="фланец или кольцо с трубой",
    groove="С симметричным скосом одной кромки",
    weld_character="Двусторонний",
    methods_limits=_m(zp=((2, 15), 14), r=((2, 15), 14)),
    gost_table="27",
    sketch_page=6,
    notes="В табл. 1 числовые пределы для У8 объединены с У7.",
)

JOINTS["У16"] = _joint(
    "У16",
    name="Угловое соединение отростка с трубой равных размеров, без скоса кромок, односторонний",
    joint_type="corner",
    connection_kind="отросток с трубой равных размеров",
    groove="Без скоса кромок",
    weld_character="Односторонний",
    methods_limits=_m(zp=((2, 4), 14), r=((2, 4), 25)),
    gost_table="28",
    sketch_page=7,
)

JOINTS["У17"] = _joint(
    "У17",
    name="Угловое соединение отростка, ответвительного штуцера или приварыша с трубой, без скоса кромок, односторонний",
    joint_type="corner",
    connection_kind="отросток / ответвительный штуцер / приварыш с трубой",
    groove="Без скоса кромок",
    weld_character="Односторонний",
    methods_limits=_m(
        zp=((2, 20), 14), zn=((2, 20), 14), r=((2, 20), 25), g=((1, 7), [14, 150])
    ),
    gost_table="29",
    sketch_page=7,
)

JOINTS["У18"] = _joint(
    "У18",
    name="Угловое соединение отростка, ответвительного штуцера или приварыша с трубой, без скоса кромок, односторонний (ряд 2–25)",
    joint_type="corner",
    connection_kind="отросток / ответвительный штуцер / приварыш с трубой",
    groove="Без скоса кромок",
    weld_character="Односторонний",
    methods_limits=_m(zp=((2, 25), 14), zn=((2, 25), 14), r=((2, 25), 25)),
    gost_table="30",
    sketch_page=7,
    notes="Та же категория, что У17; иные пределы S. Размеры e и g в сечении А–А — при проектировании (п. 12 стандарта).",
)

JOINTS["У19"] = _joint(
    "У19",
    name="Угловое соединение отростка, ответвительного штуцера или приварыша с трубой, со скосом одной кромки, односторонний",
    joint_type="corner",
    connection_kind="отросток / ответвительный штуцер / приварыш с трубой",
    groove="Со скосом одной кромки",
    weld_character="Односторонний",
    methods_limits=_m(zp=((4, 25), 14), zn=((4, 25), 14), r=((4, 25), 25)),
    gost_table="31",
    sketch_page=8,
    notes="Размеры e и g в сечении А–А — при проектировании (п. 12).",
)

JOINTS["У20"] = _joint(
    "У20",
    name="Угловое соединение ответвительного штуцера или приварыша с трубой, со скосом одной кромки, односторонний на цилиндрическом усе",
    joint_type="corner",
    connection_kind="ответвительный штуцер или приварыш с трубой",
    groove="Со скосом одной кромки",
    weld_character="Односторонний на цилиндрическом усе",
    methods_limits=_m(zp=((4, 20), 12), zn=((4, 20), 12), r=((4, 20), 25)),
    gost_table="32",
    sketch_page=8,
)

JOINTS["У21"] = _joint(
    "У21",
    name="Угловое соединение ответвительного штуцера или приварыша с трубой, со скосом одной кромки, односторонний на съемной подкладке",
    joint_type="corner",
    connection_kind="ответвительный штуцер или приварыш с трубой",
    groove="Со скосом одной кромки",
    weld_character="Односторонний на съемной подкладке",
    methods_limits=_m(zp=((4, 20), 12), zn=((4, 20), 12), r=((4, 20), 25)),
    gost_table="33",
    sketch_page=8,
    notes="В табл. 1 пределы для У21 объединены с У20.",
)


# Row bands on table-1 pages: (pdf_page_1based, [(code, y0_frac, y1_frac), ...])
# Fractions of page height for the data rows (below header). Calibrated on 200 dpi renders.
TABLE1_ROW_BANDS: dict[int, list[tuple[str, float, float]]] = {
    3: [
        ("С2", 0.145, 0.245),
        ("С4", 0.245, 0.355),
        ("С5", 0.362, 0.445),
        ("С8", 0.445, 0.505),
        ("С10", 0.505, 0.595),
        ("С17", 0.595, 0.705),
        ("С18", 0.705, 0.825),
        ("С19", 0.825, 0.950),
    ],
    4: [
        ("С46", 0.120, 0.220),
        ("С47", 0.220, 0.305),
        ("С48", 0.305, 0.415),
        ("С49", 0.415, 0.525),
        ("С50", 0.525, 0.610),
        ("С51", 0.610, 0.710),
        ("С52", 0.710, 0.830),
        ("С53", 0.830, 0.955),
    ],
    5: [
        ("С54", 0.115, 0.340),
        ("С55", 0.340, 0.520),
        ("С56", 0.520, 0.680),
        ("Н1", 0.680, 0.815),
        ("Н3", 0.815, 0.955),
    ],
    6: [
        ("Н4", 0.115, 0.300),
        ("У15", 0.300, 0.480),
        ("У5", 0.480, 0.620),
        ("У7", 0.620, 0.760),
        ("У8", 0.760, 0.945),
    ],
    7: [
        ("У16", 0.120, 0.375),
        ("У17", 0.375, 0.655),
        ("У18", 0.655, 0.940),
    ],
    8: [
        ("У19", 0.120, 0.395),
        ("У20", 0.395, 0.655),
        ("У21", 0.655, 0.895),
    ],
}

# Cross-section sketch column (prepared + weld) as width fractions
SKETCH_X = {
    "landscape": (0.42, 0.585),
    "portrait": (0.40, 0.68),
}


def ensure_pages_rendered() -> None:
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(SRC_PDF))
    try:
        for i in range(doc.page_count):
            out = PAGES_DIR / f"page_{i + 1:02d}.png"
            if out.exists() and out.stat().st_size > 1000:
                continue
            mat = fitz.Matrix(200 / 72, 200 / 72)
            pix = doc[i].get_pixmap(matrix=mat, alpha=False)
            pix.save(str(out))
    finally:
        doc.close()


def extract_sketches() -> dict[str, str]:
    """Crop sketch regions from table 1 pages; return code → relative path."""
    SKETCH_DIR.mkdir(parents=True, exist_ok=True)
    saved: dict[str, str] = {}

    for page_no, bands in TABLE1_ROW_BANDS.items():
        img_path = PAGES_DIR / f"page_{page_no:02d}.png"
        im = Image.open(img_path)
        w, h = im.size
        orient = "landscape" if w > h else "portrait"
        x0 = int(w * SKETCH_X[orient][0])
        x1 = int(w * SKETCH_X[orient][1])
        for code, y0f, y1f in bands:
            y0 = int(h * y0f)
            y1 = int(h * y1f)
            crop = im.crop((x0, y0, x1, y1))
            # Slight contrast pad
            out_path = SKETCH_DIR / f"{code}.png"
            crop.save(out_path, optimize=True)
            rel = f"techcards/joints/gost_16037/{code}.png"
            saved[code] = rel
            JOINTS[code]["sketch"] = rel
            JOINTS[code]["sketch_file"] = str(out_path.relative_to(ROOT)).replace("\\", "/")
            JOINTS[code]["sketch_source"] = {
                "page_png": f"_gost16037_pages/page_{page_no:02d}.png",
                "crop_box_px": [x0, y0, x1, y1],
                "note": "Вырезка столбца «Форма поперечного сечения» из табл. 1",
            }
    return saved


def also_save_full_table1_pages() -> None:
    """Copy full table-1 page renders into sketch dir as reference."""
    ref = SKETCH_DIR / "_table1_pages"
    ref.mkdir(parents=True, exist_ok=True)
    for page_no in range(3, 9):
        src = PAGES_DIR / f"page_{page_no:02d}.png"
        if src.exists():
            shutil.copy2(src, ref / f"table1_page_{page_no:02d}.png")


def copy_pdf() -> None:
    DST_PDF.parent.mkdir(parents=True, exist_ok=True)
    if not DST_PDF.exists() or DST_PDF.stat().st_size != SRC_PDF.stat().st_size:
        shutil.copy2(SRC_PDF, DST_PDF)


def build_payload(sketch_map: dict[str, str]) -> dict:
    by_cat = {"butt": [], "corner": [], "tee": [], "lap": []}
    for code, info in JOINTS.items():
        by_cat[info["joint_type"]].append(code)

    # Stable sort: letter then number
    def sort_key(c: str):
        return (c[0], int("".join(ch for ch in c if ch.isdigit()) or 0))

    for k in by_cat:
        by_cat[k] = sorted(by_cat[k], key=sort_key)

    gaps = []
    for code, info in JOINTS.items():
        if info.get("uncertain"):
            gaps.append({"code": code, "items": info["uncertain"]})

    gaps.extend(
        [
            {
                "code": None,
                "items": [
                    "PDF — растровый скан без текстового слоя; числа размерных табл. 5–33 частично восстановлены из HTML-текста стандарта и требуют выборочной сверки со сканом.",
                    "Тавровые соединения (Т*) в ГОСТ 16037-80 не нормируются — только С / У / Н.",
                    "Обозначение Н2 отсутствует в табл. 1 и табл. 21–23 (после Н1 идёт Н3).",
                    "Пропуски в нумерации стыковых (нет С1, С3, С6… С45 и т.п.) — норма для данного ГОСТ (номера из ГОСТ 16037-70 частично исключены).",
                    "Эскизы PNG вырезаны из табл. 1 (столбец поперечных сечений); более крупные эскизы есть в табл. 2–33 на стр. 9–22 PDF.",
                ],
            }
        ]
    )

    return {
        "document": {
            "code": "ГОСТ 16037-80",
            "title": "Соединения сварные стальных трубопроводов. Основные типы, конструктивные элементы и размеры",
            "title_en": "Welded joints in steel pipelines. Main types, design elements and dimensions",
            "replaces": "ГОСТ 16037-70",
            "effective_from": "1981-07-01",
            "source_pdf": str(DST_PDF.relative_to(ROOT)).replace("\\", "/"),
            "source_pdf_original": str(SRC_PDF),
            "edition_note": "Переиздание (май 1999 г.) с Изменением № 1 (ИУС 3-91)",
            "scope": (
                "Сварные соединения трубопроводов из сталей: трубы с трубами и арматурой. "
                "Не распространяется на соединения при изготовлении самих труб из листа/полосы."
            ),
        },
        "welding_processes": WELDING_PROCESSES,
        "dimension_symbols": DIMENSION_SYMBOLS,
        "joint_type_map": {
            "butt": "стыковое (С)",
            "corner": "угловое (У)",
            "lap": "нахлесточное (Н)",
            "tee": "тавровое — не применяется в ГОСТ 16037-80",
        },
        "codes_by_category": {
            "стыковые": by_cat["butt"],
            "угловые": by_cat["corner"],
            "тавровые": by_cat["tee"],
            "нахлёсточные": by_cat["lap"],
        },
        "joint_count": len(JOINTS),
        "JOINT_TYPES": JOINTS,
        "sketches": sketch_map,
        "sketch_dir": str(SKETCH_DIR.relative_to(ROOT)).replace("\\", "/"),
        "gaps_and_uncertain": gaps,
        "notes_for_implementer": [
            "Поля JOINT_TYPES выровнены под gost_59023_2.py: code, name, joint_type, groove, methods, dimensions, sketch, gost_table, material.",
            "methods — коды способов ГОСТ 16037 (ЗП/ЗН/Р/Ф/Г), не коды ГОСТ Р 59023.2.",
            "methods_limits — пределы S и Dn из табл. 1 (числитель/знаменатель).",
            "dimensions — строки из табл. 2–33 где удалось извлечь; иначе пусто + dimensions_notes.",
            "Для UI sketch path: static/" + "techcards/joints/gost_16037/<CODE>.png",
        ],
    }


def main() -> None:
    assert SRC_PDF.exists(), f"Missing source PDF: {SRC_PDF}"
    copy_pdf()
    ensure_pages_rendered()
    sketch_map = extract_sketches()
    also_save_full_table1_pages()
    payload = build_payload(sketch_map)
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("PDF ->", DST_PDF)
    print("JSON ->", OUT_JSON)
    print("Sketches ->", SKETCH_DIR, "count=", len(sketch_map))
    print("Joints=", len(JOINTS))
    for cat, codes in payload["codes_by_category"].items():
        print(f"  {cat}: {len(codes)} -> {', '.join(codes)}")


if __name__ == "__main__":
    main()
