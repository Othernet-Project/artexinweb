# -*- coding: utf-8 -*-
import sys

from os import environ
from os.path import dirname, join

import bottle

from artexinweb import exceptions


is_test_mode = lambda: ('py.test' in sys.argv or
                        sys.argv[0].endswith('py.test') or
                        sys.argv[0].endswith('py/test.py'))

WEBAPP_ROOT = dirname(__file__)
VIEW_ROOT = join(WEBAPP_ROOT, 'views')
DEV_STATIC_ROOT = join(WEBAPP_ROOT, 'static')

DEFAULT_CONFIG_PATH = join(WEBAPP_ROOT, 'confs', 'dev.ini')
CONFIG_PATH = environ.get('CONFIG_PATH', DEFAULT_CONFIG_PATH)

BOTTLE_CONFIG = bottle.ConfigDict()
BOTTLE_CONFIG.load_config(CONFIG_PATH)

if not BOTTLE_CONFIG and not is_test_mode():
    raise exceptions.ImproperlyConfigured('Empty or no configuration found.')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(process)s] [%(levelname)s] %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': True
        }
    }
}
