#!/usr/bin/env python3
"""
build_gost_joint_catalog.py

Parses GOST R 59023.2-2020 (meganorm plain-text) and produces:

  normative/gost_59023_table_catalog.py
      - TABLE_CATALOG  : list of dicts, one per table (9.1-9.122)
      - GOST_SECTIONS  : dict, section 5-8 → table-number lists

  normative/gost_59023_extended_joints.py
      - JOINT_TYPES_EXT : dict of joint-code → info, for codes NOT
        already in gost_59023_2.JOINT_TYPES or
        gost_59023_joint_supplement.SUPPLEMENT_JOINT_TYPES
      - MATERIAL_VARIANTS : dict of joint-code → list of material scopes,
        for codes that appear in multiple material sections

Usage:
    python normative/build_gost_joint_catalog.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
SOURCE_FILE = Path("/home/ubuntu/.cursor/projects/workspace/agent-tools/"
                   "9b2c12c9-2849-4711-8ff7-29139a53b196.txt")
OUT_CATALOG = HERE / "gost_59023_table_catalog.py"
OUT_EXTENDED = HERE / "gost_59023_extended_joints.py"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VALID_METHODS: set[str] = {
    "10", "11", "20", "30", "31", "32",
    "40", "42", "51", "52", "53", "60",
}

# Regex patterns
RE_TABLE_HEADER = re.compile(r"^Таблица (9\.\d+)$")
RE_JOINT_CODE   = re.compile(r"^(ТС|ТУ|С|У|Т)-?(\d+(?:-\d+)*)$")
RE_DECIMAL      = re.compile(r"^(\d+)[,.](\d+)$")
RE_RANGE_TEXT   = re.compile(
    r"(?:От|Св\.)\s+([\d,]+)\s+до\s+([\d,]+)"
)

# GOST sections 5-8 table ranges (from the document text, sections 5, 6, 7, 8)
# Section 5: perlit/high-chrome steel
# Section 6: austenite/Fe-Ni
# Section 7: titanium (sheet + tube)
# Section 8: aluminum
GOST_SECTIONS_RAW: dict[str, list[str]] = {
    "section_5_steel": [
        "9.1","9.2","9.3","9.4","9.5","9.6","9.7","9.8","9.9","9.10",
        "9.12","9.13","9.14","9.15","9.16","9.17","9.18","9.19",
        "9.20","9.21","9.22","9.23","9.24","9.25",
        "9.26","9.27","9.28","9.29",
        "9.32","9.33","9.34","9.35","9.36","9.37",
        "9.38","9.39","9.40","9.41","9.42","9.43","9.44","9.45","9.46","9.47","9.48",
        "9.52","9.53","9.54","9.55","9.56","9.57","9.58","9.59","9.60",
        "9.62","9.64","9.65","9.66",
    ],
    "section_6_austenite": [
        "9.1","9.2","9.3","9.4","9.5","9.6","9.7","9.9",
        "9.11","9.12","9.13","9.14","9.15","9.16","9.17","9.18","9.19",
        "9.20","9.21",
        "9.26","9.27","9.28","9.29","9.30",
        "9.31","9.32","9.34",
        "9.38","9.43","9.44",
        "9.49","9.50","9.51","9.52","9.53","9.54","9.55","9.56","9.57","9.58","9.59","9.60",
        "9.61","9.62","9.63","9.64","9.65",
    ],
    "section_7_titanium_sheet": [
        "9.67","9.68","9.69","9.70","9.71","9.72","9.73","9.74","9.75","9.76",
        "9.77","9.78","9.79","9.80","9.81","9.82","9.83","9.84",
    ],
    "section_7_titanium_tube": [
        "9.85","9.86","9.87","9.88","9.89","9.90","9.91","9.92","9.93","9.94",
        "9.95","9.96","9.97","9.98","9.99",
    ],
    "section_8_aluminum": [
        "9.100","9.101","9.102","9.103","9.104","9.105","9.106","9.107","9.108",
        "9.109","9.110","9.111","9.112","9.113","9.114","9.115","9.116","9.117",
        "9.118","9.119","9.120","9.121","9.122",
    ],
}


def _table_number_key(tnum: str) -> float:
    """Sort key for table numbers like '9.10', '9.122'."""
    return float(tnum.replace("9.", ""))


def normalize_code(raw: str) -> str | None:
    """
    Normalize joint code:  С1 → С-1,  ТС1 → ТС-1,  С-1-1 unchanged.
    Returns None if raw does not match a joint-code pattern.
    """
    raw = raw.strip()
    m = RE_JOINT_CODE.match(raw)
    if not m:
        return None
    prefix = m.group(1)
    nums   = m.group(2)          # already hyphen-separated if were hyphens
    # The regex already absorbed any existing hyphen between prefix and nums;
    # nums may still be like "1-1" which is correct.
    return f"{prefix}-{nums}"


def _parse_decimal(s: str) -> float | None:
    """Parse a Russian-locale decimal string like '3,0' or '3.0'."""
    m = RE_DECIMAL.match(s.strip())
    if m:
        return float(f"{m.group(1)}.{m.group(2)}")
    return None


# ---------------------------------------------------------------------------
# Material scope assignment
# ---------------------------------------------------------------------------

def _material_scope_for_table(tnum: str) -> str:
    """Return the primary material scope for a table number."""
    n = _table_number_key(tnum)
    if 67 <= n <= 84:
        return "titanium_sheet"
    if 85 <= n <= 99:
        return "titanium_tube"
    if 100 <= n <= 122:
        return "aluminum"
    return "steel"


# ---------------------------------------------------------------------------
# Document parsing
# ---------------------------------------------------------------------------

def load_lines(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as fh:
        return [line.rstrip() for line in fh]


def find_table_boundaries(lines: list[str]) -> list[tuple[str, int, int]]:
    """
    Returns list of (table_number, start_line, end_line) tuples, sorted by
    table number.  end_line is exclusive (start of next table or EOF).
    """
    headers: list[tuple[str, int]] = []
    for i, line in enumerate(lines):
        m = RE_TABLE_HEADER.match(line.strip())
        if m:
            headers.append((m.group(1), i))

    result = []
    for idx, (tnum, start) in enumerate(headers):
        end = headers[idx + 1][1] if idx + 1 < len(headers) else len(lines)
        result.append((tnum, start, end))

    result.sort(key=lambda x: _table_number_key(x[0]))
    return result


def _extract_s_range(section_lines: list[str],
                     after_last_method_idx: int) -> tuple[float | None, float | None]:
    """
    Best-effort extraction of S_min / S_max from the dimension block of a
    table section.  We scan the lines after the last welding-method line and
    collect decimal values that look like realistic wall-thickness values
    (0.1 … 350 mm).  Avoid tolerance lines (starting with +/- or +).
    """
    s_values: list[float] = []

    # Look for "От X до Y" style range texts first
    full_text = "\n".join(section_lines[after_last_method_idx:])
    for m in RE_RANGE_TEXT.finditer(full_text):
        v1 = _parse_decimal(m.group(1).replace(" ", ""))
        v2 = _parse_decimal(m.group(2).replace(" ", ""))
        if v1 is not None:
            s_values.append(v1)
        if v2 is not None:
            s_values.append(v2)

    # Also scan plain decimal lines
    for line in section_lines[after_last_method_idx:]:
        line = line.strip()
        if line.startswith(("+", "-", "≤", "≥", ">")):
            continue
        v = _parse_decimal(line)
        if v is not None and 0.1 <= v <= 350.0:
            s_values.append(v)

    if not s_values:
        return None, None
    return min(s_values), max(s_values)


def _deduplicate_methods(methods: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for m in methods:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def parse_table(tnum: str, lines: list[str], start: int, end: int) -> dict:
    """
    Parse a single table section.  Returns a dict with keys:
      table, joint_codes, material_scope, methods, s_min, s_max
    """
    section = lines[start:end]
    codes: list[str]   = []
    methods: list[str] = []
    last_method_line   = 0

    # Column-header keywords to skip
    skip_keywords = {
        "Условное", "Конструктивные", "Способ", "подготавливаемых",
        "подготовленных", "шва", "номинальное", "предельное",
        "значение", "отклонение", "элементов", "соединения",
        "кромок", "свариваемых", "деталей", "сварного",
        "Марка", "проволоки", "Сплавы", "сплавы",
    }

    for i, raw_line in enumerate(section):
        line = raw_line.strip()
        if not line:
            continue
        # Skip column header keywords
        if any(kw in line for kw in skip_keywords):
            continue
        nc = normalize_code(line)
        if nc:
            if nc not in codes:
                codes.append(nc)
            continue
        if line in VALID_METHODS:
            methods.append(line)
            last_method_line = i
            continue

    s_min, s_max = _extract_s_range(section, last_method_line)

    return {
        "table":         tnum,
        "joint_codes":   codes,
        "material_scope": _material_scope_for_table(tnum),
        "methods":       _deduplicate_methods(methods),
        "s_min":         s_min,
        "s_max":         s_max,
    }


# ---------------------------------------------------------------------------
# Main parsing pipeline
# ---------------------------------------------------------------------------

def build_catalog(lines: list[str]) -> list[dict]:
    boundaries = find_table_boundaries(lines)
    catalog: list[dict] = []
    for tnum, start, end in boundaries:
        entry = parse_table(tnum, lines, start, end)
        catalog.append(entry)
    return catalog


# ---------------------------------------------------------------------------
# Determine which codes are new (not in existing modules)
# ---------------------------------------------------------------------------

def load_existing_codes() -> set[str]:
    """Load all codes already in gost_59023_2 and gost_59023_joint_supplement."""
    sys.path.insert(0, str(HERE.parent))
    try:
        from normative.gost_59023_2 import JOINT_TYPES
        from normative.gost_59023_joint_supplement import SUPPLEMENT_JOINT_TYPES
        return set(JOINT_TYPES.keys()) | set(SUPPLEMENT_JOINT_TYPES.keys())
    except ImportError as exc:
        print(f"WARNING: could not import existing modules: {exc}", file=sys.stderr)
        return set()


# ---------------------------------------------------------------------------
# Build MATERIAL_VARIANTS
# ---------------------------------------------------------------------------

def build_material_variants(catalog: list[dict]) -> dict[str, list[str]]:
    """
    Returns dict: joint_code → list of material scopes in which it appears.
    Only codes appearing in 2+ distinct scopes are included.
    """
    code_scopes: dict[str, list[str]] = {}
    for entry in catalog:
        scope = entry["material_scope"]
        for code in entry["joint_codes"]:
            code_scopes.setdefault(code, [])
            if scope not in code_scopes[code]:
                code_scopes[code].append(scope)

    return {
        code: sorted(scopes)
        for code, scopes in code_scopes.items()
        if len(scopes) >= 2
    }


# ---------------------------------------------------------------------------
# Joint type description helpers
# ---------------------------------------------------------------------------

_JOINT_TYPE_MAP = {
    "С": "butt",
    "У": "corner",
    "Т": "tee",
    "ТС": "butt",
    "ТУ": "corner",
}

_MATERIAL_LABEL = {
    "steel": "perlit",
    "titanium_sheet": "titanium",
    "titanium_tube": "titanium",
    "aluminum": "aluminum",
}

_GROOVE_HINTS: dict[str, str] = {
    "steel":           "По таблице ГОСТ Р 59023.2-2020",
    "titanium_sheet":  "Для листовых деталей из Ti-сплавов",
    "titanium_tube":   "Для трубных деталей из Ti-сплавов",
    "aluminum":        "Для деталей из Al-сплавов",
}


def _joint_type_key(code: str) -> str:
    for prefix in ("ТС", "ТУ", "С", "У", "Т"):
        if code.startswith(prefix):
            return _JOINT_TYPE_MAP.get(prefix, "butt")
    return "butt"


def build_new_joint_entries(
    catalog: list[dict],
    existing_codes: set[str],
) -> dict[str, dict]:
    """
    For each joint code in the catalog that is NOT in existing_codes,
    build a minimal JOINT_TYPES-style entry.
    """
    # Collect all tables for each code (for table list and methods)
    code_tables:  dict[str, list[str]] = {}
    code_methods: dict[str, list[str]] = {}
    code_scope:   dict[str, str]       = {}

    for entry in catalog:
        scope = entry["material_scope"]
        for code in entry["joint_codes"]:
            if code in existing_codes:
                continue
            code_tables.setdefault(code, [])
            code_methods.setdefault(code, [])
            if entry["table"] not in code_tables[code]:
                code_tables[code].append(entry["table"])
            for m in entry["methods"]:
                if m not in code_methods[code]:
                    code_methods[code].append(m)
            # Primary scope: pick the first one (may appear in multiple)
            if code not in code_scope:
                code_scope[code] = scope

    # Fallback: titanium tube codes with no parsed methods default to 51+52.
    # Table 9.87 (ТС-4, ТС-5) has combined cell formatting in the source that
    # makes method codes invisible to the plain-text parser.
    for code in list(code_methods.keys()):
        scope = code_scope.get(code, "steel")
        if scope == "titanium_tube" and not code_methods[code]:
            code_methods[code] = ["51", "52"]

    result: dict[str, dict] = {}
    for code in sorted(code_tables.keys()):
        tables = code_tables[code]
        primary_table = tables[0] if tables else "?"
        scope = code_scope.get(code, "steel")
        result[code] = {
            "code":       code,
            "name":       f"Сварное соединение {code} "
                          f"(ГОСТ Р 59023.2-2020, табл. {primary_table})",
            "joint_type": _joint_type_key(code),
            "material":   _MATERIAL_LABEL.get(scope, "perlit"),
            "groove":     _GROOVE_HINTS.get(scope, "По таблице ГОСТ Р 59023.2-2020"),
            "methods":    code_methods.get(code, []),
            "sketch":     "",
            "gost_table": primary_table,
            "bead_mode":  "equal",
            "gost_tables_all": tables,
            "dimensions": [],
        }

    return result


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _py_repr(obj, indent: int = 0) -> str:
    """Simple recursive repr for lists/dicts/scalars as pretty Python literals."""
    pad  = "    " * indent
    pad1 = "    " * (indent + 1)

    if isinstance(obj, dict):
        if not obj:
            return "{}"
        lines = ["{"]
        for k, v in obj.items():
            lines.append(f"{pad1}{k!r}: {_py_repr(v, indent + 1)},")
        lines.append(f"{pad}}}")
        return "\n".join(lines)

    if isinstance(obj, list):
        if not obj:
            return "[]"
        if all(not isinstance(x, (dict, list)) for x in obj):
            # Compact one-liner for simple lists
            return repr(obj)
        lines = ["["]
        for item in obj:
            lines.append(f"{pad1}{_py_repr(item, indent + 1)},")
        lines.append(f"{pad}]")
        return "\n".join(lines)

    return repr(obj)


# ---------------------------------------------------------------------------
# Write gost_59023_table_catalog.py
# ---------------------------------------------------------------------------

def write_catalog_file(catalog: list[dict], gost_sections: dict) -> None:
    lines: list[str] = [
        '"""',
        "gost_59023_table_catalog.py — auto-generated by build_gost_joint_catalog.py",
        "",
        "Contains:",
        "  TABLE_CATALOG  — list of dicts, one per table 9.1–9.122",
        "  GOST_SECTIONS  — dict of section name → list of table numbers",
        '"""',
        "from __future__ import annotations",
        "",
        "# fmt: off",
        "",
    ]

    # TABLE_CATALOG
    lines.append("TABLE_CATALOG: list[dict] = [")
    for entry in catalog:
        lines.append("    {")
        lines.append(f"        'table':         {entry['table']!r},")
        lines.append(f"        'joint_codes':   {entry['joint_codes']!r},")
        lines.append(f"        'material_scope': {entry['material_scope']!r},")
        lines.append(f"        'methods':       {entry['methods']!r},")
        s_min = entry["s_min"]
        s_max = entry["s_max"]
        lines.append(f"        's_min':         {s_min!r},")
        lines.append(f"        's_max':         {s_max!r},")
        lines.append("    },")
    lines.append("]")
    lines.append("")

    # GOST_SECTIONS
    lines.append("")
    lines.append("GOST_SECTIONS: dict[str, list[str]] = {")
    for sec_name, table_list in gost_sections.items():
        lines.append(f"    {sec_name!r}: {table_list!r},")
    lines.append("}")
    lines.append("")

    OUT_CATALOG.write_text("\n".join(lines), encoding="utf-8")
    print(f"  → wrote {OUT_CATALOG}")


