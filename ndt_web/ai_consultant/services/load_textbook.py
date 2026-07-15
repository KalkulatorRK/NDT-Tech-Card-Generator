"""Загрузка учебного пособия «Основы радиационного НК» в БД консультанта."""
import os, re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ndt_project.settings')
import django
django.setup()

from ai_consultant.models import DocumentSource, DocumentChunk
from ai_consultant.services.embeddings import embed_texts, get_embedding_model_name

EMB_MODEL = get_embedding_model_name()

# Читаем текст
p = '/home/hermesadm/ndt-work/NDT-Tech-Card-Generator/ndt_web/textbook_sources/rt_basics_full.txt'
if not os.path.exists(p):
    import fitz
    pdf_src = '/home/hermesadm/.hermes/cache/documents/doc_fcb829c3fa25_Основы RT контроля.pdf'
    doc = fitz.open(pdf_src)
    full = '\n'.join(doc[i].get_text() for i in range(len(doc)))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f: f.write(full)
else:
    full = open(p).read()

# Нарезка чанков
chunks_raw = []
lines = full.split('\n')
cur_label, cur_text = 'ВВЕДЕНИЕ', ''
for line in lines:
    s = line.strip()
    m = re.match(r'^(\d+(?:\.\d+)*)[\.\s]+([А-ЯЁ].*)$', s)
    if m and len(s) < 120:
        if cur_text.strip():
            chunks_raw.append((cur_label, cur_text.strip()))
        cur_label = s[:100]
        cur_text = ''
    else:
        cur_text += s + '\n'
if cur_text.strip():
    chunks_raw.append((cur_label, cur_text.strip()))

print(f'Нарезано {len(chunks_raw)} чанков')

# Источник
source, created = DocumentSource.objects.get_or_create(
    doc_number='Назипов Р.А. Основы радиационного НК (2008)',
    defaults={
        'title': 'Основы радиационного неразрушающего контроля. Учебно-методическое пособие. Казань, КГУ, 2008. 66 с.',
        'doc_type': 'textbook',
        'is_active': True,
    }
)
if not created:
    n_old = source.chunks.count()
    source.chunks.all().delete()
    print(f'Источник обновлён (удалено {n_old} старых чанков)')
else:
    print('Создан новый источник type=textbook')

# Создаём чанки с эмбеддингами
texts = [c[1] for c in chunks_raw]
labels = [c[0] for c in chunks_raw]

print(f'Генерирую эмбеддинги для {len(texts)} текстов...')
embeddings = embed_texts(texts)
print(f'Эмбеддинги: {len(embeddings)} шт x {len(embeddings[0])} dim')

objs = []
for i, (label, text) in enumerate(chunks_raw):
    objs.append(DocumentChunk(
        source=source,
        chunk_index=i + 1,
        section_label=label,
        text=text,
        embedding=embeddings[i] if i < len(embeddings) else None,
        embedding_model_version=EMB_MODEL,
    ))

DocumentChunk.objects.bulk_create(objs, batch_size=50)
print(f'Сохранено {len(objs)} чанков')
print(f'Готово! Источник: {source.doc_number}')
