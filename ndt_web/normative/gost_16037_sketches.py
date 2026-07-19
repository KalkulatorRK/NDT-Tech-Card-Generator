# -*- coding: utf-8 -*-
"""
Системная подготовка эскизов ГОСТ 16037-80.

Принцип (для всех типов соединений):
1. В кадре — оба чертежа: подготовленные кромки + сварной шов.
2. Без текста шапки/подвала таблицы.
3. Без колонок обозначения и «Способ сварки», если там нет штриховки.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

_INK = 200


def _rows(im: Image.Image) -> tuple[list[list[bool]], int, int]:
    gray = im.convert('L')
    w, h = gray.size
    data = list(gray.getdata())
    rows = [[data[y * w + x] < _INK for x in range(w)] for y in range(h)]
    return rows, w, h


def _side_hatch(rows: list[list[bool]], w: int, h: int) -> tuple[list[float], list[float]]:
    mid = w // 2
    left = [0.0] * h
    right = [0.0] * h
    for y in range(h - 1):
        r0, r1 = rows[y], rows[y + 1]
        hl = hr = 0
        for x in range(0, mid - 1, 2):
            if r0[x] and r1[x + 1]:
                hl += 1
            if r0[x + 1] and r1[x]:
                hl += 1
        for x in range(mid, w - 1, 2):
            if r0[x] and r1[x + 1]:
                hr += 1
            if r0[x + 1] and r1[x]:
                hr += 1
        left[y] = float(hl)
        right[y] = float(hr)
    return left, right


def _smooth(prof: list[float], radius: int) -> list[float]:
    h = len(prof)
    out = [0.0] * h
    for i in range(h):
        a = max(0, i - radius)
        b = min(h, i + radius + 1)
        out[i] = sum(prof[a:b]) / (b - a)
    return out


def _hatch_ok(im: Image.Image, min_side: float = 40.0) -> bool:
    rows, w, h = _rows(im)
    if w < 40 or h < 40:
        return False
    hl, hr = _side_hatch(rows, w, h)
    return sum(hl) >= min_side and sum(hr) >= min_side


def _content_x(rows: list[list[bool]], w: int, y0: int, y1: int) -> tuple[int, int]:
    band_h = max(1, y1 - y0)
    cols = [sum(rows[y][x] for y in range(y0, y1)) for x in range(w)]
    xs = [i for i, n in enumerate(cols) if n > max(6, int(band_h * 0.04))]
    if not xs:
        return 0, w
    return xs[0], xs[-1] + 1


def _drop_low_hatch_sides(
    rows: list[list[bool]],
    w: int,
    y0: int,
    y1: int,
    x0: int,
    x1: int,
) -> tuple[int, int]:
    band_h = max(1, y1 - y0)
    cols = [sum(rows[y][x] for y in range(y0, y1)) for x in range(w)]
    thr = int(band_h * 0.40)
    seps: list[int] = []
    x = x0
    while x < x1:
        if cols[x] >= thr:
            a = x
            while x < x1 and cols[x] >= thr:
                x += 1
            seps.append((a + x - 1) // 2)
        else:
            x += 1
    cleaned: list[int] = []
    for s in seps:
        if not cleaned or s - cleaned[-1] > max(10, int(w * 0.015)):
            cleaned.append(s)
    bounds = [x0] + [s for s in cleaned if x0 < s < x1 - 1] + [x1]
    cells = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]
    cells = [(a, b) for a, b in cells if b - a > 20]
    if len(cells) < 2:
        return x0, x1

    def cell_hatch(a: int, b: int) -> float:
        hits = 0
        tot = 0
        for y in range(y0, min(y1, len(rows) - 1)):
            r0, r1 = rows[y], rows[y + 1]
            for xx in range(a, min(b - 1, w - 1), 2):
                tot += 1
                if r0[xx] and r1[xx + 1]:
                    hits += 1
        return hits / max(1, tot)

    width = max(1, x1 - x0)
    # слева — обозначение (С17), справа — способ сварки (ЗП/Р)
    a, b = cells[0]
    if (b - a) < 0.24 * width and cell_hatch(a, b) < 0.012:
        cells = cells[1:]
        width = max(1, cells[-1][1] - cells[0][0]) if cells else width
    if len(cells) >= 2:
        a, b = cells[-1]
        if (b - a) < 0.30 * width and cell_hatch(a, b) < 0.012:
            cells = cells[:-1]
    # Два эскиза = две первые колонки со штриховкой слева направо
    # (не «шов + способ сварки» по макс. score).
    hatched = [(a, b) for a, b in cells if cell_hatch(a, b) > 0.01]
    if len(hatched) >= 2:
        return hatched[0][0], hatched[1][1]
    if hatched:
        return hatched[0][0], hatched[-1][1]
    if cells:
        return cells[0][0], cells[-1][1]
    return x0, x1


def _strip_top_rules(im: Image.Image) -> Image.Image:
    rows, w, h = _rows(im)
    cut = 0
    for y in range(min(40, h)):
        dens = sum(rows[y])
        if dens == 0 or dens > w * 0.35:
            cut = y + 1
            continue
        break
    return im.crop((0, cut, w, h)) if cut else im


def _strip_top_text_header(im: Image.Image) -> Image.Image:
    """Срезает текстовую шапку колонок над чертежами."""
    rows, w, h = _rows(im)
    if h < 80:
        return im
    hl, hr = _side_hatch(rows, w, h)
    hatch = [hl[y] + hr[y] for y in range(h)]
    peak = max(hatch) if hatch else 0
    if peak < 4:
        return im
    thr = max(2.5, 0.14 * peak)
    start = None
    run = 0
    for y in range(h):
        if hatch[y] >= thr:
            run += 1
            if run >= 6:
                start = y - run + 1
                break
        else:
            run = 0
    if start is None or start < 18:
        return im
    start = min(start, int(h * 0.48))
    return im.crop((0, max(0, start - 8), w, h))


def _strip_bottom_text(im: Image.Image) -> Image.Image:
    """Срезает «Размеры, мм» / шапку следующей таблицы под эскизами."""
    rows, w, h = _rows(im)
    if h < 100:
        return im
    hl, hr = _side_hatch(rows, w, h)
    hatch = _smooth([hl[y] + hr[y] for y in range(h)], radius=max(5, h // 50))
    peak_y = max(range(h), key=lambda y: hatch[y])
    peak = hatch[peak_y]
    if peak < 4:
        return im
    thr = max(2.5, 0.15 * peak)
    # идём вниз от пика, режем после устойчивого провала
    gap = 0
    cut = h
    for y in range(peak_y, h):
        if hatch[y] < thr * 0.30:
            gap += 1
            if gap >= max(16, h // 20):
                cut = y - gap + 1
                break
        else:
            gap = 0
    if cut < h and cut > max(120, int(h * 0.45)):
        return im.crop((0, 0, w, min(h, cut + 12)))
    return im


def _trim_dense(im: Image.Image, pad: int = 8) -> Image.Image:
    rows, w, h = _rows(im)
    row_n = [sum(r) for r in rows]
    col_n = [sum(rows[y][x] for y in range(h)) for x in range(w)]
    ys = [i for i, n in enumerate(row_n) if n > 20]
    xs = [i for i, n in enumerate(col_n) if n > 20]
    if not ys or not xs:
        return im
    return im.crop((
        max(0, xs[0] - pad),
        max(0, ys[0] - pad),
        min(w, xs[-1] + 1 + pad),
        min(h, ys[-1] + 1 + pad),
    ))


def _looks_good(im: Image.Image) -> bool:
    w, h = im.size
    if w < 400 or h < 250:
        return False
    ar = w / h
    if ar < 1.05 or ar > 6.5:
        return False
    return _hatch_ok(im, min_side=25)


def refine_dual_sketch(im: Image.Image) -> Image.Image:
    """Сырой кроп области таблицы → оба чертежа без лишнего текста."""
    if im.mode not in ('RGB', 'L', 'RGBA'):
        im = im.convert('RGB')
    rows, w, h = _rows(im)
    if w < 40 or h < 40:
        return im

    x0, x1 = _content_x(rows, w, 0, h)
    x0, x1 = _drop_low_hatch_sides(rows, w, 0, h, x0, x1)
    if (x1 - x0) < 0.40 * w:
        x0, x1 = _content_x(rows, w, 0, h)
    pad = 8
    out = im.crop((max(0, x0 - pad), 0, min(w, x1 + pad), h))
    out = _strip_top_rules(out)
    out = _strip_top_text_header(out)
    out = _strip_bottom_text(out)
    out = _trim_dense(out, pad=6)

    if _looks_good(out):
        return out

    # fallback: нижняя часть исходника (эскизы под шапкой)
    sub = im.crop((0, int(h * 0.25), w, h))
    srows, sw, sh = _rows(sub)
    sx0, sx1 = _content_x(srows, sw, 0, sh)
    sx0, sx1 = _drop_low_hatch_sides(srows, sw, 0, sh, sx0, sx1)
    out2 = sub.crop((max(0, sx0 - pad), 0, min(sw, sx1 + pad), sh))
    out2 = _strip_top_rules(out2)
    out2 = _strip_top_text_header(out2)
    out2 = _strip_bottom_text(out2)
    out2 = _trim_dense(out2, pad=6)
    if _looks_good(out2):
        return out2
    return out if _hatch_ok(out, min_side=15) else out2


def refine_dual_sketch_file(src: Path | str, dst: Path | str | None = None) -> Path:
    src = Path(src)
    dst = Path(dst) if dst else src
    with Image.open(src) as im:
        out = refine_dual_sketch(im)
        dst.parent.mkdir(parents=True, exist_ok=True)
        out.save(dst, optimize=True)
    return dst
