"""Пересчёт эмбеддингов для всех фрагментов (раздел 8 ТЗ, при смене модели)."""
from django.core.management.base import BaseCommand
from ai_consultant.models import DocumentChunk
from ai_consultant.services.embeddings import embed_texts, get_embedding_model_name


class Command(BaseCommand):
    help = 'Пересчёт векторов эмбеддингов для всех фрагментов (при смене модели).'

    def handle(self, *args, **options):
        chunks = list(DocumentChunk.objects.all())
        self.stdout.write(f'Всего фрагментов: {len(chunks)}')
        batch_size = 50
        model = get_embedding_model_name()
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c.text for c in batch]
            vecs = embed_texts(texts)
            for c, vec in zip(batch, vecs):
                c.embedding = vec
                c.embedding_model_version = model
            DocumentChunk.objects.bulk_update(batch, ['embedding', 'embedding_model_version'])
            self.stdout.write(f'  обновлено {min(i+batch_size, len(chunks))}/{len(chunks)}')
        self.stdout.write(self.style.SUCCESS('Готово.'))
