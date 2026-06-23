"""
Извлечение изображений конструктивных элементов швов из RTF ГОСТ Р 59023.2-2020.

Сохраняет файлы в static/img/welds/gost/ для отображения в мастере техкарты.
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


def _rtf_bytes_to_text(raw: bytes) -> str:
    def repl(match: re.Match) -> bytes:
        return bytes([int(match.group(1), 16)])

    stripped = re.sub(rb'\\pict[^}]*?(?=\\cell|\\row)', b'', raw, flags=re.DOTALL)
    s = re.sub(rb"\\'([0-9a-fA-F]{2})", repl, stripped)
    s = re.sub(rb'\\cell\b', b'|', s)
    s = re.sub(rb'\\row\b', b'\n', s)
    s = re.sub(rb'\\[a-z]+-?\d*\s?', b'', s)
    s = s.replace(b'{', b'').replace(b'}', b'')
    return s.decode('cp1251', errors='replace')


def _extract_image(row_bytes: bytes) -> tuple[str, bytes] | None:
    if b'\\pngblip' in row_bytes:
        idx = row_bytes.find(b'\\pngblip')
        rest = row_bytes[idx:]
        match = re.search(rb'([0-9A-Fa-f]{100,})', rest)
        if match:
            hex_clean = re.sub(rb'[^0-9A-Fa-f]', b'', match.group(1))
            try:
                raw = bytes.fromhex(hex_clean.decode('ascii'))
                if raw.startswith(b'\x89PNG'):
                    return 'png', raw
            except ValueError:
                pass

    match = re.search(rb'47494638[0-9A-Fa-f]{100,}', row_bytes)
    if match:
        hex_clean = re.sub(rb'[^0-9A-Fa-f]', b'', match.group(0))
        try:
            raw = bytes.fromhex(hex_clean.decode('ascii'))
            if raw.startswith(b'GIF'):
                return 'gif', raw
        except ValueError:
            pass
    return None


def extract_joint_images(rtf_path: Path, out_dir: Path) -> dict[str, str]:
    """Возвращает {код_шва: относительный путь от static/img/welds/}."""
    data = rtf_path.read_bytes()
    rows = data.split(b'\\row')
    extracted: dict[str, tuple[str, bytes]] = {}

    for i, row in enumerate(rows):
        image = _extract_image(row)
        if not image:
            continue
        combined = row + (rows[i + 1] if i + 1 < len(rows) else b'')
        text = _rtf_bytes_to_text(combined)
        codes = re.findall(r'([СУТ]-\d+(?:-\d+)?)', text)
        if not codes:
            continue
        code = codes[0]
        fmt, raw = image
        if code not in extracted or len(raw) > len(extracted[code][1]):
            extracted[code] = (fmt, raw)

    out_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    for code, (fmt, raw) in extracted.items():
        filename = code.replace('-', '_') + f'.{fmt}'
        (out_dir / filename).write_bytes(raw)
        mapping[code] = f'gost/{filename}'
    return mapping


class Command(BaseCommand):
    help = 'Извлечь изображения типов швов из RTF ГОСТ Р 59023.2-2020'

    def handle(self, *args, **options):
        base = Path(settings.BASE_DIR)
        rtf_path = base / 'normative_docs' / RTF_NAME
        out_dir = base / 'static' / 'img' / 'welds' / 'gost'

        if not rtf_path.exists():
            self.stderr.write(self.style.ERROR(f'RTF не найден: {rtf_path}'))
            return

        mapping = extract_joint_images(rtf_path, out_dir)
        self.stdout.write(self.style.SUCCESS(
            f'Извлечено {len(mapping)} изображений в {out_dir}'
        ))
        for code in sorted(mapping):
            self.stdout.write(f'  {code} -> {mapping[code]}')
