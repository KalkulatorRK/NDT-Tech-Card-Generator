"""Загрузка ГОСТ Р 50.05.09-2018 в базу ИИ-консультанта.

1) PDF из normative_docs (если ещё не загружен по checksum).
2) Эталонные чанки из normative/gost_50_05_09.py (через sync).

Запуск из каталога ndt_web:
    python ingest_gost_50_05_09.py

При отсутствии OPENAI_API_KEY / NOUS_PORTAL_API_KEY чанки сохраняются
без эмбеддингов (поиск по тексту + preferred_nds в режиме КК).
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ndt_project.settings')
os.environ.setdefault('ALLOWED_HOSTS', 'testserver,127.0.0.1,localhost')

# Подхватить .env (без вывода значений)
_env = BASE / '.env'
if _env.exists():
    for line in _env.read_text(encoding='utf-8', errors='ignore').splitlines():
        s = line.strip()
        if not s or s.startswith('#') or '=' not in s:
            continue
        k, v = s.split('=', 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v

import django
django.setup()

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
        print(f'  [!] эмбеддинги недоступны ({exc}); сохраняю нулевые векторы (поиск по тексту)')
        return [_zero_vec() for _ in texts]


def _chunk_text(text: str, max_chars: int = 1800) -> list[str]:
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    if len(text) <= max_chars:
        return [text] if text else []
    parts = []
    # режем по абзацам/пунктам
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
        print(f'PDF уже в базе (source #{existing.id}, doc_number={existing.doc_number})')
        if not existing.doc_number:
            existing.doc_number = DOC_NUMBER
            existing.save(update_fields=['doc_number'])
        return existing
    by_num = DocumentSource.objects.filter(doc_number=DOC_NUMBER).first()
    if by_num and by_num.checksum_sha256:
        print(f'Источник {DOC_NUMBER} уже есть (source #{by_num.id}), PDF не дублирую')
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

    # fallback: текстовый экстракт
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
    # временно подменяем embed_texts на безопасный вариант
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


def main():
    pdf = _find_pdf()
    if pdf:
        print(f'Найден PDF: {pdf.name}')
        ingest_pdf(pdf)
    else:
        print('PDF ГОСТ Р 50.05.09 не найден в normative_docs/')
    print('Синхронизация эталонных чанков из gost_50_05_09.py…')
    sync_py_chunks()
    n = DocumentChunk.objects.filter(source__doc_number=DOC_NUMBER).count()
    print(f'Итого чанков {DOC_NUMBER}: {n}')
    print('ГОТОВО')


if __name__ == '__main__':
    main()
