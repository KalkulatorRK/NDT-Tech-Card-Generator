# -*- coding: utf-8 -*-
"""
Перевырезка эскизов ГОСТ 16037-80 из детальных табл. 2–33 (не из обзорной табл. 1).

Сырой кроп берёт шапку таблицы (оба эскиза + возможный текст шапки),
затем `gost_16037_sketches.refine_dual_sketch` системно оставляет только чертежи.
"""
from __future__ import annotations

import json
from pathlib import Path

import fitz
from PIL import Image

from gost_16037_sketches import refine_dual_sketch

ROOT = Path(__file__).resolve().parent.parent
_CANDIDATE_PDFS = [
    ROOT / 'normative_docs' / 'ГОСТ 16037-80.pdf',
    Path(r'c:\Users\torf1\Downloads\gost_16037-80.pdf'),
]
OUT = ROOT / 'static' / 'techcards' / 'joints' / 'gost_16037'
EXTRACT = Path(__file__).resolve().parent / '_gost_16037_extract.json'
CACHE = ROOT / '_gost16037_inspect' / 'detail_pages'
CACHE.mkdir(parents=True, exist_ok=True)

# PDF page (1-based) → joints on that page (верх → низ)
PAGE_JOINTS: dict[int, list[str]] = {
    9: ['С2', 'С4', 'С5'],
    10: ['С8', 'С10'],
    11: ['С17', 'С18'],
    12: ['С19', 'С46'],
    13: ['С47', 'С48'],
    14: ['С49', 'С50'],
    15: ['С51', 'С52'],
    16: ['С53', 'С54'],
    17: ['С55', 'С56'],
    18: ['Н1', 'Н3', 'Н4'],
    19: ['У15', 'У5', 'У7'],
    20: ['У8', 'У16'],
    21: ['У17', 'У18'],
    22: ['У19', 'У20'],
    23: ['У21'],
}

# Зоны эскизов (ниже текстовых шапок таблиц).
# refine_dual_sketch подчищает боковые колонки и хвосты «Размеры, мм».
SKETCH_BOXES_2 = [
    (0.06, 0.20, 0.54, 0.38),   # верхняя
    (0.06, 0.58, 0.54, 0.76),   # нижняя
]
# Переопределения по страницам (1-based), если общая сетка не попадает в эскизы
PAGE_BOX_OVERRIDES: dict[int, list[tuple[float, float, float, float]]] = {
    9: [
        (0.05, 0.20, 0.55, 0.42),   # С2
        (0.04, 0.56, 0.58, 0.74),   # С4
        (0.06, 0.78, 0.55, 0.95),   # С5
    ],
    12: [
        (0.05, 0.22, 0.55, 0.40),   # С19
        (0.05, 0.58, 0.55, 0.76),   # С46
    ],
}
SKETCH_BOXES_3 = [
    (0.08, 0.24, 0.54, 0.38),
    (0.06, 0.58, 0.56, 0.72),
    (0.08, 0.80, 0.54, 0.94),
]
SKETCH_BOXES_3_ALT = [
    (0.08, 0.10, 0.54, 0.26),
    (0.08, 0.38, 0.54, 0.54),
    (0.08, 0.66, 0.54, 0.82),
]
SKETCH_BOXES_1 = [
    (0.08, 0.16, 0.54, 0.34),
]


def resolve_pdf() -> Path:
    for p in _CANDIDATE_PDFS:
        if p.is_file():
            return p
    # fallback: любой *16037*.pdf в normative_docs
    for p in sorted((ROOT / 'normative_docs').glob('*16037*.pdf')):
        return p
    raise SystemExit('PDF ГОСТ 16037-80 не найден')


def render_page(pdf: fitz.Document, page_1based: int, zoom: float = 2.5) -> Path:
    cache = CACHE / f'p{page_1based:02d}_z{zoom}.png'
    if cache.exists():
        return cache
    page = pdf[page_1based - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    pix.save(str(cache))
    return cache


def crop_frac(img: Image.Image, box: tuple[float, float, float, float]) -> Image.Image:
    w, h = img.size
    x0, y0, x1, y1 = box
    return img.crop((int(w * x0), int(h * y0), int(w * x1), int(h * y1)))


def boxes_for(page_no: int, n: int) -> list[tuple[float, float, float, float]]:
    if page_no in PAGE_BOX_OVERRIDES:
        return PAGE_BOX_OVERRIDES[page_no]
    if n == 1:
        return SKETCH_BOXES_1
    if n == 2:
        return SKETCH_BOXES_2
    if page_no == 9:
        return SKETCH_BOXES_3
    return SKETCH_BOXES_3_ALT


def main() -> None:
    pdf_path = resolve_pdf()
    print('PDF:', pdf_path)
    OUT.mkdir(parents=True, exist_ok=True)
    pdf = fitz.open(str(pdf_path))
    done: dict[str, dict] = {}

    for page_no, codes in PAGE_JOINTS.items():
        if page_no > pdf.page_count:
            print(f'skip page {page_no}: out of range')
            continue
        path = render_page(pdf, page_no)
        img = Image.open(path)
        boxes = boxes_for(page_no, len(codes))
        for code, box in zip(codes, boxes):
            raw = crop_frac(img, box)
            crop = refine_dual_sketch(raw)
            out_path = OUT / f'{code}.png'
            crop.save(out_path, optimize=True)
            done[code] = {
                'file': str(out_path.relative_to(ROOT)).replace('\\', '/'),
                'pdf_page': page_no,
                'crop_frac': list(box),
                'size_px': list(crop.size),
                'bytes': out_path.stat().st_size,
            }
            print(f'OK {code}: {crop.size[0]}x{crop.size[1]} p.{page_no}')

    if EXTRACT.exists():
        data = json.loads(EXTRACT.read_text(encoding='utf-8'))
        sketches = data.setdefault('sketches', {})
        for code, meta in done.items():
            sketches[code] = f'techcards/joints/gost_16037/{code}.png'
            jt = data.get('JOINT_TYPES', {}).get(code)
            if jt is not None:
                jt['sketch'] = sketches[code]
                jt['sketch_file'] = f'static/techcards/joints/gost_16037/{code}.png'
                jt['sketch_source'] = {
                    'pdf_page': meta['pdf_page'],
                    'crop_frac': meta['crop_frac'],
                    'note': (
                        'Эскизы из детальной табл. ГОСТ 16037-80; '
                        'refine_dual_sketch — оба чертежа без текста шапки'
                    ),
                    'size_px': meta['size_px'],
                    'bytes': meta['bytes'],
                }
        data['sketch_count'] = len(sketches)
        data['sketch_dir'] = 'static/techcards/joints/gost_16037'
        EXTRACT.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        print('updated', EXTRACT.name)

    missing = set()
    if EXTRACT.exists():
        data = json.loads(EXTRACT.read_text(encoding='utf-8'))
        missing = set(data.get('JOINT_TYPES', {})) - set(done)
    if missing:
        print('MISSING:', sorted(missing))
    print(f'DONE {len(done)} sketches -> {OUT}')


if __name__ == '__main__':
    main()
