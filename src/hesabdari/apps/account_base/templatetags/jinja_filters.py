from django import template

register = template.Library()

@register.filter
def toman(value):
    try:
        value = int(value)
        return f"{value:,} تومن"
    except (ValueError, TypeError):
        return value