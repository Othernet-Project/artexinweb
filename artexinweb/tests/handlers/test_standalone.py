# -*- coding: utf-8 -*-
import datetime
import os
import urllib

from unittest import mock

import pytest

from artexinweb import exceptions
from artexinweb.handlers.standalone import StandaloneHandler
from artexinweb.models import Task
from artexinweb.tests.base import BaseMongoTestCase
from artexinweb.tests.mocks import mock_bottle_config


class TestStandaloneHandler(BaseMongoTestCase):

    @classmethod
    def setup_class(cls):
        cls.job_id = 'a' * 32
        cls.target = '/srv/media/lalala/somefile.zip'
        cls.temp_dir = '/tmp/random_tmp'
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

    @mock.patch('tempfile.mkdtemp')
    @mock.patch('artexinweb.handlers.standalone.StandaloneHandler.get_extractor')  # NOQA
    def test_extract_target(self, get_extractor, mkdtemp):
        extractor = mock.Mock()
        get_extractor.return_value = extractor

        mkdtemp.return_value = '/tmp/some_folder'

        handler = StandaloneHandler()
        handler.extract_target(self.target)

        dest_dir = '/tmp/some_folder'
        get_extractor.assert_called_once_with(self.target)
        extractor.assert_called_once_with(self.target, dest_dir)

    @mock.patch('os.walk')
    @mock.patch('imghdr.what')
    def test_count_images(self, what, walk):
        image_paths = [(None, None, ['test.gif']),
                       (None, None, ['another.jpg']),
                       (None, None, ['catch.jpg'])]
        walk.return_value = image_paths
        what.return_value = True

        handler = StandaloneHandler()
        result = handler.count_images(self.temp_dir)

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
            result = handler.read_title(self.temp_dir)

        html_path = os.path.join(self.temp_dir, expected_html_file)
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

    @mock.patch('shutil.rmtree')
    @mock.patch('artexin.pack.create_zipball')
    @mock.patch('artexinweb.handlers.standalone.StandaloneHandler.count_images')  # NOQA
    @mock.patch('artexinweb.handlers.standalone.StandaloneHandler.read_title')
    @mock.patch('artexinweb.handlers.standalone.StandaloneHandler.extract_target')  # NOQA
    def test_handle_task(self, extract_target, read_title, count_images,
                         create_zipball, shutil_rmtree):
        options = {'origin': self.origin}
        task = Task.create(self.job_id, self.target)

        handler = StandaloneHandler()

        expected_meta = {'title': 'page title',
                         'images': 4,
                         'url': self.origin,
                         'domain': urllib.parse.urlparse(self.origin).netloc}

        extract_target.return_value = self.temp_dir
        read_title.return_value = expected_meta['title']
        count_images.return_value = expected_meta['images']

        def mocked_create_zipball(*args, **kwargs):
            return kwargs['meta']
        create_zipball.side_effect = mocked_create_zipball

        mock_settings = {'artexin.out_dir': '/test/out'}
        with mock_bottle_config('artexinweb.settings.BOTTLE_CONFIG',
                                mock_settings):
            result = handler.handle_task(task, options)

        for call_arg in create_zipball.call_args:
            if isinstance(call_arg, dict):
                assert call_arg['src_dir'] == self.temp_dir
                assert call_arg['out_dir'] == mock_settings['artexin.out_dir']
                for key, value in expected_meta.items():
                    assert call_arg['meta'][key] == value

                assert isinstance(call_arg['meta']['timestamp'],
                                  datetime.datetime)

        extract_target.assert_called_once_with(task.target)
        read_title.assert_called_once_with(self.temp_dir)
        count_images.assert_called_once_with(self.temp_dir)
        shutil_rmtree.assert_called_once_with(self.temp_dir)

        assert len(result) == len(expected_meta) + 1

        for key, value in expected_meta.items():
            assert result[key] == value

        assert isinstance(result['timestamp'], datetime.datetime)

    @mock.patch('artexinweb.models.Task.mark_finished')
    def test_handle_task_result(self, mark_finished):
        task = Task.create(self.job_id, self.temp_dir)

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
