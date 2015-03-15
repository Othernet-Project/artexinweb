# -*- coding: utf-8 -*-
from unittest import mock

from artexinweb.handlers.base import BaseJobHandler
from artexinweb.models import Job, Task
from artexinweb.tests.base import BaseMongoTestCase


class TestBaseJobHandler(BaseMongoTestCase):

    @classmethod
    def setup_class(cls):
        cls.job_id = 'a' * 32
        cls.targets = [
            'http://en.wikipedia.org/wiki/Prime_factor',
            'http://en.wikipedia.org/wiki/Integer_factorization'
        ]

    def test_is_valid_task(self):
        task = Task.create(self.job_id, self.targets[0])
        handler = BaseJobHandler()

        # initial status is queued
        assert handler.is_valid_task(task) is True

        task.mark_processing()
        assert handler.is_valid_task(task) is True

        task.mark_failed("failed")
        assert handler.is_valid_task(task) is True

        task.mark_finished()
        assert handler.is_valid_task(task) is False

    @mock.patch('artexinweb.models.jobs.Job.queue_class')
    @mock.patch('artexinweb.handlers.base.BaseJobHandler.process_task')
    @mock.patch('artexinweb.models.Job.mark_finished')
    @mock.patch('artexinweb.models.Job.mark_erred')
    @mock.patch('artexinweb.models.Job.mark_processing')
    def test_run_success(self, mark_processing, mark_erred, mark_finished,
                         process_task, *args):
        job = Job.create(targets=self.targets,
                         job_type=Job.FETCHABLE,
                         extract=True,
                         javascript=True)
        # make second task already finished, so it should be skipped
        job.tasks[1].mark_finished()

        handler = BaseJobHandler()
        handler.run({'type': job.job_type, 'id': job.job_id})

        mark_processing.assert_called_once_with()
        mark_finished.assert_called_once_with()
        assert not mark_erred.called

        calls = [mock.call(job.tasks[0], job.options)]
        process_task.assert_has_calls(calls)

    @mock.patch('artexinweb.models.jobs.Job.queue_class')
    @mock.patch('artexinweb.handlers.base.BaseJobHandler.process_task')
    @mock.patch('artexinweb.models.Job.mark_finished')
    @mock.patch('artexinweb.models.Job.mark_erred')
    @mock.patch('artexinweb.models.Job.mark_processing')
    def test_run_failure(self, mark_processing, mark_erred, mark_finished,
                         process_task, *args):
        job = Job.create(targets=self.targets,
                         job_type=Job.FETCHABLE,
                         extract=True,
                         javascript=True)
        # make second task failed, as real processing is skipped, it will
        # trigger failure on the whole process
        job.tasks[1].mark_failed("failed")

        handler = BaseJobHandler()
        handler.run({'type': job.job_type, 'id': job.job_id})

        mark_processing.assert_called_once_with()
        mark_erred.assert_called_once_with()
        assert not mark_finished.called

        calls = [mock.call(task, job.options) for task in job.tasks]
        process_task.assert_has_calls(calls)

    @mock.patch('artexinweb.handlers.base.BaseJobHandler.handle_task')
    @mock.patch('artexinweb.models.Task.mark_failed')
    def test_process_task_invalid_target(self, mark_failed, handle_task):
        task = Task.create(self.job_id, self.targets[0])

        handler = BaseJobHandler()
        with mock.patch.object(handler, 'is_valid_target', return_value=False):
            handler.process_task(task, {})

            assert mark_failed.call_count == 1
            assert not handle_task.called

    @mock.patch('artexinweb.handlers.base.BaseJobHandler.handle_task_result')
    @mock.patch('artexinweb.handlers.base.BaseJobHandler.handle_task')
    @mock.patch('artexinweb.models.Task.mark_failed')
    def test_process_task_success(self, mark_failed, handle_task,
                                  handle_task_result):
        task = Task.create(self.job_id, self.targets[0])
        options = {}
        task_result = {'result': 'OK'}

        handle_task.return_value = task_result

        handler = BaseJobHandler()
        with mock.patch.object(handler, 'is_valid_target', return_value=True):
            handler.process_task(task, options)

            handle_task.assert_called_once_with(task, options)
            handle_task_result.assert_called_once_with(task,
                                                       task_result,
                                                       options)
            assert not mark_failed.called

    @mock.patch('artexinweb.handlers.base.BaseJobHandler.handle_task_result')
    @mock.patch('artexinweb.handlers.base.BaseJobHandler.handle_task')
    @mock.patch('artexinweb.models.Task.mark_failed')
    def test_process_task_handle_task_failure(self, mark_failed, handle_task,
                                              handle_task_result):
        task = Task.create(self.job_id, self.targets[0])
        options = {}

        handle_task.side_effect = Exception()

        handler = BaseJobHandler()
        with mock.patch.object(handler, 'is_valid_target', return_value=True):
            handler.process_task(task, options)

            handle_task.assert_called_once_with(task, options)
            assert not handle_task_result.called
            assert mark_failed.call_count == 1

    @mock.patch('artexinweb.handlers.base.BaseJobHandler.handle_task_result')
    @mock.patch('artexinweb.handlers.base.BaseJobHandler.handle_task')
    @mock.patch('artexinweb.models.Task.mark_failed')
    def test_process_task_handle_task_result_failure(self,
                                                     mark_failed,
                                                     handle_task,
                                                     handle_task_result):
        task = Task.create(self.job_id, self.targets[0])
        options = {}
        task_result = {'result': 'OK'}

        handle_task.return_value = task_result
        handle_task_result.side_effect = Exception()

        handler = BaseJobHandler()
        with mock.patch.object(handler, 'is_valid_target', return_value=True):
            handler.process_task(task, options)

            handle_task.assert_called_once_with(task, options)
            handle_task_result.assert_called_once_with(task,
                                                       task_result,
                                                       options)
            assert mark_failed.call_count == 1
