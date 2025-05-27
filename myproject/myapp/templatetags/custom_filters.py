# myapp/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''
    
def dict_get(d, key):
    return d.get(key)

@register.filter
def dict_get(dict_obj, key):
    return dict_obj.get(key)

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0)