"""
Дополнительные шаблонные теги и фильтры для приложения НК-Карта.
"""

from django import template

register = template.Library()


@register.filter
def index(lst, i):
    """Возвращает элемент списка по индексу."""
    try:
        return lst[i]
    except (IndexError, TypeError):
        return None


@register.filter
def radiographic_reference(value):
    """Ссылка на НД без табл./п. 4.6 для радиографической оценки."""
    from quality.assessor import _sanitize_radiographic_reference
    return _sanitize_radiographic_reference(value)


@register.filter
def subtract(value, arg):
    """Вычитание двух чисел."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0
