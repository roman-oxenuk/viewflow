# -*- coding: utf-8 -*-
import json
import requests
from urllib.parse import urljoin

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
