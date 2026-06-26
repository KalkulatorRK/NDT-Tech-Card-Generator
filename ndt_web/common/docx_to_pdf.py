"""
Конвертация DOCX → PDF через mammoth (DOCX→HTML) и xhtml2pdf (HTML→PDF).

Используется как основной путь генерации PDF техкарт; при ошибке
вызывающий код переключается на ReportLab.
"""

from __future__ import annotations

import base64
import logging
import os
from io import BytesIO
from pathlib import Path

import mammoth
from xhtml2pdf import pisa

from common.pdf_fonts import _FONTS_DIR

logger = logging.getLogger(__name__)

_FONT_REGULAR = _FONTS_DIR / 'DejaVuSans.ttf'
_FONT_BOLD = _FONTS_DIR / 'DejaVuSans-Bold.ttf'


def _embed_images(image) -> dict:
    """Встраивает изображения из DOCX как data-URI для xhtml2pdf."""
    with image.open() as image_bytes:
        encoded = base64.b64encode(image_bytes.read()).decode('ascii')
    return {
        'src': f'data:{image.content_type};base64,{encoded}',
    }


def docx_to_html(docx_path: str) -> str:
    """
    Конвертирует DOCX в HTML-фрагмент тела документа.

    :param docx_path: путь к файлу .docx
    :return: HTML-содержимое (без обёртки html/head)
    """
    with open(docx_path, 'rb') as docx_file:
        result = mammoth.convert_to_html(
            docx_file,
            convert_image=mammoth.images.img_element(_embed_images),
        )
    for message in result.messages:
        logger.debug('mammoth: %s', message)
    return result.value


def _build_pdf_html(body_html: str) -> str:
    """Оборачивает HTML-фрагмент в полный документ с кириллическими шрифтами."""
    regular = _FONT_REGULAR.resolve()
    bold = _FONT_BOLD.resolve()
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<style>
@font-face {{
    font-family: "DejaVuSans";
    src: url("file://{regular}");
}}
@font-face {{
    font-family: "DejaVuSans-Bold";
    src: url("file://{bold}");
    font-weight: bold;
}}
@page {{
    size: a4;
    margin: 1.5cm 1.5cm 1.5cm 2cm;
}}
body {{
    font-family: DejaVuSans, sans-serif;
    font-size: 9pt;
    line-height: 1.35;
    color: #222;
}}
p {{ margin: 0.25em 0; }}
table {{
    border-collapse: collapse;
    width: 100%;
    font-size: 8.5pt;
    margin: 0.4em 0;
}}
td, th {{
    border: 1px solid #999;
    padding: 3px 5px;
    vertical-align: top;
}}
strong, b {{
    font-family: DejaVuSans-Bold, DejaVuSans, sans-serif;
}}
img {{
    max-width: 100%;
    height: auto;
}}
</style>
</head>
<body>{body_html}</body>
</html>"""


def _link_callback(uri: str, rel: str) -> str:
    """Разрешает file:// пути к шрифтам для xhtml2pdf."""
    if uri.startswith('file://'):
        return uri[7:]
    path = Path(uri)
    if path.is_file():
        return str(path.resolve())
    return uri


def html_to_pdf(html: str, output_path: str) -> None:
    """
    Конвертирует HTML в PDF-файл.

    :raises RuntimeError: если xhtml2pdf вернул ошибку
    """
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'wb') as pdf_file:
        result = pisa.CreatePDF(
            html,
            dest=pdf_file,
            encoding='utf-8',
            link_callback=_link_callback,
        )
    if result.err:
        raise RuntimeError(f'xhtml2pdf: ошибка конвертации (код {result.err})')


def convert_docx_to_pdf(docx_path: str, output_path: str) -> str:
    """
    Полный пайплайн DOCX → HTML → PDF.

    :return: путь к созданному PDF
    :raises RuntimeError: при ошибке конвертации
    """
    if not os.path.isfile(docx_path):
        raise FileNotFoundError(f'DOCX не найден: {docx_path}')
    if not _FONT_REGULAR.is_file():
        raise FileNotFoundError(f'Шрифт не найден: {_FONT_REGULAR}')

    body_html = docx_to_html(docx_path)
    if not body_html.strip():
        raise RuntimeError('mammoth вернул пустой HTML')

    full_html = _build_pdf_html(body_html)
    html_to_pdf(full_html, output_path)

    if not os.path.isfile(output_path) or os.path.getsize(output_path) < 500:
        raise RuntimeError('PDF не создан или слишком мал')

    return output_path
