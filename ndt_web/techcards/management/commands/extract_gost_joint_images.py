"""
Извлечение изображений швов в разрезе из RTF ГОСТ Р 59023.2-2020.

Берёт рисунки из столбца «шва сварного соединения» (не из столбца
«подготовленных кромок свариваемых деталей») таблиц раздела 9.

Сохраняет файлы в static/img/welds/gost/.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

RTF_NAME = (
    'ГОСТ Р 59023.2-2020 Сварка и наплавка оборудования и трубопроводов '
    'атомных энергетических..._Текст.rtf'
)

JOINT_CODE_RE = re.compile(r'(?:ТС|ТУ|[СУТ])-?\d+(?:-\d+)?')


def normalize_joint_code(raw: str, known_codes: frozenset[str]) -> str | None:
    """
    Приводит обозначение из RTF к каноническому виду (С32 → С-32, С1-2 → С-1-2).

    Принимает только коды из каталога JOINT_TYPES, отсекая марки сплавов (Т1-0 и т.п.).
    """
    raw = raw.strip()
    if raw in known_codes:
        return raw

    m = re.match(r'^(ТС|ТУ|[СУТ])-(\d+(?:-\d+)?)$', raw)
    if m:
        candidate = raw
        if candidate in known_codes:
            return candidate

    m = re.match(r'^(ТС|ТУ|[СУТ])(\d+(?:-\d+)?)$', raw)
    if m:
        candidate = f'{m.group(1)}-{m.group(2)}'
        if candidate in known_codes:
            return candidate

    m = re.match(r'^(ТС|ТУ|[СУТ])(\d+)$', raw)
    if m:
        prefix, digits = m.group(1), m.group(2)
        for split_at in range(1, len(digits)):
            candidate = f'{prefix}-{digits[:split_at]}-{digits[split_at:]}'
            if candidate in known_codes:
                return candidate
        candidate = f'{prefix}-{digits}'
        if candidate in known_codes:
            return candidate

    return None


def find_joint_code_in_cells(cells: list[bytes], known_codes: frozenset[str]) -> str | None:
    for cell in cells:
        text = _rtf_cell_text(cell)
        for match in JOINT_CODE_RE.finditer(text):
            code = normalize_joint_code(match.group(0), known_codes)
            if code:
                return code
    return None


def _rtf_cell_text(raw: bytes) -> str:
    def repl(match: re.Match) -> bytes:
        return bytes([int(match.group(1), 16)])

    s = re.sub(rb"\\'([0-9a-fA-F]{2})", repl, raw)
    s = re.sub(rb'\\[a-z]+-?\d*\s?', b'', s)
    s = s.replace(b'{', b'').replace(b'}', b'')
    return s.decode('cp1251', errors='replace')


def _extract_image_from_cell(cell_bytes: bytes) -> tuple[str, bytes] | None:
    if b'\\pngblip' in cell_bytes:
        idx = cell_bytes.find(b'\\pngblip')
        match = re.search(rb'([0-9A-Fa-f]{100,})', cell_bytes[idx:])
        if match:
            hex_clean = re.sub(rb'[^0-9A-Fa-f]', b'', match.group(1))
            try:
                raw = bytes.fromhex(hex_clean.decode('ascii'))
                if raw.startswith(b'\x89PNG'):
                    return 'png', raw
            except ValueError:
                pass

    match = re.search(rb'47494638[0-9A-Fa-f]{100,}', cell_bytes)
    if match:
        hex_clean = re.sub(rb'[^0-9A-Fa-f]', b'', match.group(0))
        try:
            raw = bytes.fromhex(hex_clean.decode('ascii'))
            if raw.startswith(b'GIF'):
                return 'gif', raw
        except ValueError:
            pass
    return None


def _find_weld_column_indices(cells: list[bytes]) -> tuple[int | None, int | None]:
    """Определяет индексы столбцов кромок и шва в разрезе по заголовку таблицы."""
    edge_idx = weld_idx = None
    for i, cell in enumerate(cells):
        text = _rtf_cell_text(cell).lower().replace('\n', ' ')
        if 'кромок' in text and 'свар' in text:
            edge_idx = i
        if 'шва свар' in text or ('шва' in text and 'соеди' in text):
            weld_idx = i
    if edge_idx is not None and weld_idx is None:
        weld_idx = edge_idx + 1
    return edge_idx, weld_idx


def _list_cell_images(cells: list[bytes]) -> list[tuple[int, tuple[str, bytes]]]:
    """Ячейки строки, содержащие рисунок: (индекс, (fmt, bytes))."""
    found: list[tuple[int, tuple[str, bytes]]] = []
    for i, cell in enumerate(cells):
        img = _extract_image_from_cell(cell)
        if img:
            found.append((i, img))
    return found


def _pick_weld_seam_image(
    cells: list[bytes],
    weld_col_idx: int | None,
    edge_col_idx: int | None,
) -> tuple[str, bytes] | None:
    """
    Рисунок из столбца «шва сварного соединения» (готовый шов, g/g1).

    Не брать столбец подготовки кромок и не выбирать «самый большой» GIF —
    у кромок файл часто крупнее и перетирал правильный эскиз шва.
    """
    image_cells = _list_cell_images(cells)
    if not image_cells:
        return None

    # 1) Два соседних рисунка в строке ГОСТ: слева кромки, справа шов с g/g1
    for k in range(len(image_cells) - 1):
        i0 = image_cells[k][0]
        i1, img1 = image_cells[k + 1]
        if i1 == i0 + 1:
            return img1

    # 2) Точный индекс столбца шва по заголовку таблицы
    if weld_col_idx is not None and 0 <= weld_col_idx < len(cells):
        img = _extract_image_from_cell(cells[weld_col_idx])
        if img:
            return img

    # 3) Единственный рисунок — только если это не столбец кромок
    only_i, only_img = image_cells[0]
    if edge_col_idx is not None and only_i == edge_col_idx:
        return None
    if len(image_cells) == 1:
        return only_img

    # 4) Несколько несоседних — второй рисунок в строке (правее кромок)
    return image_cells[1][1]


def extract_joint_images(
    rtf_path: Path,
    out_dir: Path,
    known_codes: frozenset[str] | None = None,
) -> dict[str, str]:
    """
    Извлекает эскизы шва в разрезе для каждого условного обозначения.

    :return: {код_шва: относительный путь от static/img/welds/}
    """
    if known_codes is None:
        from normative.gost_59023_2 import ALL_JOINT_CODES
        known_codes = frozenset(ALL_JOINT_CODES)

    data = rtf_path.read_bytes()
    rows = data.split(b'\\row')
    weld_col_idx: int | None = None
    edge_col_idx: int | None = None
    # Первый удачный эскиз шва для кода; не перетирать «более крупным» из кромок
    extracted: dict[str, tuple[str, bytes]] = {}

    for row in rows:
        cells = row.split(b'\\cell')
        edge_idx, weld_idx = _find_weld_column_indices(cells)
        if edge_idx is not None:
            edge_col_idx = edge_idx
            weld_col_idx = weld_idx
            continue

        if weld_col_idx is None and edge_col_idx is None:
            continue

        joint_code = find_joint_code_in_cells(cells, known_codes)
        if not joint_code or joint_code in extracted:
            continue

        image = _pick_weld_seam_image(cells, weld_col_idx, edge_col_idx)
        if not image:
            continue

        extracted[joint_code] = image

    out_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    for code, (fmt, raw) in extracted.items():
        filename = code.replace('-', '_') + f'.{fmt}'
        (out_dir / filename).write_bytes(raw)
        mapping[code] = f'gost/{filename}'

    return mapping


class Command(BaseCommand):
    help = (
        'Извлечь изображения швов в разрезе (столбец «шва сварного соединения») '
        'из RTF ГОСТ Р 59023.2-2020'
    )

    def handle(self, *args, **options):
        base = Path(settings.BASE_DIR)
        rtf_path = base / 'normative_docs' / RTF_NAME
        out_dir = base / 'static' / 'img' / 'welds' / 'gost'

        if not rtf_path.exists():
            self.stderr.write(self.style.ERROR(f'RTF не найден: {rtf_path}'))
            return

        mapping = extract_joint_images(rtf_path, out_dir)
        self.stdout.write(self.style.SUCCESS(
            f'Извлечено {len(mapping)} изображений швов в разрезе -> {out_dir}'
        ))
        for code in sorted(mapping):
            self.stdout.write(f'  {code} -> {mapping[code]}')
