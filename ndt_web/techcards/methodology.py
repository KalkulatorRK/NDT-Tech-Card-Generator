"""Профили методических документов РГК.

Выбор документа на экране «Метод» задаёт doc_code в URL/сессии.
От профиля зависят: подписи схем, ссылки в техкарте, тексты подсказок.
Внутренние коды схем (5a, 5g, …) общие — совпадает геометрия расчёта.
"""
from __future__ import annotations

from dataclasses import dataclass


DOC_GOST_50_05_07 = 'ГОСТ Р 50.05.07-2018'
DOC_GOST_7512 = 'ГОСТ 7512-82'


@dataclass(frozen=True)
class MethodologyProfile:
    """Параметры методики для UI и генератора."""

    code: str
    short_name: str
    scheme_label_style: str  # '50_05_07' | '7512'
    # Использовать табл. Б ГОСТ Р 50.05.07 для подбора источника/плёнки
    use_table_b_sources: bool
    # Чувствительность K по категориям НП-105 (АЭУ)
    use_np105_sensitivity: bool
    method_doc_cite: str
    film_help: str
    scheme_help: str


PROFILE_50_05_07 = MethodologyProfile(
    code=DOC_GOST_50_05_07,
    short_name='ГОСТ Р 50.05.07',
    scheme_label_style='50_05_07',
    use_table_b_sources=True,
    use_np105_sensitivity=True,
    method_doc_cite=DOC_GOST_50_05_07,
    film_help=(
        'Допустимые плёнки по табл. Б ГОСТ Р 50.05.07-2018 '
        'для выбранного источника и радиационной толщины.'
    ),
    scheme_help=(
        'Выберите схему по типу объекта (обозначения прил. Г ГОСТ Р 50.05.07-2018). '
        'Для трубопроводов — чертежи 3а–3и. Для плоских деталей — Чертёж 2.'
    ),
)

PROFILE_7512 = MethodologyProfile(
    code=DOC_GOST_7512,
    short_name='ГОСТ 7512',
    scheme_label_style='7512',
    # Табл. Б 50.05.07 — удобный инженерный справочник источников/плёнок;
    # для общей отрасли 7512 не запрещает те же источники (ГОСТ 20426 и др.).
    use_table_b_sources=True,
    # K задаётся ТД на изделие / заказчиком (п. 6.x ГОСТ 7512); НП-105 — опция для АЭУ.
    use_np105_sensitivity=True,
    method_doc_cite=DOC_GOST_7512,
    film_help=(
        'Плёнки подбираются по радиационной толщине и источнику '
        '(справочно — диапазоны табл. Б ГОСТ Р 50.05.07-2018; '
        'методика контроля — ГОСТ 7512-82).'
    ),
    scheme_help=(
        'Выберите схему по ГОСТ 7512-82 (черт. 4, 5а–5з, 6). '
        'Для трубопроводов — черт. 5а–5з. Для плоских деталей — черт. 4.'
    ),
)

_PROFILES = {
    DOC_GOST_50_05_07: PROFILE_50_05_07,
    DOC_GOST_7512: PROFILE_7512,
}


def normalize_doc_code(doc_code: str | None) -> str:
    """Нормализует код документа из URL/сессии."""
    code = (doc_code or '').strip()
    if not code:
        return DOC_GOST_50_05_07
    if '7512' in code:
        return DOC_GOST_7512
    if '50.05.07' in code or '50.05.07' in code.replace(' ', ''):
        return DOC_GOST_50_05_07
    return code


def get_methodology(doc_code: str | None) -> MethodologyProfile:
    """Профиль методики по коду документа (кнопка выбора)."""
    key = normalize_doc_code(doc_code)
    return _PROFILES.get(key, PROFILE_50_05_07)


def is_gost_7512(doc_code: str | None) -> bool:
    return normalize_doc_code(doc_code) == DOC_GOST_7512
