# -*- coding: utf-8 -*-
import datetime
import json
import os
import urllib

from unittest import mock

import pytest

from artexinweb import exceptions, utils
from artexinweb.handlers.standalone import StandaloneHandler
from artexinweb.models import Task
from artexinweb.tests.base import BaseMongoTestCase
from artexinweb.tests.mocks import mock_bottle_config


class TestStandaloneHandler(BaseMongoTestCase):

    @classmethod
    def setup_class(cls):
        cls.job_id = 'a' * 32
        cls.target = '/srv/media/lalala/somefile.zip'
        cls.target_dir = '/tmp/random_tmp/unique_hash'
        cls.origin = 'http://en.wikipedia.org/wiki/Prime_factor'

    def test_is_html_file(self):
        handler = StandaloneHandler()
        assert handler.is_html_file('test.gif') is False
        assert handler.is_html_file('start.html') is True

    @mock.patch('zipfile.ZipFile')
    @mock.patch('os.path.isfile')
    def test_is_valid_target_success(self, isfile, zipfile):
        isfile.return_value = True

        zf = mock.MagicMock()
        zf.namelist.return_value = ['test.jpg', 'index.html']
        context = mock.MagicMock()
        context.__enter__.return_value = zf
        zipfile.return_value = context

        handler = StandaloneHandler()
        result = handler.is_valid_target(self.target)

        assert result is True
        isfile.assert_called_once_with(self.target)

    @mock.patch('os.path.isfile')
    def test_is_valid_target_no_file(self, isfile):
        isfile.return_value = False

        handler = StandaloneHandler()
        result = handler.is_valid_target(self.target)

        assert result is False
        isfile.assert_called_once_with(self.target)

    @mock.patch('zipfile.ZipFile')
    @mock.patch('os.path.isfile')
    def test_is_valid_target_no_html_in_zip(self, isfile, zipfile):
        isfile.return_value = True

        zf = mock.MagicMock()
        zf.namelist.return_value = ['test.jpg', 'readme.txt']
        context = mock.MagicMock()
        context.__enter__.return_value = zf
        zipfile.return_value = context

        handler = StandaloneHandler()
        result = handler.is_valid_target(self.target)

        assert result is False
        isfile.assert_called_once_with(self.target)

    def test_get_extractor_success(self):
        handler = StandaloneHandler()
        for supported_file_type in handler.extractors:
            test_fname = 'some_file.{0}'.format(supported_file_type)
            assert callable(handler.get_extractor(test_fname))

    def test_get_extractor_fail(self):
        handler = StandaloneHandler()
        with pytest.raises(exceptions.TaskHandlingError):
            handler.get_extractor('test.rar')

    @mock.patch('os.makedirs')
    @mock.patch('tempfile.mkdtemp')
    @mock.patch('artexinweb.handlers.standalone.StandaloneHandler.get_extractor')  # NOQA
    def test_extract_target(self, get_extractor, mkdtemp, makedirs):
        extractor = mock.Mock()
        get_extractor.return_value = extractor

        mkdtemp.return_value = '/tmp/some_folder'

        handler = StandaloneHandler()
        handler.extract_target(self.target, 'somehash')

        dest_dir = '/tmp/some_folder/somehash'
        get_extractor.assert_called_once_with(self.target)
        extractor.assert_called_once_with(self.target, dest_dir)
        makedirs.assert_called_once_with(dest_dir)

    @mock.patch('os.walk')
    @mock.patch('imghdr.what')
    def test_count_images(self, what, walk):
        image_paths = [(None, None, ['test.gif']),
                       (None, None, ['another.jpg']),
                       (None, None, ['catch.jpg'])]
        walk.return_value = image_paths
        what.return_value = True

        handler = StandaloneHandler()
        result = handler.count_images(self.target_dir)

        assert result == len(image_paths)

    @mock.patch('artexin.extract.get_title')
    @mock.patch('bs4.BeautifulSoup')
    @mock.patch('os.listdir')
    def _read_title_test(self, file_list, expected_html_file, listdir,
                         beautiful_soup, get_title, ):
        listdir.return_value = file_list
        title = 'page title'
        get_title.return_value = title
        beautiful_soup.return_value = 'soup'

        handler = StandaloneHandler()

        m_open = mock.mock_open()
        with mock.patch('builtins.open', m_open):
            result = handler.read_title(self.target_dir)

        html_path = os.path.join(self.target_dir, expected_html_file)
        m_open.assert_called_once_with(html_path, 'r')

        file_handle = m_open()
        file_handle.read.assert_called_once_with()

        get_title.assert_called_once_with(beautiful_soup.return_value)

        assert result == title

    def test_read_title_precedence(self):
        file_list = ['test.jpg',
                     'start.html',
                     'another.gif',
                     'script.js',
                     'index.html']
        expected_html_file = 'index.html'
        self._read_title_test(file_list, expected_html_file)

    def test_read_title_fallback(self):
        file_list = ['test.jpg',
                     'onlythis.html',
                     'another.gif',
                     'script.js']
        expected_html_file = 'onlythis.html'
        self._read_title_test(file_list, expected_html_file)

    @mock.patch('artexin.pack.zipdir')
    @mock.patch('shutil.rmtree')
    def test_archive_target(self, rmtree, zipdir):
        mock_settings = {'artexin.out_dir': '/test/out'}

        handler = StandaloneHandler()
        with mock_bottle_config('artexinweb.settings.BOTTLE_CONFIG',
                                mock_settings):
            result = handler.archive_target(self.target_dir)

        zip_file_path = os.path.join(mock_settings['artexin.out_dir'],
                                     'unique_hash.zip')

        assert result == zip_file_path

        temp_dir = os.path.dirname(self.target_dir)

        rmtree.assert_called_once_with(temp_dir)
        zipdir.assert_called_once_with(zip_file_path, self.target_dir)

    @mock.patch('os.stat')
    @mock.patch('artexin.pack.serialize_datetime')
    @mock.patch('artexinweb.handlers.standalone.StandaloneHandler.archive_target')  # NOQA
    @mock.patch('artexinweb.handlers.standalone.StandaloneHandler.count_images')  # NOQA
    @mock.patch('artexinweb.handlers.standalone.StandaloneHandler.read_title')
    @mock.patch('artexinweb.handlers.standalone.StandaloneHandler.extract_target')  # NOQA
    def test_handle_task(self, extract_target, read_title, count_images,
                         archive_target, serialize_datetime, stat):
        options = {'origin': self.origin}
        origin_hash = utils.hash_data([self.origin])
        task = Task.create(self.job_id, self.target)

        handler = StandaloneHandler()

        expected_meta = {'title': 'page title',
                         'images': 4,
                         'timestamp': '2015-02-22 12:03:23.778567',
                         'url': self.origin,
                         'domain': urllib.parse.urlparse(self.origin).netloc}
        zip_file_path = '/temp/out/file.zip'
        st_size = 1234

        extract_target.return_value = self.target_dir
        read_title.return_value = expected_meta['title']
        count_images.return_value = expected_meta['images']
        serialize_datetime.return_value = expected_meta['timestamp']
        archive_target.return_value = zip_file_path

        stat_result = mock.Mock()
        stat_result.st_size = st_size
        stat.return_value = stat_result

        m_open = mock.mock_open()
        with mock.patch('builtins.open', m_open):
            result = handler.handle_task(task, options)

        info_path = os.path.join(self.target_dir, 'info.json')
        m_open.assert_called_once_with(info_path, 'w', encoding='utf-8')

        info_contents = json.dumps(expected_meta, indent=2)
        file_handle = m_open()
        file_handle.write.assert_called_once_with(info_contents)

        extract_target.assert_called_once_with(task.target, origin_hash)
        read_title.assert_called_once_with(self.target_dir)
        count_images.assert_called_once_with(self.target_dir)
        archive_target.assert_called_once_with(self.target_dir)
        stat.assert_called_once_with(zip_file_path)

        assert len(result) == 7

        for key in ('title', 'images', 'url', 'domain'):
            assert result[key] == expected_meta[key]

        assert result['size'] == st_size
        assert result['hash'] == origin_hash
        assert isinstance(result['timestamp'], datetime.datetime)

    @mock.patch('artexinweb.models.Task.mark_finished')
    def test_handle_task_result(self, mark_finished):
        task = Task.create(self.job_id, self.target_dir)

        result = {'size': 1234,
                  'hash': 'a' * 32,
                  'title': 'page title',
                  'images': 12,
                  'timestamp': datetime.datetime.utcnow()}

        handler = StandaloneHandler()
        handler.handle_task_result(task, result, {})

        mark_finished.assert_called_once_with()

        assert task.size == result['size']
        assert task.md5 == result['hash']
        assert task.title == result['title']
        assert task.images == result['images']
        assert task.timestamp == result['timestamp']
