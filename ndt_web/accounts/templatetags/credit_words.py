from django import template

from accounts.credits import credit_word

register = template.Library()


@register.filter
def credit_word_filter(count):
    """Склонение: {{ n|credit_word_filter }} → кредит / кредита / кредитов."""
    try:
        return credit_word(int(count))
    except (TypeError, ValueError):
        return 'кредитов'
