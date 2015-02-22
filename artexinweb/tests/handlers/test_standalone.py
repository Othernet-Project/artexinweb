# -*- coding: utf-8 -*-
import datetime
import os

from unittest import mock

from artexinweb.handlers.standalone import StandaloneHandler
from artexinweb.models import Task
from artexinweb.tests.base import BaseMongoTestCase
from artexinweb.tests.mocks import mock_bottle_config


class TestStandaloneHandler(BaseMongoTestCase):

    @classmethod
    def setup_class(cls):
        cls.job_id = 'a' * 32
        cls.target = '/srv/media/lalala'

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
