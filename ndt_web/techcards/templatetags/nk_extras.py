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
def subtract(value, arg):
    """Вычитание двух чисел."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0
