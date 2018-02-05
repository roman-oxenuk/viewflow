# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import template


register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def get_attr(obj, key):
    if hasattr(obj, key):
        return getattr(obj, key)
    return None


@register.assignment_tag
def check_is_client(user):
    return user.groups.filter(name='Клиенты').exists()
