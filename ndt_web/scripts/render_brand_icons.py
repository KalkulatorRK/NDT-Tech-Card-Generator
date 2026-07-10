#!/usr/bin/env python3
"""Render PNG brand icons from app-icon.svg."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

try:
    import cairosvg
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'cairosvg', '-q'])
    import cairosvg

try:
    from PIL import Image
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'Pillow', '-q'])
    from PIL import Image

BRAND_DIR = Path(__file__).resolve().parents[1] / 'static' / 'img' / 'brand'
SVG_PATH = BRAND_DIR / 'app-icon.svg'

OUTPUTS = {
    'app-icon.png': 512,
    'icon-512.png': 512,
    'icon-192.png': 192,
    'apple-touch-icon.png': 180,
    'favicon-32.png': 32,
}


def render_png(size: int) -> bytes:
    return cairosvg.svg2png(
        url=str(SVG_PATH),
        output_width=size,
        output_height=size,
    )


def write_favicon_ico(png_32_path: Path) -> None:
    img = Image.open(png_32_path).convert('RGBA')
    sizes = [(16, 16), (32, 32), (48, 48)]
    icons = [img.resize(s, Image.Resampling.LANCZOS) for s in sizes]
    icons[0].save(
        BRAND_DIR / 'favicon.ico',
        format='ICO',
        sizes=[(i.width, i.height) for i in icons],
        append_images=icons[1:],
    )


def main() -> None:
    for name, size in OUTPUTS.items():
        out = BRAND_DIR / name
        out.write_bytes(render_png(size))
        print(f'  {name} ({size}×{size})')

    write_favicon_ico(BRAND_DIR / 'favicon-32.png')
    print('  favicon.ico')


if __name__ == '__main__':
    print('Rendering brand icons…')
    main()
    print('Done.')
