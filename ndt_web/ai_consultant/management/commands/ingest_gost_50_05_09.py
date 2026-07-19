"""Management-команда: загрузка ГОСТ Р 50.05.09-2018 в базу консультанта.

Идемпотентна. Вызывается из build.sh на Render (Shell на Free недоступен).

  python manage.py ingest_gost_50_05_09
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from django.core.management.base import BaseCommand

from ai_consultant.models import DocumentChunk, DocumentSource
from ai_consultant.services.embeddings import (
    EMBEDDING_DIM,
    get_embedding_model_name,
)

DOC_NUMBER = 'ГОСТ Р 50.05.09-2018'
DOC_TITLE = (
    'ГОСТ Р 50.05.09-2018 Система оценки соответствия в области использования '
    'атомной энергии. Унифицированные методики. Капиллярный контроль'
)
BASE = Path(__file__).resolve().parents[3]  # ndt_web/


def _find_pdf() -> Path | None:
    nd = BASE / 'normative_docs'
    if not nd.is_dir():
        return None
    for p in nd.iterdir():
        if p.is_file() and p.suffix.lower() == '.pdf' and '50.05.09' in p.name:
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
    parts = []
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


def ingest_pdf(pdf_path: Path) -> DocumentSource:
    raw = pdf_path.read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    existing = DocumentSource.objects.filter(checksum_sha256=checksum).first()
    if existing:
        print(f'PDF уже в базе (source #{existing.id})')
        if not existing.doc_number:
            existing.doc_number = DOC_NUMBER
            existing.save(update_fields=['doc_number'])
        return existing
    by_num = DocumentSource.objects.filter(doc_number=DOC_NUMBER).first()
    if by_num and by_num.checksum_sha256:
        print(f'Источник {DOC_NUMBER} уже есть (source #{by_num.id})')
        return by_num

    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(raw))
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            t = (page.extract_text() or '').strip()
            if t:
                pages.append((f'стр. {i}', t))
    except Exception as exc:
        print(f'Ошибка чтения PDF: {exc}')
        pages = []

    extract = BASE / '_gost_500509_extract.txt'
    if not pages and extract.exists():
        pages = [('текст', extract.read_text(encoding='utf-8'))]

    sections = []
    for label, body in pages:
        for j, chunk in enumerate(_chunk_text(body)):
            if len(chunk.strip()) > 40:
                sections.append((f'{label}' if j == 0 else f'{label}.{j}', chunk))

    print(f'PDF: фрагментов {len(sections)}')
    storage_key = f'documents/gost/{checksum[:16]}.pdf'
    try:
        from ai_consultant.services.storage import upload_document
        upload_document(str(pdf_path), storage_key)
    except Exception as exc:
        print(f'  [!] storage upload пропущен: {exc}')
        storage_key = str(pdf_path)

    src = DocumentSource.objects.create(
        title=DOC_TITLE,
        doc_type='gost',
        doc_number=DOC_NUMBER,
        storage_key=storage_key,
        checksum_sha256=checksum,
    )
    texts = [t for _, t in sections]
    vecs = _embed_or_zeros(texts)
    has_real = any(any(x != 0.0 for x in (v or [])) for v in vecs)
    model = get_embedding_model_name() if has_real else 'none-local'
    for i, ((lbl, txt), vec) in enumerate(zip(sections, vecs)):
        DocumentChunk.objects.create(
            source=src,
            chunk_index=i,
            section_label=lbl[:50],
            text=txt,
            embedding=vec,
            embedding_model_version=model,
        )
    print(f'PDF загружен: source #{src.id}, {len(sections)} чанков')
    return src


def sync_py_chunks():
    from sync_normative_py_to_db import _build_gost500509
    import sync_normative_py_to_db as S
    import ai_consultant.services.embeddings as E

    original = E.embed_texts

    def safe_embed(texts):
        try:
            return original(texts)
        except Exception as exc:
            print(f'  [!] sync без эмбеддингов: {exc}')
            return [_zero_vec() for _ in texts]

    E.embed_texts = safe_embed
    S.embed_texts = safe_embed
    try:
        _build_gost500509()
    finally:
        E.embed_texts = original
        S.embed_texts = original


class Command(BaseCommand):
    help = 'Загрузка ГОСТ Р 50.05.09-2018 (КК) в базу ИИ-консультанта'

    def handle(self, *args, **options):
        pdf = _find_pdf()
        if pdf:
            self.stdout.write(f'Найден PDF: {pdf.name}')
            ingest_pdf(pdf)
        else:
            self.stdout.write(self.style.WARNING(
                'PDF ГОСТ Р 50.05.09 не найден в normative_docs/'
            ))
        self.stdout.write('Синхронизация эталонных чанков…')
        sync_py_chunks()
        n = DocumentChunk.objects.filter(source__doc_number=DOC_NUMBER).count()
        self.stdout.write(self.style.SUCCESS(
            f'Итого чанков {DOC_NUMBER}: {n}'
        ))
