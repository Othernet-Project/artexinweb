# -*- coding: utf-8 -*-
from unittest import mock


def pass_through(template_name):
    def _pass_through(func):
        def __pass_through(*args, **kwargs):
            return func(*args, **kwargs)
        return __pass_through
    return _pass_through


class TestJobControllers(object):

    @mock.patch('bottle.jinja2_view')
    @mock.patch('artexinweb.models.jobs.Job.objects')
    def test_task_list(self, job_objects, jinja2_view):
        jinja2_view.side_effect = pass_through

        mocked_job = mock.Mock()
        mocked_job.tasks = []
        job_objects.get.return_value = mocked_job

        from artexinweb.controllers.jobs import task_list
        result = task_list('job_id')

        assert result == {'task_list': [], 'job_id': 'job_id'}

    @mock.patch('bottle.jinja2_view')
    @mock.patch('artexinweb.models.jobs.Job.objects')
    def test_job_details(self, job_objects, jinja2_view):
        jinja2_view.side_effect = pass_through

        mocked_job = mock.Mock()
        mocked_job.tasks = []
        job_objects.get.return_value = mocked_job

        from artexinweb.controllers.jobs import jobs_details
        result = jobs_details('job_id')

        assert result == {'job': mocked_job}
