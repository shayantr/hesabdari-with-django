from django import template

register = template.Library()

@register.filter
def toman(value):
    try:
        value = int(value)
        return f"{value:,}"
    except (ValueError, TypeError):
        return value
