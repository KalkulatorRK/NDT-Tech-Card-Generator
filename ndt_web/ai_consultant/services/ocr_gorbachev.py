#!/usr/bin/env python3
"""OCR Горбачёва через tesseract + нарезка чанков по разделам + загрузка в БД."""
import os, sys, re, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ndt_project.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import django
django.setup()
from ai_consultant.models import DocumentSource, DocumentChunk
from ai_consultant.services.embeddings import embed_texts, get_embedding_model_name

import fitz
from PIL import Image
from tesserocr import PyTessBaseAPI

TESSDATA = '/home/hermesadm/.tessdata'
PDF_PATH = '/tmp/gorbachev_book.pdf'
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'textbook_sources')
os.makedirs(OUT_DIR, exist_ok=True)
OCR_FILE = os.path.join(OUT_DIR, 'gorbachev_ocr_full_tess.txt')

doc = fitz.open(PDF_PATH)
total = len(doc)
print(f"📖 {total} страниц")

# === ЭТАП 1: OCR через tesseract ===
start = 0
if os.path.exists(OCR_FILE):
    existing = open(OCR_FILE).read()
    start = max(0, len([l for l in existing.split('\n') if l.startswith('=== PAGE ')]) - 1)
    print(f"🔄 Продолжаю со стр. {start + 1}")

with open(OCR_FILE, 'a') as f:
    for p in range(start, total):
        pix = doc[p].get_pixmap(dpi=200)
        img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
        with PyTessBaseAPI(lang='rus', path=TESSDATA) as api:
            api.SetImage(img)
            # Улучшаем OCR для книг
            api.SetVariable('tessedit_pageseg_mode', '6')  # Один блок текста
            api.SetVariable('textord_heavy_nr', '1')
            text = api.GetUTF8Text().strip()
        f.write(f"=== PAGE {p+1} ===\n{text}\n")
        if p % 20 == 0:
            f.flush()
        if p % 10 == 0:
            print(f'  Стр.{p+1}: {len(text)} симв.')

doc.close()
print(f'📝 OCR завершён! {total} стр., файл: {OCR_FILE}')

# === ЭТАП 2: Парсинг и нарезка ===
body = open(OCR_FILE).read()
body = re.sub(r'\n=== PAGE \d+ ===\n', '\n', body)

# Ищем все заголовки вида "1.1." или "1.1.1" с текстом после
# В tesseract-тексте заголовки выглядят как "1.1. Название"
# или просто в начале строки
sections = []
for m in re.finditer(r'^(\d+\.\d+(?:\.\d+)?)[\.\s]+([А-ЯЁ][^\n]+)', body, re.MULTILINE):
    sections.append((m.start(), m.end(), m.group(0).strip()))

print(f'📋 Найдено заголовков разделов: {len(sections)}')
for i, (_, _, title) in enumerate(sections[:25]):
    print(f'  {i+1}. {title[:60]}')
if len(sections) > 25:
    print(f'  ... и ещё {len(sections) - 25}')

# Режем чанки по найденным заголовкам
chunks_raw = []
prev_end = 0
for start_pos, end_pos, title in sections:
    if prev_end > 0:
        text = body[prev_end:start_pos].strip()
        if text:
            chunks_raw.append((prev_title, text))
    prev_end = start_pos
    prev_title = title

tail = body[prev_end:].strip()
if tail and sections:
    chunks_raw.append((sections[-1][2], tail))

# Если заголовков мало — режем по границам
if len(chunks_raw) < 10:
    print("⚠️ Мало разделов, режу по строкам с номерами")
    chunks_raw = []
    for m in re.finditer(r'(?:^|\n)((?:\d+\.?)+[\.\s]+[А-ЯЁ][^\n]*)(?=\n)', body):
        pass

print(f'\n📚 Чанков: {len(chunks_raw)}')
for i, (t, tx) in enumerate(chunks_raw[:8]):
    print(f'  {i+1}. [{t[:45]}] {len(tx)} симв.')
if len(chunks_raw) > 8:
    print(f'  ... и ещё {len(chunks_raw) - 8}')

# === ЭТАП 3: Загрузка в БД ===
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
    print(f'♻️ Старый источник обновлён (удалено {old})')
else:
    print('✅ Создан новый источник')

objs = []
for i, (title, text) in enumerate(chunks_raw):
    objs.append(DocumentChunk(
        source=source, chunk_index=i + 1,
        section_label=title[:200],
        text=text,
    ))

BS = 20
print('🔮 Эмбеддинги...')
for i in range(0, len(objs), BS):
    batch = objs[i:i+BS]
    try:
        emb = embed_texts([o.text for o in batch])
        for j, o in enumerate(batch):
            o.embedding = emb[j] if j < len(emb) else None
            o.embedding_model_version = EMB
    except Exception as e:
        print(f'  ⚠️ emb batch {i}: {e}')
    time.sleep(0.3)

DocumentChunk.objects.bulk_create(objs, batch_size=50)
print(f'✅ Сохранено {len(objs)} чанков')
print(f'📚 {source.doc_number}')
