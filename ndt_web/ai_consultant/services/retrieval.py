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
    from ai_consultant.services.nd_sources import (
        is_citable_nd_source,
        is_textbook_source,
    )
    from django.db.models import Q

    try:
        q_vec = embed_query(query)
    except Exception:
        # без API-ключа эмбеддингов — только текст + профильные НД
        from ai_consultant.services.embeddings import EMBEDDING_DIM
        q_vec = [0.0] * EMBEDDING_DIM
    preferred_nds = [p for p in (preferred_nds or []) if p]

    def _is_preferred(c) -> bool:
        if not preferred_nds:
            return False
        doc = getattr(getattr(c, 'source', None), 'doc_number', '') or ''
        title = getattr(getattr(c, 'source', None), 'title', '') or ''
        hay = (doc + ' ' + title).upper()
        return any(nd.upper() in hay for nd in preferred_nds)

    def _preferred_boost(c):
        """Сильный буст профильных НД выбранного метода (важнее косинуса)."""
        return 2.5 if _is_preferred(c) else 0.0

    def _source_boost(c) -> float:
        """НД выше справочников; учебники — только вспомогательный фон."""
        src = getattr(c, 'source', None)
        if is_citable_nd_source(src):
            return 0.45
        if is_textbook_source(src):
            return -0.25
        return 0.0

    def _preferred_seed(limit: int) -> list:
        """Гарантированно подтягиваем чанки профильных НД (даже с нулевым embedding)."""
        if not preferred_nds or limit <= 0:
            return []
        q_filter = Q()
        for nd in preferred_nds:
            q_filter |= Q(source__doc_number__icontains=nd) | Q(source__title__icontains=nd)
        qs = DocumentChunk.objects.filter(q_filter).select_related('source')
        # текстовый overlap по запросу — вперёд
        q_terms = [t for t in query.lower().split() if len(t) > 2]
        scored = []
        for c in qs[:400]:
            text = (c.text or '').lower()
            hit = sum(1 for t in q_terms if t in text) if q_terms else 0
            # эталонные чанки из .py обычно короче и полезнее
            label = (c.section_label or '').lower()
            py_bonus = 0.5 if ('табл' in label or 'п.' in label or 'прил' in label) else 0.0
            scored.append((hit + py_bonus, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for _, c in scored[:limit]:
            c.score = 10.0 + _source_boost(c)  # выше обычного RAG
            out.append(c)
        return out

    if _is_pgvector():
        from django.contrib.postgres.search import SearchVector, SearchQuery
        from pgvector.django import CosineDistance
        sv = SearchVector('text', config='russian')
        sq = SearchQuery(query, config='russian')
        fts = DocumentChunk.objects.annotate(search=sv).filter(search=sq)
        vec = DocumentChunk.objects.annotate(
            distance=CosineDistance('embedding', q_vec)
        ).order_by('distance')[:top_k * 3]
        fts_ids = set(c.id for c in fts)
        results = []
        for c in vec:
            c.score = 1.0 - float(getattr(c, 'distance', 0))
            if c.id in fts_ids:
                c.score += 0.2
            if getattr(c, 'is_golden', False):
                c.score += 0.5
            c.score += _source_boost(c)
            c.score += _preferred_boost(c)
            results.append(c)
    else:
        chunks = list(DocumentChunk.objects.select_related('source').all())
        results = []
        q_terms = set(query.lower().split())
        for c in chunks:
            emb = c.embedding
            sim = _cosine_sim(q_vec, emb) if emb else 0.0
            text_hit = sum(1 for t in q_terms if t in (c.text or '').lower())
            c.score = sim + 0.1 * text_hit
            if getattr(c, 'is_golden', False):
                c.score += 0.5
            c.score += _source_boost(c)
            c.score += _preferred_boost(c)
            results.append(c)

    # Профильные НД — в начало (квота ≥ половины top_k)
    seed = _preferred_seed(max(4, top_k // 2 + 2))
    by_id = {c.id: c for c in results}
    for c in seed:
        by_id[c.id] = c
    merged = list(by_id.values())
    merged.sort(key=lambda x: x.score, reverse=True)

    # Если задан preferred — не даём чужим НД вытеснить весь топ
    if preferred_nds:
        pref = [c for c in merged if _is_preferred(c)]
        other = [c for c in merged if not _is_preferred(c)]
        half = max(4, (top_k * 2) // 3)
        ordered = (pref + other)[:top_k] if len(pref) >= half else (pref + other)[:top_k]
        # если pref мало — всё равно ставим их первыми
        if pref:
            rest = [c for c in ordered if c.id not in {p.id for p in pref[:half]}]
            ordered = pref[:half] + rest
            # unique preserve order
            seen = set()
            uniq = []
            for c in ordered:
                if c.id in seen:
                    continue
                seen.add(c.id)
                uniq.append(c)
            return uniq[:top_k]
    return merged[:top_k]
