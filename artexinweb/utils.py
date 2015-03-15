# -*- coding: utf-8 -*-
import hashlib
import os
import pkgutil
import shutil
import tempfile
import zipfile

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
                label = '{0} ({1})'.format(locale.english_name,
                                           locale.display_name)

            languages.append((lang_code, label))

    return sorted(languages, key=lambda x: x[1])


def list_zipfile(zip_filepath):
    with zipfile.ZipFile(zip_filepath, 'r') as zf:
        return zf.namelist()


def unzip(source_filename, dest_dir):
    with zipfile.ZipFile(source_filename) as zf:
        for member in zf.infolist():
            # Path traversal defense copied from
            # http://hg.python.org/cpython/file/tip/Lib/http/server.py#l765
            words = member.filename.split('/')
            path = dest_dir

            for word in words[:-1]:
                drive, word = os.path.splitdrive(word)
                head, word = os.path.split(word)
                if word in (os.curdir, os.pardir, ''):
                    continue
                path = os.path.join(path, word)

            zf.extract(member, path)


def remove_from_zip(zip_filepath, *removables):
    """Repack a zip archive without the files specified in `removables`.

    :param zip_filepath:  Full path to the repackable zip file
    :param *removables:   Filenames to be removed from the source zipfile
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        tmp_zipfile = os.path.join(tmp_dir, 'tmp.zip')
        with zipfile.ZipFile(zip_filepath, 'r') as zip_read:
            with zipfile.ZipFile(tmp_zipfile, 'w') as zip_write:
                for item in zip_read.infolist():
                    if item.filename not in removables:
                        data = zip_read.read(item.filename)
                        zip_write.writestr(item, data)

        shutil.move(tmp_zipfile, zip_filepath)
    finally:
        shutil.rmtree(tmp_dir)


def replace_in_zip(zip_filepath, **replacements):
    """Replace the files specified in `replacements` in a zip file.

    :param zip_filepath:    Full path to the zip file
    :param **replacements:  Filename / data pairs
    """
    remove_from_zip(zip_filepath, *replacements.keys())
    with zipfile.ZipFile(zip_filepath, 'a') as zip_write:
        for filename, data in replacements.items():
            zip_write.writestr(filename, data)
