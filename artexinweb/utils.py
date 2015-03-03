# -*- coding: utf-8 -*-
import hashlib
import os
import pkgutil

import babel


def discover(package):
    modules = pkgutil.iter_modules(package.__path__)

    for (module_finder, name, ispkg) in modules:
        __import__('.'.join([package.__name__, name]))


def hash_data(*args):
    md5 = hashlib.md5()

    for data in args:
        md5.update(bytes(str(data), 'utf-8'))

    return md5.hexdigest()


def get_extension(filepath):
    return os.path.splitext(filepath)[-1].strip(".").lower()


def collect_locales():
    """Collects all the languages supported by Babel.

    :returns:  list of (language_code, language_name) tuples"""
    languages = []

    for lang_code in babel.localedata.locale_identifiers():
        locale = babel.Locale(lang_code)
        if locale.english_name:
            if (not locale.display_name or
                    locale.display_name == locale.english_name):
                label = locale.english_name
            else:
                label = '{0} ({1})'.format(locale.display_name,
                                           locale.english_name)

            languages.append((lang_code, label))

    return languages
