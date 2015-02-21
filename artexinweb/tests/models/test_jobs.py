# -*- coding: utf-8 -*-
from unittest import mock

import pytest

from artexinweb.models import Job, Task
from artexinweb.tests.models.base import BaseMongoTestCase


class TestJobModel(BaseMongoTestCase):

    def assert_tasks(self, job, expected_targets):
        assert len(job.tasks) == len(expected_targets)

        for i, task in enumerate(job.tasks):
            assert task.status == Task.QUEUED
            assert task.job_id == job.job_id
            assert task.target == expected_targets[i]

    @classmethod
    def setup_class(cls):
        cls.fetchable_targets = [
            'http://en.wikipedia.org/wiki/Prime_factor',
            'http://en.wikipedia.org/wiki/Integer_factorization'
        ]

        cls.standalone_targets = ['/srv/media/some_uuid']
        cls.origin = 'http://en.wikipedia.org/wiki/Prime_factor'

    @mock.patch('artexinweb.models.jobs.Job.queue_class')
    def test_create_fetchable_job(self, queue_class):
        job = Job.create(targets=self.fetchable_targets,
                         job_type=Job.FETCHABLE,
                         extract=True,
                         javascript=True)

        assert job.status == Job.QUEUED
        assert job.job_type == Job.FETCHABLE
        assert job.scheduled == job.updated
        assert job.options['extract'] is True
        assert job.options['javascript'] is True

        queue = queue_class.return_value
        queue.put.assert_called_once_with({'type': job.job_type,
                                           'id': job.job_id})

        self.assert_tasks(job, self.fetchable_targets)

    @mock.patch('artexinweb.models.jobs.Job.queue_class')
    def test_create_standalone_job(self, queue_class):
        job = Job.create(targets=self.standalone_targets,
                         job_type=Job.STANDALONE,
                         origin=self.origin)

        assert job.status == Job.QUEUED
        assert job.job_type == Job.STANDALONE
        assert job.scheduled == job.updated
        assert job.options['origin'] == self.origin

        queue = queue_class.return_value
        queue.put.assert_called_once_with({'type': job.job_type,
                                           'id': job.job_id})

        self.assert_tasks(job, self.standalone_targets)

    @mock.patch('artexinweb.models.jobs.Job.queue_class')
    def test_mark_queued(self, queue_class):
        job = Job.create(targets=self.standalone_targets,
                         job_type=Job.STANDALONE,
                         origin=self.origin)

        job.mark_erred()  # jobs are queued by default, so make it erred
        assert job.is_queued is False
        job.mark_queued()
        assert job.is_queued is True

    @mock.patch('artexinweb.models.jobs.Job.queue_class')
    def test_mark_processing(self, queue_class):
        job = Job.create(targets=self.standalone_targets,
                         job_type=Job.STANDALONE,
                         origin=self.origin)

        assert job.is_processing is False
        job.mark_processing()
        assert job.is_processing is True

    @mock.patch('artexinweb.models.jobs.Job.queue_class')
    def test_mark_erred(self, queue_class):
        job = Job.create(targets=self.standalone_targets,
                         job_type=Job.STANDALONE,
                         origin=self.origin)

        assert job.is_erred is False
        job.mark_erred()
        assert job.is_erred is True

    @mock.patch('artexinweb.models.jobs.Job.queue_class')
    def test_mark_finished(self, queue_class):
        job = Job.create(targets=self.standalone_targets,
                         job_type=Job.STANDALONE,
                         origin=self.origin)

        assert job.is_finished is False
        job.mark_finished()
        assert job.is_finished is True

    @mock.patch('artexinweb.models.jobs.Job.queue_class')
    def test_retry(self, queue_class):
        job = Job.create(targets=self.standalone_targets,
                         job_type=Job.STANDALONE,
                         origin=self.origin)

        job.mark_erred()  # jobs are queued by default, so make it erred
        assert job.is_queued is False

        job.retry()

        assert job.is_queued is True

        queue = queue_class.return_value
        job_data = {'type': job.job_type, 'id': job.job_id}
        # called twice, first when the job is created, next when it's retried
        queue.put.assert_has_calls([mock.call(job_data), mock.call(job_data)])

    def test_is_valid_type(self):
        assert Job.is_valid_type(Job.STANDALONE) is True
        assert Job.is_valid_type(Job.FETCHABLE) is True
        assert Job.is_valid_type('INVALID') is False