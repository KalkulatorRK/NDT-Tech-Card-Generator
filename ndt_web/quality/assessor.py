"""
Модуль оценки качества сварных соединений.

Вызывает логику из normative.np_105_18 и оформляет результаты
для отображения и генерации PDF.
"""

import os
import re
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from common.pdf_fonts import register_cyrillic_fonts, FONT_REGULAR, FONT_BOLD
from normative.np_105_18 import assess_multiple_defects


def _sanitize_radiographic_reference(reference: str) -> str:
    """Убирает ссылки на табл./п. 4.6 — для оценки по радиографическим снимкам."""
    if not reference:
        return '—'
    ref = reference.strip()
    if re.search(r'4[.,\s]*6', ref):
        return 'НП-105-18'
    return ref


def perform_assessment(form_data: dict, defects_data: list) -> dict:
    """
    Выполняет оценку качества сварного соединения.

    :param form_data: данные основной формы (doc, category, thickness, weld_length)
    :param defects_data: список словарей с данными о дефектах
    :return: итоговый словарь с результатами
    """
    weld_category = form_data.get('weld_category', 'II')
    wall_thickness = float(form_data.get('wall_thickness', 10))
    weld_length = float(form_data.get('weld_length', 0) or 0)
    normative_doc = form_data.get('normative_doc', 'НП-105-18')

    defects = []
    for d in defects_data:
        defects.append({
            'type': d.get('defect_type', ''),
            'size_1': float(d.get('size_1', 0) or 0),
            'size_2': float(d.get('size_2', 0) or 0),
            'count': int(d.get('count', 1)),
        })

    summary = assess_multiple_defects(
        defects=defects,
        category=weld_category,
        thickness_mm=wall_thickness,
        weld_length_mm=weld_length,
        inclusion_cluster_count_100mm=form_data.get('inclusion_cluster_count_100mm'),
        large_inclusion_count_100mm=form_data.get('large_inclusion_count_100mm'),
    )

    return {
        'normative_doc': normative_doc,
        'weld_category': weld_category,
        'wall_thickness': wall_thickness,
        'weld_length': weld_length,
        'inclusion_cluster_count_100mm': form_data.get('inclusion_cluster_count_100mm'),
        'large_inclusion_count_100mm': form_data.get('large_inclusion_count_100mm'),
        'defects_count': len(defects),
        **summary,
    }


def _pdf_styles():
    """Стили Paragraph с кириллическим шрифтом."""
    register_cyrillic_fonts()
    base = getSampleStyleSheet()
    return {
        'title': ParagraphStyle(
            'PdfTitle', parent=base['Title'],
            fontName=FONT_BOLD, fontSize=13, spaceAfter=4, alignment=TA_CENTER,
        ),
        'heading': ParagraphStyle(
            'PdfHeading', parent=base['Normal'],
            fontName=FONT_BOLD, fontSize=10, spaceBefore=4, spaceAfter=4,
        ),
        'normal': ParagraphStyle(
            'PdfNormal', parent=base['Normal'],
            fontName=FONT_REGULAR, fontSize=9, spaceAfter=2, leading=11,
        ),
        'small': ParagraphStyle(
            'PdfSmall', parent=base['Normal'],
            fontName=FONT_REGULAR, fontSize=8, leading=10,
        ),
        'cell': ParagraphStyle(
            'PdfCell', parent=base['Normal'],
            fontName=FONT_REGULAR, fontSize=8, leading=10,
        ),
        'cell_bold': ParagraphStyle(
            'PdfCellBold', parent=base['Normal'],
            fontName=FONT_BOLD, fontSize=8, leading=10,
        ),
        'verdict_ok': ParagraphStyle(
            'PdfVerdictOk', parent=base['Normal'],
            fontName=FONT_BOLD, fontSize=14, textColor=colors.Color(0.1, 0.6, 0.1),
            alignment=TA_CENTER, spaceBefore=5, spaceAfter=5,
        ),
        'verdict_fail': ParagraphStyle(
            'PdfVerdictFail', parent=base['Normal'],
            fontName=FONT_BOLD, fontSize=14, textColor=colors.Color(0.8, 0.1, 0.1),
            alignment=TA_CENTER, spaceBefore=5, spaceAfter=5,
        ),
    }


def _p(text, style, markup: bool = False) -> Paragraph:
    raw = str(text if text is not None else '—')
    if markup:
        safe = raw.replace('&', '&amp;')
    else:
        safe = raw.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return Paragraph(safe, style)


