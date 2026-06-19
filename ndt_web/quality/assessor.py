"""
Модуль оценки качества сварных соединений.

Вызывает логику из normative.np_105_18 и оформляет результаты
для отображения и генерации PDF.
"""

import os
import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

from normative.np_105_18 import assess_multiple_defects, DOCUMENT_FULL_NAME


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

    # Приводим данные к нужному формату для np_105_18
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
        weld_category=weld_category,
        wall_thickness_mm=wall_thickness,
        weld_length_mm=weld_length,
    )

    return {
        'normative_doc': normative_doc,
        'weld_category': weld_category,
        'wall_thickness': wall_thickness,
        'weld_length': weld_length,
        'defects_count': len(defects),
        **summary,
    }


def generate_assessment_pdf(assessment_data: dict, defects_data: list, output_path: str) -> str:
    """
    Создаёт PDF-отчёт об оценке качества.

    :param assessment_data: данные об объекте контроля
    :param defects_data: список дефектов
    :param output_path: путь для сохранения файла
    :return: путь к созданному файлу
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'T', parent=styles['Title'], fontSize=13, spaceAfter=6, alignment=TA_CENTER,
    )
    normal = ParagraphStyle(
        'N', parent=styles['Normal'], fontSize=9, spaceAfter=3,
    )
    small = ParagraphStyle(
        'S', parent=styles['Normal'], fontSize=8, textColor=colors.grey,
    )

    story = []

    story.append(Paragraph('ПРОТОКОЛ ОЦЕНКИ КАЧЕСТВА', title_style))
    story.append(Paragraph('СВАРНОГО СОЕДИНЕНИЯ', title_style))
    story.append(Paragraph(
        f'Нормативный документ: {assessment_data.get("normative_doc", "НП-105-18")}',
        normal,
    ))
    story.append(Paragraph(f'Дата: {datetime.now().strftime("%d.%m.%Y %H:%M")}', normal))
    story.append(Spacer(1, 5 * mm))

    # Параметры объекта
    params_data = [
        ['Параметр', 'Значение'],
        ['Категория шва', assessment_data.get('weld_category', '')],
        ['Толщина стенки, мм', str(assessment_data.get('wall_thickness', ''))],
        ['Длина шва, мм', str(assessment_data.get('weld_length', '')) or '—'],
    ]
    t = Table(params_data, colWidths=[80 * mm, 80 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.24, 0.47, 0.85)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 1), (0, -1), colors.Color(0.95, 0.97, 1.0)),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 5 * mm))

    # Результаты оценки дефектов
    results = assessment_data.get('results', [])
    table_data = [[
        '№', 'Тип дефекта', 'Размер, мм',
        'Доп. размер\n(мм)', 'Доп. размер\n(норма)', 'Результат', 'Ссылка',
    ]]

    for i, r in enumerate(results, 1):
        defect = defects_data[i - 1] if i - 1 < len(defects_data) else {}
        s1 = defect.get('size_1', 0)
        verdict_text = 'ГОДЕН' if r.get('is_acceptable') else 'БРАК'
        table_data.append([
            str(i),
            r.get('defect_name', ''),
            f'{s1:.2f}',
            f'{r.get("max_allowed_mm", 0):.2f}',
            '',
            verdict_text,
            r.get('reference', ''),
        ])

    results_table = Table(
        table_data,
        colWidths=[8 * mm, 40 * mm, 20 * mm, 22 * mm, 22 * mm, 20 * mm, 30 * mm],
    )
    results_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.24, 0.47, 0.85)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 1), (4, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    # Цвет строк в зависимости от результата
    for i, r in enumerate(results, 1):
        if not r.get('is_acceptable'):
            results_table.setStyle(TableStyle([
                ('BACKGROUND', (0, i), (-1, i), colors.Color(1.0, 0.9, 0.9)),
            ]))
        else:
            results_table.setStyle(TableStyle([
                ('BACKGROUND', (0, i), (-1, i), colors.Color(0.9, 1.0, 0.9)),
            ]))

    story.append(Paragraph('Результаты оценки дефектов:', ParagraphStyle('H', fontSize=10, spaceBefore=4, spaceAfter=4, fontName='Helvetica-Bold')))
    story.append(results_table)
    story.append(Spacer(1, 5 * mm))

    # Итоговое заключение
    is_ok = assessment_data.get('is_acceptable', False)
    verdict = assessment_data.get('verdict', '—')
    verdict_color = colors.Color(0.1, 0.6, 0.1) if is_ok else colors.Color(0.8, 0.1, 0.1)

    verdict_style = ParagraphStyle(
        'Verdict',
        parent=styles['Normal'],
        fontSize=14,
        textColor=verdict_color,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        spaceBefore=5,
        spaceAfter=5,
    )
    story.append(Paragraph(f'ЗАКЛЮЧЕНИЕ: {verdict}', verdict_style))

    if assessment_data.get('score_exceeded'):
        story.append(Paragraph(assessment_data.get('score_reason', ''), normal))

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        f'Подпись специалиста НК: _____________________',
        normal,
    ))

    doc.build(story)
    return output_path
