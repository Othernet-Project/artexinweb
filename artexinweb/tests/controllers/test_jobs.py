# -*- coding: utf-8 -*-
from unittest import mock

import artexinweb.controllers.jobs


class TestJobControllers(object):

    @mock.patch('bottle.jinja2_view')
    @mock.patch('artexinweb.models.jobs.Job.objects')
    def test_task_list(self, job_objects, jinja2_view):

        def pass_through(template_name):
            def _pass_through(func):
                def __pass_through(*args, **kwargs):
                    result = func(*args, **kwargs)
                    return result
                return __pass_through
            return _pass_through

        jinja2_view.side_effect = pass_through

        # from artexinweb.controllers import jobs as job_controllers

        mocked_job = mock.Mock()
        mocked_job.tasks = []
        job_objects.get.return_value = mocked_job

        result = artexinweb.controllers.jobs.task_list('job_id')

        # assert result == {'task_list': [], 'job_id': 'job_id'}
