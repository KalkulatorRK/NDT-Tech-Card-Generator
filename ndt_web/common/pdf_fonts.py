"""
Регистрация шрифтов с поддержкой кириллицы для ReportLab PDF.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_REGULAR = 'DejaVuSans'
FONT_BOLD = 'DejaVuSans-Bold'

_FONTS_DIR = Path(__file__).resolve().parent.parent / 'fonts'


@lru_cache(maxsize=1)
def register_cyrillic_fonts() -> tuple[str, str]:
    """
    Регистрирует DejaVu Sans (обычный и жирный) в ReportLab.

    :return: (имя обычного шрифта, имя жирного шрифта)
    """
    regular_path = _FONTS_DIR / 'DejaVuSans.ttf'
    bold_path = _FONTS_DIR / 'DejaVuSans-Bold.ttf'

    if not regular_path.exists():
        raise FileNotFoundError(
            f'Не найден шрифт DejaVuSans: {regular_path}'
        )

    if FONT_REGULAR not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(regular_path)))

    if bold_path.exists() and FONT_BOLD not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold_path)))

    return FONT_REGULAR, FONT_BOLD
