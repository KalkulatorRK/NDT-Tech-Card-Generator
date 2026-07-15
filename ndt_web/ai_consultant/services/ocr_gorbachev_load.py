#!/usr/bin/env python3
"""Этап 2: парсинг OCR-текста Горбачёва + нарезка чанков + загрузка в БД.

Запускать с загруженным .env:
  cd /home/hermesadm/ndt-work/NDT-Tech-Card-Generator/ndt_web
  set -a && source /home/hermesadm/.env && set +a
  PYTHONPATH=. DJANGO_SETTINGS_MODULE=ndt_project.settings python3 ai_consultant/services/ocr_gorbachev_load.py
"""
import os, sys, re, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ndt_project.settings')
import django
django.setup()
from ai_consultant.models import DocumentSource, DocumentChunk
from ai_consultant.services.embeddings import embed_texts, get_embedding_model_name

OCR_PATH = os.path.join(os.path.dirname(__file__), '..', 'textbook_sources', 'gorbachev_ocr_full_tess.txt')
if not os.path.exists(OCR_PATH):
    OCR_PATH = '/home/hermesadm/ndt-work/NDT-Tech-Card-Generator/ndt_web/ai_consultant/textbook_sources/gorbachev_ocr_full_tess.txt'

body = open(OCR_PATH).read()
# Убираем разметку страниц
body = re.sub(r'\n=== PAGE \d+ ===\n', '\n', body)

# Ищем заголовки разделов: "1.1. Текст", "4.2. Текст", "10.1. Текст"
headers = []
for m in re.finditer(r'(?:^|\n)(\d+\.\d+(?:\.\d+)?)[\.\s]+([А-ЯЁA-Z][^\n]{3,80})', body):
    full_title = f"{m.group(1)}. {m.group(2).strip()}"
    headers.append((m.start(), full_title))

print(f'📋 Найдено заголовков: {len(headers)}')
for i, (_, t) in enumerate(headers[:20]):
    print(f'  {i+1}. {t[:60]}')
if len(headers) > 20:
    print(f'  ... и ещё {len(headers)-20}')

# Режем чанки
chunks = []
prev_pos = 0
prev_title = 'ВВЕДЕНИЕ'
for pos, title in headers:
    if pos > prev_pos:
        text = body[prev_pos:pos].strip()
        if len(text) > 100:
            chunks.append((prev_title, text))
    prev_pos = pos
    prev_title = title

tail = body[prev_pos:].strip()
if len(tail) > 100:
    chunks.append((prev_title, tail))

print(f'\n📚 Чанков: {len(chunks)}')
for i, (t, tx) in enumerate(chunks[:5]):
    print(f'  {i+1}. [{t[:45]}] {len(tx)} симв.')

# === Загрузка в БД ===
EMB = get_embedding_model_name()

source, created = DocumentSource.objects.get_or_create(
    doc_number='Горбачёв В.И. Радиографический контроль сварных соединений (2009)',
    defaults={
        'title': 'Радиографический контроль сварных соединений. Учебно-методическое пособие. Москва: Спутник+, 2009. 487 с.',
        'doc_type': 'textbook',
        'is_active': True,
    }
)
if not created:
    old = source.chunks.count()
    source.chunks.all().delete()
    print(f'♻️ Удалено {old} старых чанков')

objs = []
for i, (title, text) in enumerate(chunks):
    objs.append(DocumentChunk(
        source=source, chunk_index=i + 1,
        section_label=title[:200],
        text=text,
    ))

BS = 20
total_emb = len(objs)
print(f'🔮 Эмбеддинги: {total_emb} чанков...')
for i in range(0, len(objs), BS):
    batch = objs[i:i+BS]
    texts = [o.text[:15000] for o in batch]  # обрезка до ~3000 токенов для text-embedding-3-small (макс 8192)
    try:
        emb = embed_texts(texts)
        for j, o in enumerate(batch):
            o.embedding = emb[j] if j < len(emb) else None
            o.embedding_model_version = EMB
        if i % 40 == 0:
            print(f'  {i}/{total_emb}')
    except Exception as e:
        err = str(e)[:80]
        print(f'  ⚠️ emb fail batch {i}: {err}')
        # Пропускаем этот батч
        for o in batch:
            pass  # оставляем embedding=None, обработаем позже
    time.sleep(0.3)

# Сохраняем только чанки с эмбеддингами
good = [o for o in objs if o.embedding is not None]
print(f'  Чанков с эмбеддингами: {len(good)}/{total_emb}')
DocumentChunk.objects.bulk_create(good, batch_size=50)
print(f'✅ Сохранено {len(good)} чанков')
print(f'📚 {source.doc_number}')
