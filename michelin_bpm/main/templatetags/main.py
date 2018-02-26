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


@register.filter
def has_attr(obj, key):
    if hasattr(obj, key):
        return True
    return False


@register.assignment_tag
def check_is_client(user):
    return user.groups.filter(name='Клиенты').exists()


@register.assignment_tag
def check_is_form_with_correction_field(form):
    return bool([
        field for name, field in form.fields.items()
        if 'data-correction-field' in field.widget.attrs
    ])


@register.filter
def remove_required(field):
    field.field.required = False
    return field