def generate_assessment_pdf(assessment_data: dict, defects_data: list, output_path: str) -> str:
    """
    Создаёт PDF-отчёт об оценке качества с поддержкой кириллицы.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    styles = _pdf_styles()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    story = []
    story.append(_p('ПРОТОКОЛ ОЦЕНКИ КАЧЕСТВА', styles['title']))
    story.append(_p('СВАРНОГО СОЕДИНЕНИЯ', styles['title']))
    story.append(_p(
        f'Нормативный документ: {assessment_data.get("normative_doc", "НП-105-18")}',
        styles['normal'],
    ))
    story.append(_p(
        f'Дата: {datetime.now().strftime("%d.%m.%Y %H:%M")}',
        styles['normal'],
    ))
    story.append(Spacer(1, 4 * mm))

    params_rows = [
        [_p('Параметр', styles['cell_bold']), _p('Значение', styles['cell_bold'])],
        [_p('Категория шва', styles['cell']), _p(assessment_data.get('weld_category', ''), styles['cell'])],
        [_p('Толщина стенки, мм', styles['cell']), _p(assessment_data.get('wall_thickness', ''), styles['cell'])],
        [_p('Длина шва, мм', styles['cell']), _p(assessment_data.get('weld_length', '') or '—', styles['cell'])],
    ]
    inc_count = assessment_data.get('inclusion_cluster_count_100mm')
    if inc_count is not None:
        params_rows.append([
            _p('Включения и скопления на 100,0 мм, шт.', styles['cell']),
            _p(inc_count, styles['cell']),
        ])
    large_count = assessment_data.get('large_inclusion_count_100mm')
    if large_count is not None:
        params_rows.append([
            _p('Крупные включения на 100,0 мм, шт.', styles['cell']),
            _p(large_count, styles['cell']),
        ])

    params_table = Table(params_rows, colWidths=[85 * mm, 85 * mm])
    params_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.24, 0.47, 0.85)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 1), (0, -1), colors.Color(0.95, 0.97, 1.0)),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(params_table)
    story.append(Spacer(1, 4 * mm))

    results = assessment_data.get('results', [])
    aggregate_types = {'_aggregate_regular_inclusions', '_aggregate_large_inclusions'}
    defect_results = [r for r in results if r.get('defect_type') not in aggregate_types]

    header = [
        _p('№', styles['cell_bold']),
        _p('Тип дефекта', styles['cell_bold']),
        _p('Усл. запись', styles['cell_bold']),
        _p('Размер,<br/>мм', styles['cell_bold'], markup=True),
        _p('Разм. 2,<br/>мм', styles['cell_bold'], markup=True),
        _p('Норма,<br/>мм', styles['cell_bold'], markup=True),
        _p('Кол-во', styles['cell_bold']),
        _p('Результат', styles['cell_bold']),
        _p('Ссылка на НД', styles['cell_bold']),
    ]
    table_data = [header]

    for i, r in enumerate(defect_results, 1):
        defect = defects_data[i - 1] if i - 1 < len(defects_data) else {}
        s1 = defect.get('size_1', 0)
        s2 = defect.get('size_2', 0)
        count = defect.get('count', 1)
        verdict_text = 'ГОДЕН' if r.get('is_acceptable') else 'БРАК'
        name = r.get('defect_name', '')
        if r.get('inclusion_group_label'):
            name = f'{name}<br/><i>{r["inclusion_group_label"]}</i>'

        table_data.append([
            _p(str(i), styles['cell']),
            _p(name, styles['cell'], markup=True),
            _p(r.get('gost_notation', '') or '—', styles['cell']),
            _p(f'{float(s1):.2f}', styles['cell']),
            _p(f'{float(s2):.2f}' if s2 else '—', styles['cell']),
            _p(
                f'{r.get("max_allowed_mm", 0):.2f}' if r.get('max_allowed_mm') else '—',
                styles['cell'],
            ),
            _p(str(count) if count else '—', styles['cell']),
            _p(verdict_text, styles['cell']),
            _p(_sanitize_radiographic_reference(r.get('reference', '')), styles['cell']),
        ])

    col_widths = [7 * mm, 30 * mm, 22 * mm, 14 * mm, 14 * mm, 14 * mm, 11 * mm, 14 * mm, 28 * mm]
    results_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    results_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.24, 0.47, 0.85)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (2, 1), (7, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))

    for i, r in enumerate(defect_results, 1):
        bg = (
            colors.Color(0.9, 1.0, 0.9) if r.get('is_acceptable')
            else colors.Color(1.0, 0.9, 0.9)
        )
        results_table.setStyle(TableStyle([
            ('BACKGROUND', (0, i), (-1, i), bg),
        ]))

    story.append(_p('Детальная оценка дефектов', styles['heading']))
    story.append(results_table)
    story.append(Spacer(1, 3 * mm))

    for i, r in enumerate(defect_results, 1):
        if r.get('reason'):
            story.append(_p(f'{i}. {r["reason"]}', styles['small']))
    story.append(Spacer(1, 3 * mm))

    aggregates = assessment_data.get('aggregates', [])
    if aggregates:
        story.append(_p('Оценка числа включений на участке 100,0 мм', styles['heading']))
        for agg in aggregates:
            status = 'в норме' if agg.get('is_acceptable') else 'ПРЕВЫШЕНО'
            story.append(_p(
                f'{agg.get("group_label", "")}: {agg.get("total_count", 0)} шт. '
                f'(допустимо: {agg.get("max_count_100mm", "—")} шт.) — {status}',
                styles['normal'],
            ))
        story.append(Spacer(1, 3 * mm))

    is_ok = assessment_data.get('is_acceptable', False)
    verdict = assessment_data.get('verdict', '—')
    story.append(_p(
        f'ЗАКЛЮЧЕНИЕ: {verdict}',
        styles['verdict_ok'] if is_ok else styles['verdict_fail'],
    ))

    if assessment_data.get('combined_gost_notation'):
        story.append(_p(
            f'Условная запись дефектов (ГОСТ 7512-82, приложение 5): '
            f'<b>{assessment_data["combined_gost_notation"]}</b>',
            styles['normal'],
            markup=True,
        ))

    if assessment_data.get('score_exceeded') and assessment_data.get('score_reason'):
        story.append(_p(assessment_data['score_reason'], styles['normal']))

    story.append(Spacer(1, 8 * mm))
    story.append(_p('Подпись специалиста НК: _____________________', styles['normal']))

    doc.build(story)
    return output_path
