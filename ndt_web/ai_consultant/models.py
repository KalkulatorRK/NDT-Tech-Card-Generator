"""Модели ИИ-консультанта: источники документов, фрагменты с векторами, сессии диалогов.

Раздел 5 ТЗ. Для эмбеддингов используется pgvector.django.VectorField,
когда доступен (PostgreSQL + расширение vector), иначе (SQLite, локальная
разработка без Postgres) — JSONField с поиском через numpy (План Б, раздел 17).
"""
from django.db import models

# Адаптивный выбор типа поля для эмбеддинга: VectorField только на PostgreSQL+pgvector
try:
    from pgvector.django import VectorField  # type: ignore
    _USE_PGVECTOR = True
except Exception:
    VectorField = None
    _USE_PGVECTOR = False


def _embedding_field():
    if _USE_PGVECTOR:
        return VectorField(dimensions=1536)
    return models.JSONField(null=True, blank=True)


class DocumentSource(models.Model):
    """Нормативный документ (ГОСТ, НП, СТО)."""
    title = models.CharField(max_length=300, verbose_name='Название')
    doc_type = models.CharField(max_length=20, verbose_name='Тип',
                                help_text='gost / np / sto / other')
    doc_number = models.CharField(max_length=100, blank=True, verbose_name='Номер документа')
    source_url = models.URLField(blank=True, verbose_name='Ссылка')
    storage_key = models.CharField(max_length=255, blank=True, verbose_name='Ключ в хранилище')
    checksum_sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Источник документа'
        verbose_name_plural = 'Источники документов'
        ordering = ['doc_number']

    def __str__(self):
        return f"{self.doc_number or self.title}"


class DocumentChunk(models.Model):
    """Смысловой фрагмент документа (пункт НД или страница-рисунок/таблица)."""
    source = models.ForeignKey(DocumentSource, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.PositiveIntegerField(default=0)
    section_label = models.CharField(max_length=200, blank=True, verbose_name='Пункт/раздел')
    text = models.TextField(verbose_name='Текст фрагмента')
    embedding = _embedding_field()
    embedding_model_version = models.CharField(max_length=50, blank=True)
    is_golden = models.BooleanField(
        default=False,
        verbose_name='Эталонный якорь (golden answer)',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Фрагмент документа'
        verbose_name_plural = 'Фрагменты документов'
        ordering = ['source', 'chunk_index']

    def __str__(self):
        return f"{self.source} [{self.section_label}]"


class ConsultantSession(models.Model):
    """Сессия диалога пользователя с консультантом."""
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='consultant_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    llm_provider = models.CharField(max_length=30, blank=True)
    llm_model = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Сессия {self.id} ({self.user})"


class ConsultantMessage(models.Model):
    """Сообщение в сессии (вопрос или ответ)."""
    ROLE_CHOICES = [('user', 'Пользователь'), ('assistant', 'Консультант')]
    session = models.ForeignKey(ConsultantSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField(verbose_name='Содержимое')
    cited_chunks = models.ManyToManyField(DocumentChunk, blank=True, related_name='cited_in')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
