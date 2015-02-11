# -*- coding: utf-8 -*-
from bottle import get, jinja2_view, static_file

from artexinweb import settings


@get('/static/<filename:path>')
def send_static(filename):
    return static_file(filename, root=settings.STATIC_ROOT)


@get('/')
@jinja2_view('index.html')
def index():
    return {}