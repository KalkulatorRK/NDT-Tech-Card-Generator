"""Форматирование количества кредитов (1 кредит = 1 техкарта НК)."""


def credit_word(count: int) -> str:
    """Склонение слова «кредит» для целого числа."""
    n = abs(int(count))
    if n % 10 == 1 and n % 100 != 11:
        return 'кредит'
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return 'кредита'
    return 'кредитов'


def format_credits(count: int) -> str:
    """Возвращает строку вида «5 кредитов»."""
    return f'{count} {credit_word(count)}'
