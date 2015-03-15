# -*- coding: utf-8 -*-
import datetime

from unittest import mock

from artexinweb.handlers.fetchable import FetchableHandler
from artexinweb.models import Task
from artexinweb.tests.base import BaseMongoTestCase
from artexinweb.tests.mocks import mock_bottle_config


class TestFetchableHandler(BaseMongoTestCase):

    @classmethod
    def setup_class(cls):
        cls.job_id = 'a' * 32
        cls.target = 'http://en.wikipedia.org/wiki/Prime_factor'

    @mock.patch('urllib.request.urlopen')
    def test_is_valid_target_success(self, urlopen):
        target = 'http://www.target.com'
        handler = FetchableHandler()
        result = handler.is_valid_target(target)

        assert result is True
        urlopen.assert_called_once_with(target)

    @mock.patch('urllib.request.urlopen')
    def test_is_valid_target_failure(self, urlopen):
        target = 'http://www.target.com'
        urlopen.side_effect = Exception()

        handler = FetchableHandler()
        result = handler.is_valid_target(target)

        assert result is False
        urlopen.assert_called_once_with(target)

    @mock.patch('artexinweb.models.Task.mark_finished')
    @mock.patch('artexinweb.models.Task.mark_failed')
    def test_handle_task_result_failure(self, mark_failed, mark_finished):
        task = Task.create(self.job_id, self.target)
        result = {'error': 'something went wrong'}
        options = {}

        handler = FetchableHandler()
        handler.handle_task_result(task, result, options)

        assert not mark_finished.called
        assert mark_failed.call_count == 1

    @mock.patch('artexinweb.models.Task.mark_finished')
    @mock.patch('artexinweb.models.Task.mark_failed')
    def test_handle_task_result_success(self, mark_failed, mark_finished):
        task = Task.create(self.job_id, self.target)
        result = {'size': 1024,
                  'hash': self.job_id,
                  'title': 'Target title',
                  'images': 3,
                  'timestamp': datetime.datetime.utcnow()}
        options = {}

        handler = FetchableHandler()
        handler.handle_task_result(task, result, options)

        assert not mark_failed.called
        mark_finished.assert_called_once_with()

        assert task.size == result['size']
        assert task.md5 == result['hash']
        assert task.title == result['title']
        assert task.images == result['images']
        assert task.timestamp == result['timestamp']

    @mock.patch('artexin.pack.collect')
    @mock.patch('artexin.preprocessor_mappings.get_preps')
    def test_handle_task(self, get_preps, collect):
        task = Task.create(self.job_id, self.target)
        options = {'javascript': True, 'extract': True}

        fake_preps = ['prep1']
        get_preps.return_value = fake_preps

        collect_result = {'meta': 'so meta'}
        collect.return_value = collect_result

        mock_settings = {'artexin.out_dir': '/test/out'}

        handler = FetchableHandler()
        with mock_bottle_config('artexinweb.settings.BOTTLE_CONFIG',
                                mock_settings):
            result = handler.handle_task(task, options)

        assert result == collect_result

        get_preps.assert_called_once_with(task.target)

        out_dir = mock_settings['artexin.out_dir']
        collect.assert_called_once_with(task.target,
                                        prep=fake_preps,
                                        base_dir=out_dir,
                                        javascript=True,
                                        do_extract=True,
                                        meta={})