# ---------------------------------------------------------------------------
# Write gost_59023_extended_joints.py
# ---------------------------------------------------------------------------

def write_extended_file(
    new_joints: dict[str, dict],
    material_variants: dict[str, list[str]],
) -> None:
    lines: list[str] = [
        '"""',
        "gost_59023_extended_joints.py — auto-generated by build_gost_joint_catalog.py",
        "",
        "Contains:",
        "  JOINT_TYPES_EXT   — joint codes NOT in gost_59023_2.JOINT_TYPES",
        "                      or gost_59023_joint_supplement.SUPPLEMENT_JOINT_TYPES",
        "  MATERIAL_VARIANTS — codes that appear in multiple material scopes",
        '"""',
        "from __future__ import annotations",
        "",
        "# fmt: off",
        "",
    ]

    # JOINT_TYPES_EXT
    lines.append("JOINT_TYPES_EXT: dict[str, dict] = {")
    for code, info in sorted(new_joints.items()):
        lines.append(f"    {code!r}: {{")
        lines.append(f"        'code':           {info['code']!r},")
        lines.append(f"        'name':           {info['name']!r},")
        lines.append(f"        'joint_type':     {info['joint_type']!r},")
        lines.append(f"        'material':       {info['material']!r},")
        lines.append(f"        'groove':         {info['groove']!r},")
        lines.append(f"        'methods':        {info['methods']!r},")
        lines.append(f"        'sketch':         {info['sketch']!r},")
        lines.append(f"        'gost_table':     {info['gost_table']!r},")
        lines.append(f"        'gost_tables_all': {info['gost_tables_all']!r},")
        lines.append(f"        'bead_mode':      {info['bead_mode']!r},")
        lines.append(f"        'dimensions':     {info['dimensions']!r},")
        lines.append("    },")
    lines.append("}")
    lines.append("")

    # MATERIAL_VARIANTS
    lines.append("")
    lines.append("# Codes that appear with the same name in multiple material sections.")
    lines.append("# key → list of material scopes (steel / titanium_sheet / titanium_tube / aluminum)")
    lines.append("MATERIAL_VARIANTS: dict[str, list[str]] = {")
    for code in sorted(material_variants.keys()):
        scopes = material_variants[code]
        lines.append(f"    {code!r}: {scopes!r},")
    lines.append("}")
    lines.append("")

    OUT_EXTENDED.write_text("\n".join(lines), encoding="utf-8")
    print(f"  → wrote {OUT_EXTENDED}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"Reading {SOURCE_FILE} …")
    lines = load_lines(SOURCE_FILE)
    print(f"  {len(lines)} lines loaded.")

    print("Parsing tables …")
    catalog = build_catalog(lines)
    print(f"  {len(catalog)} tables parsed.")

    print("Loading existing joint codes …")
    existing_codes = load_existing_codes()
    print(f"  {len(existing_codes)} existing codes found.")

    print("Building material variants …")
    material_variants = build_material_variants(catalog)
    print(f"  {len(material_variants)} codes with material variants.")

    print("Building new joint entries …")
    new_joints = build_new_joint_entries(catalog, existing_codes)
    print(f"  {len(new_joints)} new unique codes found.")

    # Collect unique codes across all tables
    all_codes: set[str] = set()
    for entry in catalog:
        all_codes.update(entry["joint_codes"])
    print(f"  {len(all_codes)} total unique codes across all tables.")

    print(f"\nWriting output files …")
    write_catalog_file(catalog, GOST_SECTIONS_RAW)
    write_extended_file(new_joints, material_variants)

    # ---- Summary ----
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total tables parsed    : {len(catalog)}")
    print(f"  Total unique codes     : {len(all_codes)}")
    print(f"  New codes (not in existing modules): {len(new_joints)}")
    print(f"    {sorted(new_joints.keys())}")
    print(f"  Codes with material variants: {len(material_variants)}")
    for code, scopes in sorted(material_variants.items()):
        print(f"    {code}: {scopes}")
    print("=" * 60)


if __name__ == "__main__":
    main()
