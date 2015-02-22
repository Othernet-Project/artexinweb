# -*- coding: utf-8 -*-
import datetime
import json
import os
import urllib

from unittest import mock

from artexinweb import utils
from artexinweb.handlers.standalone import StandaloneHandler
from artexinweb.models import Task
from artexinweb.tests.base import BaseMongoTestCase
from artexinweb.tests.mocks import mock_bottle_config


class TestStandaloneHandler(BaseMongoTestCase):

    @classmethod
    def setup_class(cls):
        cls.job_id = 'a' * 32
        cls.target = '/srv/media/lalala'
        cls.origin = 'http://en.wikipedia.org/wiki/Prime_factor'

    @mock.patch('os.path.exists')
    def test_is_valid_target_success(self, exists):
        exists.return_value = True

        handler = StandaloneHandler()
        result = handler.is_valid_target(self.target)

        assert result is True
        exists.assert_called_once_with(self.target)

    @mock.patch('os.path.exists')
    def test_is_valid_target_failure(self, exists):
        exists.return_value = False

        handler = StandaloneHandler()
        result = handler.is_valid_target(self.target)

        assert result is False
        exists.assert_called_once_with(self.target)

    @mock.patch('artexin.pack.zipdir')
    @mock.patch('shutil.rmtree')
    @mock.patch('shutil.copytree')
    @mock.patch('tempfile.mkdtemp')
    def test_zip_files(self, mkdtemp, copytree, rmtree, zipdir):
        temp_dir = '/tmp/something'
        mkdtemp.return_value = temp_dir
        zip_filename = 'some_hash'

        mock_settings = {'artexin.out_dir': '/test/out'}

        handler = StandaloneHandler()
        with mock_bottle_config('artexinweb.settings.BOTTLE_CONFIG',
                                mock_settings):
            result = handler.zip_files(self.target, zip_filename)

        zip_file_path = os.path.join(mock_settings['artexin.out_dir'],
                                     '{0}.zip'.format(zip_filename))

        assert result == zip_file_path

        zippable_dir = os.path.join(temp_dir, zip_filename)

        copytree.assert_called_once_with(self.target, zippable_dir)
        rmtree.assert_called_once_with(temp_dir)
        zipdir.assert_called_once_with(zip_file_path, zippable_dir)

    @mock.patch('os.stat')
    @mock.patch('artexin.pack.serialize_datetime')
    @mock.patch('artexinweb.handlers.standalone.StandaloneHandler.zip_files')
    @mock.patch('artexinweb.handlers.standalone.StandaloneHandler.count_images')  # NOQA
    @mock.patch('artexinweb.handlers.standalone.StandaloneHandler.read_title')
    def test_handle_task(self, read_title, count_images, zip_files,
                         serialize_datetime, stat):
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

        read_title.return_value = expected_meta['title']
        count_images.return_value = expected_meta['images']
        serialize_datetime.return_value = expected_meta['timestamp']
        zip_files.return_value = zip_file_path

        stat_result = mock.Mock()
        stat_result.st_size = st_size
        stat.return_value = stat_result

        m_open = mock.mock_open()
        with mock.patch('builtins.open', m_open):
            result = handler.handle_task(task, options)

        info_path = os.path.join(task.target, 'info.json')
        m_open.assert_called_once_with(info_path, 'w', encoding='utf-8')

        info_contents = json.dumps(expected_meta, indent=2)
        file_handle = m_open()
        file_handle.write.assert_called_once_with(info_contents)

        read_title.assert_called_once_with(task.target)
        count_images.assert_called_once_with(task.target)
        zip_files.assert_called_once_with(task.target,
                                          zip_filename=origin_hash)
        stat.assert_called_once_with(zip_file_path)

        assert len(result) == 7

        for key in ('title', 'images', 'url', 'domain'):
            assert result[key] == expected_meta[key]

        assert result['size'] == st_size
        assert result['hash'] == origin_hash
        assert isinstance(result['timestamp'], datetime.datetime)

    @mock.patch('artexinweb.models.Task.mark_finished')
    def test_handle_task_result(self, mark_finished):
        task = Task.create(self.job_id, self.target)

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

    @mock.patch('os.walk')
    @mock.patch('imghdr.what')
    def test_count_images(self, what, walk):
        image_paths = [(None, None, ['test.gif']),
                       (None, None, ['another.jpg']),
                       (None, None, ['catch.jpg'])]
        walk.return_value = image_paths
        what.return_value = True

        handler = StandaloneHandler()
        result = handler.count_images(self.target)

        assert result == len(image_paths)

    @mock.patch('artexin.extract.get_title')
    @mock.patch('bs4.BeautifulSoup')
    @mock.patch('os.listdir')
    def test_read_title(self, listdir, beautiful_soup, get_title):
        listdir.return_value = ['test.jpg',
                                'another.gif',
                                'script.js',
                                'start.html']
        title = 'page title'
        get_title.return_value = title
        beautiful_soup.return_value = 'soup'

        handler = StandaloneHandler()

        m_open = mock.mock_open()
        with mock.patch('builtins.open', m_open):
            result = handler.read_title(self.target)

        html_path = os.path.join(self.target, 'start.html')
        m_open.assert_called_once_with(html_path, 'r')

        file_handle = m_open()
        file_handle.read.assert_called_once_with()

        get_title.assert_called_once_with(beautiful_soup.return_value)

        assert result == title
