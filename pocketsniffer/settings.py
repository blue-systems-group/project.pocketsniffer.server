"""
Django settings for pocketsniffer project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import sys
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DATA_DIR = os.path.join(BASE_DIR, 'data')
MANIFEST_DIR = os.path.join(BASE_DIR, 'manifests')
LOG_DIR = os.path.join(BASE_DIR, 'logs/django')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATIC_ROOT = os.path.join(BASE_DIR, 'static')


PUBLIC_TCP_PORT = 7654
PUBLIC_BACKLOG = 10
PUBLIC_IFACE = 'eth0'
CONNECTION_TIMEOUT_SEC = 5
READ_TIMEOUT_SEC = 300
BUF_SIZE = 16*1024


SHELL_PLUS = 'ipython'

BAND2G_CHANNELS = [1, 6, 11]
BAND5G_CHANNELS = range(36, 49, 4) + range(149, 166, 4)

SHELL_PLUS_PRE_IMPORTS = (
    ('collections', 'Counter'),
    ('datetime', ('datetime')),
    'json',
    )

AP_HEARTBEAT_INTERVAL = 300



# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'oc%v)7-5wc^k8c8s%194tr35g6@zf(kriersaykbpjire6cx%x'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'djcelery',
    'apps.backend',
    'apps.controller',
    )

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    )

CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend'
BROKER_URL = 'amqp://guest:guest@localhost:5672//'

ROOT_URLCONF = 'pocketsniffer.urls'

WSGI_APPLICATION = 'pocketsniffer.wsgi.application'

BACKEND_LOCK_DEFAULTS = {
    None : {
      'length': datetime.timedelta(minutes=2),
      'timeout': datetime.timedelta(minutes=1),
      'sleep': datetime.timedelta(seconds=1),
      'block': True,
      },
    'upload': {
      'length': datetime.timedelta(minutes=2),
      'timeout': datetime.timedelta(minutes=1),
      'sleep': datetime.timedelta(seconds=1),
      'block': True,
      },
    'logcat': {
      'length': datetime.timedelta(minutes=5),
      'timeout': datetime.timedelta(minutes=5),
      'sleep': datetime.timedelta(seconds=30),
      'block': True,
      },
    'import': {
      'length': datetime.timedelta(minutes=2),
      'timeout': datetime.timedelta(minutes=1),
      'sleep': datetime.timedelta(seconds=1),
      'block': True,
      },
    'collector' : {
      'length': datetime.timedelta(seconds=10),
      'timeout': datetime.timedelta(seconds=60),
      'sleep': datetime.timedelta(seconds=1),
      'block': True,
      },
    }




# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
      'ENGINE': 'django.db.backends.postgresql_psycopg2',
      'NAME': 'pocketsniffer',
      'USER': 'pocketsniffer',
      'PASSWORD': 'pocketsniffer',
      'HOST': '127.0.0.1',
      'PORT': '5432',  
      }
    }



# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'

# Logging

DEBUG_FILE = os.path.join(LOG_DIR, "debug.log")
try:
  f = open(DEBUG_FILE, 'ab')
  f.close()
except Exception, e:
  sys.stderr.write("Error opening debug log file %s: %s. Debug logs will not be saved." % (DEBUG_FILE, e,))
  DEBUG_FILE = "/dev/null"

ERROR_FILE = os.path.join(LOG_DIR, "error.log")
try:
  f = open(ERROR_FILE, 'ab')
  f.close()
except Exception, e:
  sys.stderr.write("Error opening error log file %s: %s. Error logs will not be saved." % (ERROR_FILE, e,))
  ERROR_FILE = "/dev/null"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
      'standard': {
        'format' : "[%(asctime)s] %(levelname)8s [%(module)10s.py:%(lineno)3s] %(message)s",
        'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
      },
    'handlers': {
      'null': {
        'level':'DEBUG',
        'class':'django.utils.log.NullHandler',
        },
      'console_debug':{
        'level':'DEBUG',
        'class':'logging.StreamHandler',
        'formatter': 'standard',
        'stream': sys.stderr,
        },
      'console_error':{
        'level':'ERROR',
        'class':'logging.StreamHandler',
        'formatter': 'standard',
        'stream': sys.stdout,
        },
      'file_debug': {
        'level':'DEBUG',
        'class':'logging.handlers.RotatingFileHandler',
        'filename': DEBUG_FILE,
        'maxBytes': 1024 * 1024,
        'backupCount': 4,
        'formatter': 'standard',
        },
      'file_error': {
        'level':'ERROR',
        'class':'logging.handlers.RotatingFileHandler',
        'filename': ERROR_FILE,
        'maxBytes': 1024 * 1024,
        'backupCount': 32,
        'formatter': 'standard',
        },
      },
    'loggers': {
      'django': {
        'handlers':['console_error', 'file_error', 'console_debug', 'file_debug'],
        'level':'WARN',
        'propagate': True,
        },
      'django.db.backends': {
        'handlers':['console_error', 'file_error', 'console_debug', 'file_debug'],
        'level': 'INFO',
        'propagate': False,
        },
      'backend': {
        'handlers':['console_error', 'file_error', 'console_debug', 'file_debug'],
        'level': 'DEBUG',
        'propagate': True,
        },
      'controller': {
        'handlers':['console_error', 'file_error', 'console_debug', 'file_debug'],
        'level': 'DEBUG',
        'propagate': True,
        },
      'subdomains.middleware': {
        'handlers': ['console_error', 'file_error', 'console_debug', 'file_debug'],
        'level': 'ERROR',
        'propagate': True,
        }
      }
    }



# Local settings
from local_settings import *
