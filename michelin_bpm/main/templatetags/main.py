from __future__ import unicode_literals

from django import template


register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
