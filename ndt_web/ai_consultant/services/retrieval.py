"""Гибридный поиск (раздел 9 ТЗ): BM25 (полнотекст) + векторная близость (pgvector).

На PostgreSQL/pgvector: полнотекст через to_tsvector на лету + L2-поиск по embedding.
На SQLite (План Б): полнотекст через icontains + косинус через numpy (JSON-эмбеддинги).

Возвращает список объектов DocumentChunk (с добавленным .score) по убыванию релевантности.
"""
import os
import math


def _is_pgvector() -> bool:
    try:
        from pgvector.django import VectorField  # type: ignore
        from django.db import connection
        return connection.vendor == 'postgresql'
    except Exception:
        return False


def _cosine_sim(a, b) -> float:
    import numpy as np
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom else 0.0


def hybrid_search(query: str, top_k: int = 8, preferred_nds: list = None) -> list:
    from ai_consultant.models import DocumentChunk
    from ai_consultant.services.embeddings import embed_query

    q_vec = embed_query(query)

    def _preferred_boost(c):
        """Повышающий вес для чанков профильных НД выбранного метода НК."""
        if not preferred_nds:
            return 0.0
        doc = getattr(getattr(c, 'source', None), 'doc_number', '') or ''
        title = getattr(getattr(c, 'source', None), 'title', '') or ''
        hay = (doc + ' ' + title).upper()
        for nd in preferred_nds:
            if nd.upper() in hay:
                return 0.35
        return 0.0

    if _is_pgvector():
        from django.contrib.postgres.search import SearchVector, SearchQuery
        from pgvector.django import CosineDistance
        # Полнотекст (BM25-подобно) через to_tsvector на лету
        sv = SearchVector('text', config='russian')
        sq = SearchQuery(query, config='russian')
        fts = DocumentChunk.objects.annotate(search=sv).filter(search=sq)
        # Векторная близость
        vec = DocumentChunk.objects.annotate(
            distance=CosineDistance('embedding', q_vec)
        ).order_by('distance')[:top_k * 2]
        # Объединяем: векторные по distance, fts получают бонус
        fts_ids = set(c.id for c in fts)
        results = []
        for c in vec:
            c.score = 1.0 - float(getattr(c, 'distance', 0))
            if c.id in fts_ids:
                c.score += 0.2
            if getattr(c, 'is_golden', False):
                c.score += 0.5  # приоритет эталонных якорей (обратный инжиниринг)
            # Приоритет справочника Горбачёва (выше, чем Назипов)
            if hasattr(c, 'source') and c.source and c.source.doc_number and 'Горбачёв' in c.source.doc_number:
                c.score += 0.5
            c.score += _preferred_boost(c)
            results.append(c)
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    else:
        # SQLite: numpy cosine + простой текстовый overlap
        chunks = list(DocumentChunk.objects.all())
        results = []
        q_terms = set(query.lower().split())
        for c in chunks:
            emb = c.embedding
            sim = _cosine_sim(q_vec, emb) if emb else 0.0
            text_hit = sum(1 for t in q_terms if t in (c.text or '').lower())
            c.score = sim + 0.1 * text_hit
            if getattr(c, 'is_golden', False):
                c.score += 0.5  # приоритет эталонных якорей
            # Приоритет справочника Горбачёва
            if hasattr(c, 'source') and c.source and c.source.doc_number and 'Горбачёв' in c.source.doc_number:
                c.score += 0.5
            c.score += _preferred_boost(c)
            results.append(c)
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
