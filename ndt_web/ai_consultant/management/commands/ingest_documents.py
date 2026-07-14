"""Загрузка нормативного документа в базу (раздел 11 ТЗ).

Пример:
  python manage.py ingest_documents --file=path.pdf --doc-type=gost \
      --doc-number="ГОСТ Р 50.05.07-2018" --title="..."
"""
import os
from django.core.management.base import BaseCommand
from ai_consultant.services.ingestion import (
    parse_pdf_to_sections, parse_docx_to_sections, parse_rtf_to_sections, compute_checksum
)
from ai_consultant.services.embeddings import embed_texts, get_embedding_model_name
from ai_consultant.services.storage import upload_document
from ai_consultant.models import DocumentSource, DocumentChunk


class Command(BaseCommand):
    help = 'Загрузка нормативного документа (PDF/DOCX/RTF) в базу с векторизацией.'

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True)
        parser.add_argument('--doc-type', default='gost')
        parser.add_argument('--doc-number', default='')
        parser.add_argument('--title', required=True)
        parser.add_argument('--ocr-all', action='store_true',
                            help='OCR (vision) ВСЕХ страниц, а не только с ключевыми словами рисунок/таблица.')

    def handle(self, *args, **options):
        file_path = options['file']
        with open(file_path, 'rb') as f:
            file_bytes = f.read()

        checksum = compute_checksum(file_bytes)
        existing = DocumentSource.objects.filter(checksum_sha256=checksum).first()
        if existing:
            self.stdout.write(f'Документ уже загружен (source #{existing.id}). Пропуск.')
            return

        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            sections = parse_pdf_to_sections(file_bytes, ocr_all=options.get('ocr_all', False))
        elif ext == '.docx':
            sections = parse_docx_to_sections(file_bytes)
        elif ext == '.rtf':
            sections = parse_rtf_to_sections(file_bytes)
        else:
            raise ValueError(f'Неподдерживаемый формат: {ext}')

        self.stdout.write(f'Найдено фрагментов: {len(sections)}. Векторизация...')

        sections = [s for s in sections if len(s['text'].strip()) > 20]

        storage_key = f"documents/{options['doc_type']}/{checksum[:16]}{ext}"
        upload_document(file_path, storage_key)

        source = DocumentSource.objects.create(
            title=options['title'],
            doc_type=options['doc_type'],
            doc_number=options['doc_number'],
            storage_key=storage_key,
            checksum_sha256=checksum,
        )

        batch_size = 50
        for i in range(0, len(sections), batch_size):
            batch = sections[i:i + batch_size]
            texts = [s['text'] for s in batch]
            vecs = embed_texts(texts)
            model = get_embedding_model_name()
            for s, vec in zip(batch, vecs):
                DocumentChunk.objects.create(
                    source=source,
                    chunk_index=i + batch.index(s),
                    section_label=s['section_label'][:50],
                    text=s['text'],
                    embedding=vec,
                    embedding_model_version=model,
                )
            self.stdout.write(f'  сохранено {min(i+batch_size, len(sections))}/{len(sections)}')

        self.stdout.write(self.style.SUCCESS(
            f"Документ \"{options['title']}\" загружен: {len(sections)} фрагментов."
        ))
