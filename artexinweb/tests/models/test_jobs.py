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

    @mock.patch('artexinweb.models.jobs.Job.queue_class')
    def test_create_fetchable_job(self, queue_class):
        targets = ['http://en.wikipedia.org/wiki/Prime_factor',
                   'http://en.wikipedia.org/wiki/Integer_factorization']

        job = Job.create(targets=targets,
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

        self.assert_tasks(job, targets)

    @mock.patch('artexinweb.models.jobs.Job.queue_class')
    def test_create_standalone_job(self, queue_class):
        targets = ['/srv/media/some_uuid']
        origin = 'http://en.wikipedia.org/wiki/Prime_factor'

        job = Job.create(targets=targets,
                         job_type=Job.STANDALONE,
                         origin=origin)

        assert job.status == Job.QUEUED
        assert job.job_type == Job.STANDALONE
        assert job.scheduled == job.updated
        assert job.options['origin'] == origin

        queue = queue_class.return_value
        queue.put.assert_called_once_with({'type': job.job_type,
                                           'id': job.job_id})

        self.assert_tasks(job, targets)
