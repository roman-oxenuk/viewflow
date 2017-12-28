"""
WSGI config for michelin_bpm project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/howto/deployment/wsgi/
"""

import os
from os.path import join, dirname
from dotenv import load_dotenv

from django.core.wsgi import get_wsgi_application


dotenv_path = join(dirname(__file__), '..', '.env')
load_dotenv(dotenv_path, override=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "michelin_bpm.settings")

application = get_wsgi_application()
