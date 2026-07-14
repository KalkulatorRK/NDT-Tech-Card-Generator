"""Включение pgvector и перевод поля embedding в vector(1536).

На Neon (PostgreSQL + pgvector) расширение ставится один раз, а поле
DocumentChunk.embedding меняется с JSONB (сгенерировано на SQLite) на
vector(1536). Если таблица ещё не создана как vector — ALTER COLUMN.

Раздел 6.1 ТЗ.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ai_consultant', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="DROP EXTENSION IF EXISTS vector;",  # осторожно: удалит зависимости
        ),
        # Перевод embedding в vector(1536). USING NULL::vector защищает от
        # ошибки при пустых/несовместимых данных.
        migrations.RunSQL(
            sql="ALTER TABLE ai_consultant_documentchunk ALTER COLUMN embedding TYPE vector(1536) USING NULL::vector;",
            reverse_sql="ALTER TABLE ai_consultant_documentchunk ALTER COLUMN embedding TYPE jsonb USING NULL::jsonb;",
        ),
    ]
