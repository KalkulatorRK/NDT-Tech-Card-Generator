"""Загрузка комплекта ГОСТ Р 50.05.* (PDF + эталоны из .py) в базу консультанта.

Идемпотентна. На деплое вызывается из build.sh.

  python manage.py ingest_gost_50_05_series
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from django.core.management.base import BaseCommand

from ai_consultant.models import DocumentChunk, DocumentSource
from ai_consultant.services.embeddings import EMBEDDING_DIM, get_embedding_model_name

BASE = Path(__file__).resolve().parents[3]  # ndt_web/

# (маркер имени PDF, doc_number, title)
DOCS = [
    (
        '50.05.01',
        'ГОСТ Р 50.05.01-2018',
        'ГОСТ Р 50.05.01-2018. Контроль герметичности газовыми и жидкостными методами',
    ),
    (
        '50.05.02',
        'ГОСТ Р 50.05.02-2022',
        'ГОСТ Р 50.05.02-2022. Ультразвуковой контроль сварных соединений и наплавок',
    ),
    (
        '50.05.03',
        'ГОСТ Р 50.05.03-2022',
        'ГОСТ Р 50.05.03-2022. Ультразвуковая толщинометрия',
    ),
    (
        '50.05.04',
        'ГОСТ Р 50.05.04-2022',
        'ГОСТ Р 50.05.04-2022. УЗК сварных соединений из аустенитных сталей',
    ),
    (
        '50.05.05',
        'ГОСТ Р 50.05.05-2018',
        'ГОСТ Р 50.05.05-2018. УЗК основных материалов (полуфабрикатов)',
    ),
    (
        '50.05.08',
        'ГОСТ Р 50.05.08-2018',
        'ГОСТ Р 50.05.08-2018. Визуальный и измерительный контроль',
    ),
    (
        '50.05.11',
        'ГОСТ Р 50.05.11-2018',
        'ГОСТ Р 50.05.11-2018. Персонал НК и РК. Подтверждение компетентности',
    ),
]


def _find_pdf(marker: str) -> Path | None:
    nd = BASE / 'normative_docs'
    if not nd.is_dir():
        return None
    for p in nd.iterdir():
        if p.is_file() and p.suffix.lower() == '.pdf' and marker in p.name:
            return p
    return None


def _zero_vec():
    return [0.0] * EMBEDDING_DIM


def _embed_or_zeros(texts: list[str]) -> list:
    if not texts:
        return []
    try:
        from ai_consultant.services.embeddings import embed_texts
        return embed_texts(texts)
    except Exception as exc:
        print(f'  [!] эмбеддинги недоступны ({exc}); нулевые векторы')
        return [_zero_vec() for _ in texts]


def _chunk_text(text: str, max_chars: int = 1800) -> list[str]:
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    if len(text) <= max_chars:
        return [text] if text else []
    parts: list[str] = []
    blocks = re.split(r'(?=\n?\d+\.\d+)', text)
    buf = ''
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if len(buf) + len(b) + 1 <= max_chars:
            buf = f'{buf}\n{b}'.strip()
        else:
            if buf:
                parts.append(buf)
            if len(b) <= max_chars:
                buf = b
            else:
                for i in range(0, len(b), max_chars):
                    parts.append(b[i:i + max_chars])
                buf = ''
    if buf:
        parts.append(buf)
    return parts


def _extract_pdf_text(pdf: Path) -> str:
    try:
        import pdfplumber
        parts = []
        with pdfplumber.open(pdf) as doc:
            for page in doc.pages:
                parts.append(page.extract_text() or '')
        return '\n'.join(parts)
    except Exception:
        from pypdf import PdfReader
        r = PdfReader(str(pdf))
        return '\n'.join((p.extract_text() or '') for p in r.pages)


def _ingest_pdf(doc_number: str, title: str, pdf: Path) -> int:
    raw = pdf.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()[:16]
    src, created = DocumentSource.objects.get_or_create(
        doc_number=doc_number,
        defaults={'title': title, 'doc_type': 'gost'},
    )
    if not created and src.title != title:
        src.title = title
        src.save(update_fields=['title'])

    marker = f'pdf:{digest}'
    if DocumentChunk.objects.filter(source=src, section_label__startswith=marker).exists():
        print(f'  PDF уже загружен ({marker})')
        return 0

    text = _extract_pdf_text(pdf)
    chunks = _chunk_text(text)
    if not chunks:
        print('  PDF без текстового слоя / пустой')
        return 0

    vecs = _embed_or_zeros(chunks)
    base = DocumentChunk.objects.filter(source=src).count()
    model_name = get_embedding_model_name()
    for i, (ch, vec) in enumerate(zip(chunks, vecs)):
        DocumentChunk.objects.create(
            source=src,
            chunk_index=base + i,
            section_label=f'{marker} стр./блок {i + 1}',
            text=ch,
            embedding=vec,
            embedding_model_version=model_name,
        )
    print(f'  PDF: +{len(chunks)} чанков')
    return len(chunks)


class Command(BaseCommand):
    help = 'Загрузка ГОСТ Р 50.05.01/02/03/04/05/08/11 в базу консультанта'

    def handle(self, *args, **options):
        total = 0
        for marker, doc_number, title in DOCS:
            print(f'{doc_number}:')
            pdf = _find_pdf(marker)
            if pdf is None:
                print(f'  PDF не найден (маркер {marker})')
            else:
                print(f'  файл: {pdf.name}')
                total += _ingest_pdf(doc_number, title, pdf)

        # эталонные чанки из .py
        print('Эталоны из normative/*.py …')
        from sync_normative_py_to_db import (
            _build_gost500501,
            _build_gost500502,
            _build_gost500503,
            _build_gost500504,
            _build_gost500505,
            _build_gost500508,
            _build_gost500511,
        )
        for fn in (
            _build_gost500501,
            _build_gost500502,
            _build_gost500503,
            _build_gost500504,
            _build_gost500505,
            _build_gost500508,
            _build_gost500511,
        ):
            try:
                fn()
            except Exception as exc:
                print(f'  [!] {fn.__name__}: {exc}')

        self.stdout.write(self.style.SUCCESS(
            f'Готово. Новых PDF-чанков: {total}'
        ))
