# -*- coding: utf-8 -*-
"""
Django settings for demo project.

Generated by 'django-admin startproject' using Django 1.11.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""
import os
import environ


root = environ.Path(__file__) - 2 # two folder back
env = environ.Env(      # set default values and casting
    DEBUG=(bool, False),
    DEBUG_SQL=(bool, False),
    ALLOWED_HOSTS=(list, []),
    INTERNAL_IPS=(list, [])
)
environ.Env.read_env(env_file=os.path.join(str(root), '.env')) # reading .env file

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '5$7x$_pz3g-==zzc@n!d63o392)^(jqc^@1^sgu3v6&nzwfkko'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')
DEBUG_SQL = env('DEBUG_SQL')
INTERNAL_IPS = env('INTERNAL_IPS')

ALLOWED_HOSTS = env('ALLOWED_HOSTS')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    'viewflow',
    'viewflow.frontend',
    'reversion',
    'reversion_compare',
]

# Project apps
INSTALLED_APPS += [
    'michelin_bpm.main',
    'material',
    'material.frontend',
    'michelin_bpm.main.apps.MichelinBPMFrontendConfig',
]

if DEBUG:
    INSTALLED_APPS += [
        'debug_toolbar',
    ]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG:
    MIDDLEWARE += [
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    ]


ROOT_URLCONF = 'michelin_bpm.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ]
        }
    }
]

# if DEBUG:
#     TEMPLATES[0]['APP_DIRS'] = False
#     TEMPLATES[0]['OPTIONS']['loaders'] = [
#         'django.template.loaders.filesystem.Loader',
#         'django.template.loaders.app_directories.Loader',
#     ]

WSGI_APPLICATION = 'michelin_bpm.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#     }
# }
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': env('DJANGO_DB_NAME'),
        'USER': env('DJANGO_DB_USER'),
        'PASSWORD': env('DJANGO_DB_PASSWORD', default=''),
        'HOST': 'localhost',
    }
}

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    # {
    #     'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    # },
]

if DEBUG_SQL:
    LOGGING = {
        'version': 1,
        'filters': {
            'require_debug_true': {
                '()': 'django.utils.log.RequireDebugTrue',
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'filters': ['require_debug_true'],
                'class': 'logging.StreamHandler',
            }
        },
        'loggers': {
            'django.db.backends': {
                'level': 'DEBUG',
                'handlers': ['console'],
            }
        }
    }


PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
]


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

from django.utils.translation import ugettext_lazy as l_
LANGUAGE_CODE = 'ru'
LANGUAGES = [
    ('en', l_('English')),
    ('ru', l_('Russian')),
]
LOCALE_PATHS = (os.path.join(os.path.dirname(__file__), '..', 'locale'),)

FORMAT_MODULE_PATH = [
    'michelin_bpm.main.formats',
]


TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

SITE_ID = 1

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'


STATIC_ROOT = os.environ.get('STATIC_ROOT', '/mnt/resource/michelin-bpm/static')
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', '/mnt/resource/michelin-bpm/')

# Данные для мейлера
# http://confluence.centrobit.ru/pages/viewpage.action?pageId=8816460
DB_MAILER_API_KEY = 'd84f32d0-6351-4f5a-b771-b074d5d4'
DB_MAILER_ROOT_URL = 'http://mail1.centrobit.ru'
DEFAULT_FROM_EMAIL = 'info@centrobit.ru'

# id группы Клиентов
CLIENTS_GROUP_ID = 1
