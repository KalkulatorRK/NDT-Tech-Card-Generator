# -*- coding: utf-8 -*-
"""Проверка системного кропа эскизов ГОСТ 16037."""
from __future__ import annotations

import unittest
from pathlib import Path

from PIL import Image

from gost_16037_sketches import _hatch_ok, refine_dual_sketch

STATIC = Path(__file__).resolve().parent.parent / 'static' / 'techcards' / 'joints' / 'gost_16037'
SAMPLE_CODES = ['С17', 'С2', 'С4', 'С19', 'У8', 'Н1', 'С18']


class TestGost16037Sketches(unittest.TestCase):
    def test_all_pngs_present(self):
        self.assertTrue(STATIC.is_dir(), STATIC)
        pngs = list(STATIC.glob('*.png'))
        self.assertGreaterEqual(len(pngs), 30, len(pngs))

    def test_samples_dual_hatch(self):
        for code in SAMPLE_CODES:
            path = STATIC / f'{code}.png'
            self.assertTrue(path.is_file(), code)
            im = Image.open(path)
            w, h = im.size
            self.assertGreater(w, 400, (code, im.size))
            self.assertGreater(h, 250, (code, im.size))
            self.assertGreater(w / h, 1.05, (code, 'ожидается кадр двух эскизов', im.size))
            self.assertLess(w / h, 8.0, (code, 'слишком плоский кадр — похоже на шапку таблицы', im.size))
            self.assertTrue(_hatch_ok(im, min_side=25), (code, 'мало штриховки'))

    def test_refine_keeps_dual(self):
        path = STATIC / 'С17.png'
        if not path.is_file():
            self.skipTest('no С17')
        im = Image.open(path).convert('RGB')
        out = refine_dual_sketch(im)
        self.assertTrue(_hatch_ok(out, min_side=20))
        self.assertGreater(out.size[1], 150)


if __name__ == '__main__':
    unittest.main()
