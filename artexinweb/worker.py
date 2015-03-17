# -*- coding: utf-8 -*-
from artexinweb.decorators import registered
from artexinweb.settings import huey


@huey.task()
def dispatch(message):
    try:
        handlers = registered.handlers[message.pop('type', None)]
    except KeyError:
        pass
    else:
        for hander_func in handlers:
            hander_func(message)
