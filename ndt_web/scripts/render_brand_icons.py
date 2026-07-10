#!/usr/bin/env python3
"""Render PNG brand icons matching app-icon.svg geometry (PIL)."""

from __future__ import annotations

import io
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    import subprocess

    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'Pillow', '-q'])
    from PIL import Image, ImageDraw

BRAND_DIR = Path(__file__).resolve().parents[1] / 'static' / 'img' / 'brand'

OUTPUTS = {
    'app-icon.png': 512,
    'icon-512.png': 512,
    'icon-192.png': 192,
    'apple-touch-icon.png': 180,
    'favicon-32.png': 32,
}

STROKE = (21, 34, 56, 255)
WHITE = (255, 255, 255, 255)

TILES = [
    {
        'faces': [
            ([(-74, -24), (-8, -56), (-8, -8), (-74, 24)], (234, 67, 53)),
            ([(-8, -56), (0, -60), (0, -12), (-8, -8)], (197, 34, 31)),
            ([(-74, 24), (-8, -8), (0, -12), (-66, 20)], (217, 48, 37)),
        ],
    },
    {
        'faces': [
            ([(8, -56), (74, -24), (74, 24), (8, -8)], (66, 133, 244)),
            ([(74, -24), (82, -28), (82, 20), (74, 24)], (25, 103, 210)),
            ([(8, -8), (74, 24), (82, 20), (16, -12)], (43, 113, 217)),
        ],
    },
    {
        'faces': [
            ([(-74, 24), (-8, -8), (-8, 40), (-74, 72)], (52, 168, 83)),
            ([(-8, -8), (0, -12), (0, 36), (-8, 40)], (24, 128, 56)),
            ([(-74, 72), (-8, 40), (0, 36), (-66, 68)], (30, 142, 62)),
        ],
    },
    {
        'faces': [
            ([(8, -8), (74, 24), (74, 72), (8, 40)], (251, 188, 5)),
            ([(74, 24), (82, 20), (82, 68), (74, 72)], (227, 116, 0)),
            ([(8, 40), (74, 72), (82, 68), (16, 36)], (249, 171, 0)),
        ],
    },
]


def _scale(value: float, size: int) -> float:
    return value * size / 512


def _pt(x: float, y: float, cx: float, cy: float, size: int) -> tuple[float, float]:
    return cx + _scale(x, size), cy + _scale(y, size)


def _poly(draw: ImageDraw.ImageDraw, pts, fill, outline=None, width=1) -> None:
    draw.polygon(pts, fill=fill, outline=outline, width=width)


def render_logo(size: int) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, 'RGBA')
    cx, cy = size / 2, _scale(278, size)
    sw = max(1, round(_scale(4, size)))
    sw_top = max(1, round(_scale(5, size)))
    sw_tile = max(1, round(_scale(2.5, size)))

    def P(x, y):
        return _pt(x, y, cx, cy, size)

    _poly(draw, [P(0, 76), P(94, 123), P(94, 173), P(0, 126)], (66, 133, 244), STROKE, sw)
    _poly(draw, [P(-124, 76), P(0, 26), P(124, 76), P(0, 126)], (174, 203, 250), STROKE, sw)

    _poly(draw, [P(0, 38), P(94, 85), P(94, 135), P(0, 88)], (24, 90, 188), STROKE, sw)
    _poly(draw, [P(-124, 38), P(0, -12), P(124, 38), P(0, 88)], (66, 133, 244), STROKE, sw)

    _poly(draw, [P(0, 0), P(94, 47), P(94, 97), P(0, 50)], (189, 193, 198), STROKE, sw)
    _poly(draw, [P(-124, 0), P(0, -50), P(124, 0), P(0, 50)], WHITE, STROKE, sw_top)

    for tile in TILES:
        for face_pts, color in tile['faces']:
            _poly(draw, [P(x, y) for x, y in face_pts], color + (255,), STROKE, sw_tile)

    _poly(draw, [P(-8, -56), P(8, -56), P(8, 40), P(-8, 40)], WHITE)
    _poly(draw, [P(-74, -8), P(74, -8), P(74, 8), P(-74, 8)], WHITE)
    draw.line([P(-8, -56), P(8, -56), P(8, 40), P(-8, 40), P(-8, -56)], fill=STROKE, width=max(1, round(_scale(2, size))))
    draw.line([P(-74, -8), P(74, -8), P(74, 8), P(-74, 8), P(-74, -8)], fill=STROKE, width=max(1, round(_scale(2, size))))

    return img


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
        render_logo(size).save(out, 'PNG')
        print(f'  {name} ({size}x{size})')

    write_favicon_ico(BRAND_DIR / 'favicon-32.png')
    print('  favicon.ico')


if __name__ == '__main__':
    print('Rendering brand icons…')
    main()
    print('Done.')
