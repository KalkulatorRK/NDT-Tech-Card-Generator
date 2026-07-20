"""
ГОСТ Р 50.05.05-2018 «Система оценки соответствия в области использования
атомной энергии. Оценка соответствия в форме контроля. Унифицированные
методики. Ультразвуковой контроль основных материалов (полуфабрикатов)».

ЗАГЛУШКА: в приложенном источнике (ИС «Техэксперт») содержится только
титульная страница без текста стандарта. Структурированные требования
не кодированы — модуль хранит метаданные и явный флаг неполноты.

Источник метаданных: приказ Росстандарта от 27.02.2018 № 101-ст.
"""

from __future__ import annotations

from typing import Optional

# ------------------------------------------------------------------
# Идентификатор документа
# ------------------------------------------------------------------
DOCUMENT_CODE = 'ГОСТ Р 50.05.05-2018'
DOCUMENT_SHORT = 'ГОСТ Р 50.05.05'
DOCUMENT_FULL_NAME = (
    'ГОСТ Р 50.05.05-2018 «Система оценки соответствия в области использования '
    'атомной энергии. Оценка соответствия в форме контроля. Унифицированные '
    'методики. Ультразвуковой контроль основных материалов (полуфабрикатов)»'
)
DOCUMENT_EFFECTIVE_FROM = '2018-03-01'
DOCUMENT_APPROVAL_ORDER = 'приказ Росстандарта от 27.02.2018 № 101-ст'
DOCUMENT_INCOMPLETE = True
DOCUMENT_REPLACES = None

METHOD_CODE = 'УЗК-ОМ'
METHOD_NAME = 'ультразвуковой контроль основных материалов (полуфабрикатов)'
METHOD_NAME_EN = 'Ultrasonic testing of base materials and semi-finished products'

NOTE = (
    'Полный текст ГОСТ Р 50.05.05-2018 в приложенном PDF отсутствует: '
    'доступна только титульная страница (заглушка ИС «Техэксперт: 6 поколение»). '
    'Таблицы, термины, процедуры и числовые нормы в этом модуле намеренно не '
    'заполнены. Для работы требуется официальный текст стандарта.'
)

SCOPE = (
    'Унифицированные методики ультразвукового контроля основных материалов '
    '(полуфабрикатов) в системе оценки соответствия в области использования '
    'атомной энергии (по наименованию стандарта; детали — в полном тексте НД).'
)

# Пустые контейнеры — заполняются после получения полного текста
TERMS: dict[str, dict] = {}
ABBREVIATIONS: dict[str, str] = {}
TABLES: dict[str, list] = {}
TECH_CARD_REQUIRED_ITEMS: tuple[str, ...] = ()


def get_document_info() -> dict:
    """Метаданные документа и статус полноты."""
    return {
        'code': DOCUMENT_CODE,
        'short': DOCUMENT_SHORT,
        'full_name': DOCUMENT_FULL_NAME,
        'effective_from': DOCUMENT_EFFECTIVE_FROM,
        'approval_order': DOCUMENT_APPROVAL_ORDER,
        'incomplete': DOCUMENT_INCOMPLETE,
        'note': NOTE,
        'scope': SCOPE,
        'method_code': METHOD_CODE,
        'method_name': METHOD_NAME,
    }


def is_data_available() -> bool:
    """False — модуль-заглушка без содержательных таблиц."""
    return not DOCUMENT_INCOMPLETE


def format_incompleteness_notice() -> str:
    """Текст для RAG/tools: явное предупреждение о неполноте."""
    return (
        f'{DOCUMENT_CODE}: модуль содержит только метаданные титульного листа. '
        f'{NOTE} '
        f'Утверждён {DOCUMENT_APPROVAL_ORDER}, введён с {DOCUMENT_EFFECTIVE_FROM}. '
        f'Область (кратко): {SCOPE}'
    )


def format_scope() -> str:
    return f'{DOCUMENT_CODE}, область применения (по наименованию): {SCOPE}'


def get_table(_table_id: str) -> Optional[list]:
    """Таблицы недоступны в заглушке."""
    return TABLES.get(_table_id)


def all_kb_chunks() -> list[tuple[str, str]]:
    """1–2 чанка: неполнота источника и официальное наименование."""
    return [
        (
            'статус модуля — неполный текст НД',
            format_incompleteness_notice(),
        ),
        (
            'титульный лист — наименование и дата введения',
            (
                f'{DOCUMENT_FULL_NAME}. '
                f'Утверждён и введён в действие {DOCUMENT_APPROVAL_ORDER}. '
                f'Дата введения: {DOCUMENT_EFFECTIVE_FROM}. '
                f'Метод: {METHOD_CODE} — {METHOD_NAME}. '
                f'Структурированные требования (таблицы, процедуры, нормы) '
                f'в модуль не перенесены: полный текст стандарта отсутствовал '
                f'во вложении.'
            ),
        ),
    ]
