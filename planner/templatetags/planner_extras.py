from django import template

register = template.Library()


@register.filter
def get_item(d, key):
    if d is None:
        return None
    return d.get(key)


@register.filter
def minutes_to_hm(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    h, m = divmod(value, 60)
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"
