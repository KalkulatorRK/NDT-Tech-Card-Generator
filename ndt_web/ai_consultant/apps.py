"""Конфигурация приложения ai_consultant.

При запуске проверяем, что размерность вектора в БД совпадает
с выбранной моделью эмбеддингов (требование раздела 8 ТЗ).
"""
from django.apps import AppConfig
import os


class AiConsultantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_consultant'

    def ready(self):
        expected = int(os.environ.get('EMBEDDING_DIM', '1536'))
        actual = int(os.environ.get('EMBEDDING_DIM_ACTUAL', expected))
        if expected != actual:
            import logging
            logging.getLogger(__name__).warning(
                f"[ai_consultant] Размерность эмбеддинга в БД ({actual}) "
                f"отличается от модели ({expected}). Пересоздайте индекс "
                f"или выполните reindex_embeddings."
            )
