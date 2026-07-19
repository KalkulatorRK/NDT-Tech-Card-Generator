"""Классификация источников: цитируемые НД vs справочная литература."""

from __future__ import annotations

import re

# Признаки справочников / учебников (не цитировать в ответах)
_TEXTBOOK_MARKERS = (
    'ГОРБАЧ', 'НАЗИП', 'УЧЕБНИК', 'УЧЕБНОЕ', 'СПРАВОЧНИК', 'ПОСОБИЕ',
    'МОНОГРАФ', 'АВТОРСК',
)

_ND_DOC_TYPES = frozenset({
    'gost', 'np', 'sto', 'rd', 'pnae', 'sp', 'sanpin', 'federal',
})

_ND_NUMBER_RE = re.compile(
    r'(ГОСТ|НП[\s\-]|РД[\s\-]|СТО[\s\-]|ПНАЭ|СП[\s\-]|СанПиН|ФЗ[\s\-])',
    re.IGNORECASE,
)


def _haystack(source) -> str:
    doc_number = getattr(source, 'doc_number', '') or ''
    title = getattr(source, 'title', '') or ''
    return f'{doc_number} {title}'.upper()


def is_textbook_source(source) -> bool:
    """True для учебников/справочников (Горбачёв, Назипов и т.п.)."""
    if source is None:
        return False
    doc_type = (getattr(source, 'doc_type', '') or '').lower().strip()
    if doc_type in ('textbook', 'book', 'manual', 'reference'):
        return True
    hay = _haystack(source)
    return any(m in hay for m in _TEXTBOOK_MARKERS)


def is_citable_nd_source(source) -> bool:
    """True только для ГОСТ, НП, РД, СТО и прочих НД — их можно цитировать."""
    if source is None or is_textbook_source(source):
        return False
    doc_type = (getattr(source, 'doc_type', '') or '').lower().strip()
    if doc_type in _ND_DOC_TYPES:
        return True
    hay = _haystack(source)
    if _ND_NUMBER_RE.search(hay):
        return True
    # «other», но номер похож на НД
    num = (getattr(source, 'doc_number', '') or '').upper()
    return bool(re.search(r'ГОСТ|НП-|РД-|СТО|ПНАЭ', num))
