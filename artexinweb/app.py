# -*- coding: utf-8 -*-
import logging.config

import bottle
import mongoengine

from artexinweb import controllers
from artexinweb import handlers
from artexinweb import settings
from artexinweb import utils


huey = settings.huey  # aliasing
logging.config.dictConfig(settings.LOGGING)

bottle.TEMPLATE_PATH.insert(0, settings.VIEW_ROOT)

application = bottle.default_app()
application.config.load_dict(settings.BOTTLE_CONFIG)

mongoengine.connect('', host=application.config['database.url'])

utils.discover(controllers)
utils.discover(handlers)


if __name__ == '__main__':
    application.run(debug=True, reloader=True, host='0.0.0.0', port=9090)
