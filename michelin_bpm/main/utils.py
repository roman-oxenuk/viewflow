# -*- coding: utf-8 -*-
import json
import requests
from urllib.parse import urljoin
import xlrd
from xlutils.filter import process, XLRDReader, XLWTWriter

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.encoding import force_text
from django.utils.formats import localize
from django.utils.functional import Promise


class LazyEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return force_text(obj)
        return super(LazyEncoder, self).default(obj)


class LocalizeEncoder(LazyEncoder):
    """Сериализует дату, время, числа в локализованном формате"""

    def default(self, obj):
        before = obj
        obj = localize(obj, True)
        if before != obj:
            return force_text(obj)
        return super(LocalizeEncoder, self).default(obj)


class AgoraMailerClient:
    """
    Encapsulates a routine interaction with Mailer API.

    >>> mailer = AgoraMailerClient('api_key', 'https://mailer.ru')
    >>> response = mailer.send('marfa-password-reset-complete-en', 'admin@yandex.ru', {'context': '-'})
    """

    def __init__(self, api_key: str='', root_url: str=''):
        self.api_key = api_key or getattr(settings, 'DB_MAILER_API_KEY', None)
        assert self.api_key, 'Where is my API Key?'

        self.root_url = root_url or getattr(settings, 'DB_MAILER_ROOT_URL', None)
        assert self.api_key, 'Where is my root url?'

        self.send_api_url = urljoin(self.root_url, '/dbmail/api/')

    def send(self, slug: str, recipient: str, from_email: str, context: dict):
        bundle = {
            'data': json.dumps(context, cls=LocalizeEncoder),
            'api_key': self.api_key,
            'recipient': recipient,
            'from_email': from_email,
            'slug': slug
        }
        response = requests.post(self.send_api_url, bundle)
        assert response.text == 'OK', 'Email send failed'
        return response


def render_excel_template(template_path, context, filename):
    """Заполняет excel-шаблон данными из контекста и сохраняет результат в файл."""
    def copy2(wb):
        w = XLWTWriter()
        process(XLRDReader(wb, 'unknown.xls'), w)
        return w.output[0][1], w.style_list

    rdbook = xlrd.open_workbook(template_path, formatting_info=True)
    sheet_name = 'Main list'
    rdsheet = rdbook.sheet_by_name(sheet_name)
    wtbook, style_list = copy2(rdbook)
    wtsheet = wtbook.get_sheet(sheet_name)
    for pos, value in context.items():
        rowx, colx = pos
        xf_index = rdsheet.cell_xf_index(rowx, colx)
        if not value:
            value = ''
        wtsheet.write(rowx, colx, str(value), style_list[xf_index])
    wtbook.save(filename)
