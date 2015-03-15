# -*- coding: utf-8 -*-
import copy
import io
import json
import os

from unittest import mock

from artexinweb import settings
from artexinweb.models import Job


def pass_through(template_name):
    def _pass_through(func):
        def __pass_through(*args, **kwargs):
            return func(*args, **kwargs)
        return __pass_through
    return _pass_through


class TestJobControllers(object):

    @mock.patch('bottle.jinja2_view')
    @mock.patch('artexinweb.models.jobs.Job.objects')
    def test_job_dashboard(self, job_objects, jinja2_view):
        jinja2_view.side_effect = pass_through
        expected_count = 3

        mocked_queryset = mock.Mock()
        mocked_queryset.count.return_value = expected_count
        job_objects.filter.return_value = mocked_queryset

        from artexinweb.controllers.jobs import job_dashboard
        result = job_dashboard()

        assert result == {'erred_status': Job.ERRED,
                          'erred_job_count': expected_count}

        job_objects.filter.assert_called_once_with(status=Job.ERRED)
        mocked_queryset.count.assert_called_once_with()

    @mock.patch('bottle.jinja2_view')
    @mock.patch('bottle.request')
    @mock.patch('artexinweb.models.jobs.Job.objects')
    def test_jobs_list(self, job_objects, bottle_request, jinja2_view):
        jinja2_view.side_effect = pass_through
        from artexinweb.controllers.jobs import jobs_list
        chosen_status = 'some_status'

        bottle_request.query.get.return_value = chosen_status
        job_objects.filter.return_value = [1]

        result = jobs_list()
        assert result == {'job_list': [1],
                          'current_status': chosen_status,
                          'statuses': Job.STATUSES}

        job_objects.filter.assert_called_once_with(status=chosen_status)

        bottle_request.query.get.return_value = None
        job_objects.all.return_value = [2]

        result = jobs_list()
        assert result == {'job_list': [2],
                          'current_status': None,
                          'statuses': Job.STATUSES}

        job_objects.all.assert_called_once_with()

        calls = [mock.call('status'), mock.call('status')]
        bottle_request.query.get.assert_has_calls(calls)

    @mock.patch('bottle.redirect')
    @mock.patch('artexinweb.models.jobs.Job.create')
    def test_create_fetchable_job(self, job_create, bottle_redirect):
        from artexinweb.controllers.jobs import CreateJobController

        bottle_redirect.return_value = 'redir'
        form = mock.Mock()

        result = CreateJobController.fetchable(Job.FETCHABLE, form)

        form.get_meta.assert_called_once_with()

        assert job_create.call_count == 1
        assert result == 'redir'

    @mock.patch('uuid.uuid4')
    @mock.patch('os.makedirs')
    @mock.patch('bottle.request')
    @mock.patch('bottle.redirect')
    @mock.patch('artexinweb.models.jobs.Job.create')
    def test_create_standalone_job(self, job_create, bottle_redirect,
                                   bottle_request, os_makedirs, uuid_uuid4):
        from artexinweb.controllers.jobs import CreateJobController

        uuid_uuid4.return_value = 'test'
        bottle_redirect.return_value = 'redir'
        file1 = mock.Mock(filename='file1.zip')
        file2 = mock.Mock(filename='file2.zip')
        bottle_request.files.getlist.return_value = [file1, file2]
        form = mock.Mock()

        result = CreateJobController.standalone(Job.STANDALONE, form)
        assert result == 'redir'
        assert job_create.call_count == 1

        media_root = settings.BOTTLE_CONFIG.get('web.media_root', '')
        upload_dir = os.path.join(media_root, 'test')
        file1_path = os.path.join(upload_dir, file1.filename)
        file2_path = os.path.join(upload_dir, file2.filename)

        file1.save.assert_called_once_with(file1_path)
        file2.save.assert_called_once_with(file2_path)
        os_makedirs.assert_called_once_with(upload_dir)

    @mock.patch('bottle.request')
    @mock.patch.object(Job, 'is_valid_type')
    @mock.patch('artexinweb.controllers.jobs.CreateJobController')
    @mock.patch('bottle.jinja2_template')
    def test_jobs_create_get_form(self, jinja2_template, create_job_controller,
                                  is_valid_type, bottle_request):
        from artexinweb.controllers.jobs import jobs_create

        bottle_request.forms.get.return_value = Job.FETCHABLE
        is_valid_type.return_value = True

        mock_request = mock.Mock(files={})
        mock_request.forms.decode.return_value = {}
        bottle_request.return_value = mock_request

        form = mock.Mock()
        form.validate.return_value = False
        form_cls = mock.Mock(return_value=form)
        create_job_controller.forms.__getitem__.return_value = form_cls

        jobs_create()

        is_valid_type.assert_called_once_with(Job.FETCHABLE)
        jinja2_template.assert_called_once_with('job_fetchable.html',
                                                form=form,
                                                job_type=Job.FETCHABLE)

    @mock.patch('bottle.request')
    @mock.patch.object(Job, 'is_valid_type')
    @mock.patch('artexinweb.controllers.jobs.CreateJobController')
    @mock.patch('bottle.jinja2_template')
    def test_jobs_create_valid(self, jinja2_template, create_job_controller,
                               is_valid_type, bottle_request):
        from artexinweb.controllers.jobs import jobs_create

        bottle_request.forms.get.return_value = Job.FETCHABLE
        is_valid_type.return_value = True

        mock_request = mock.Mock(files={})
        mock_request.forms.decode.return_value = {}
        bottle_request.return_value = mock_request

        form = mock.Mock()
        form.validate.return_value = True
        form_cls = mock.Mock(return_value=form)
        create_job_controller.forms.__getitem__.return_value = form_cls

        mocked_handler = mock.Mock()
        mocked_handler.return_value = 'response'
        create_job_controller.get_handler.return_value = mocked_handler

        result = jobs_create()

        assert result == 'response'
        create_job_controller.get_handler.assert_called_once_with(
            Job.FETCHABLE.lower()
        )
        mocked_handler.assert_called_once_with(Job.FETCHABLE, form)
        is_valid_type.assert_called_once_with(Job.FETCHABLE)

    @mock.patch('bottle.request')
    @mock.patch.object(Job, 'is_valid_type')
    @mock.patch('bottle.jinja2_template')
    def test_jobs_create_invalid_job_type(self, jinja2_template, is_valid_type,
                                          bottle_request):
        from artexinweb.controllers.jobs import jobs_create

        bottle_request.forms.get.return_value = Job.FETCHABLE
        is_valid_type.return_value = False

        jobs_create()

        is_valid_type.assert_called_once_with(Job.FETCHABLE)
        jinja2_template.assert_called_once_with('job_wizard.html')

    @mock.patch.object(Job, 'is_valid_type')
    @mock.patch('artexinweb.controllers.jobs.CreateJobController')
    @mock.patch('bottle.request')
    @mock.patch('bottle.jinja2_template')
    def test_jobs_new_valid_job_type(self, jinja2_template, bottle_request,
                                     create_job_controller, is_valid_type):
        from artexinweb.controllers.jobs import jobs_new

        bottle_request.query.get.return_value = Job.FETCHABLE
        is_valid_type.return_value = True

        form = mock.Mock()
        form_cls = mock.Mock(return_value=form)
        create_job_controller.forms.__getitem__.return_value = form_cls

        jobs_new()

        jinja2_template.assert_called_once_with('job_fetchable.html',
                                                form=form,
                                                job_type=Job.FETCHABLE)

    @mock.patch.object(Job, 'is_valid_type')
    @mock.patch('artexinweb.controllers.jobs.CreateJobController')
    @mock.patch('bottle.request')
    @mock.patch('bottle.jinja2_template')
    def test_jobs_new_invalid_job_type(self, jinja2_template, bottle_request,
                                       create_job_controller, is_valid_type):
        from artexinweb.controllers.jobs import jobs_new

        bottle_request.query.get.return_value = Job.FETCHABLE
        is_valid_type.return_value = False

        jobs_new()

        jinja2_template.assert_called_once_with('job_wizard.html')

    @mock.patch('bottle.request')
    @mock.patch('bottle.jinja2_template')
    def test_jobs_retry_get(self, jinja2_template, bottle_request):
        from artexinweb.controllers.jobs import jobs_retry
        bottle_request.method = 'GET'
        job_id = 'job_id'

        jobs_retry(job_id)

        jinja2_template.assert_called_once_with('job_retry.html',
                                                job_id=job_id)

    @mock.patch('artexinweb.models.jobs.Job.objects')
    @mock.patch('bottle.redirect')
    @mock.patch('bottle.request')
    @mock.patch('bottle.jinja2_template')
    def test_jobs_retry_post(self, jinja2_template, bottle_request,
                             bottle_redirect, job_objects):
        from artexinweb.controllers.jobs import jobs_retry
        bottle_request.method = 'POST'
        bottle_redirect.return_value = 'redir'
        job_id = 'job_id'

        job = mock.Mock(is_finished=False)
        job_objects.get.return_value = job

        result = jobs_retry(job_id)

        assert result == 'redir'
        job.retry.assert_called_once_with()
        job_objects.get.assert_called_once_with(job_id=job_id)

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

    @mock.patch('bottle.jinja2_template')
    @mock.patch('bottle.request')
    @mock.patch('artexinweb.utils.read_from_zip')
    @mock.patch('artexinweb.controllers.jobs.MetaForm')
    @mock.patch('artexinweb.models.jobs.Task.objects')
    def test_task_meta_edit_read(self, task_objects, meta_form, read_from_zip,
                                 bottle_request, jinja2_template):
        from artexinweb.controllers.jobs import task_meta_edit
        bottle_request.method = 'GET'
        zipball_path = '/srv/zipballs/some_id.zip'

        form = mock.Mock()
        meta_form.return_value = form

        task_id = 'task_id'
        meta = {'language': 'en',
                'license': 'GFDL'}
        meta_filename = '{0}/info.json'.format(task_id)

        task = mock.Mock(zipball_path=zipball_path)
        task_objects.get.return_value = task

        meta_bytes = json.dumps(meta).encode('utf-8')
        read_from_zip.return_value = io.BytesIO(meta_bytes)

        task_meta_edit('job_id', task_id)

        read_from_zip.assert_called_once_with(zipball_path, meta_filename)
        jinja2_template.assert_called_once_with('task_meta.html',
                                                form=form,
                                                meta=meta,
                                                task=task)

    @mock.patch('bottle.redirect')
    @mock.patch('bottle.request')
    @mock.patch('artexinweb.utils.replace_in_zip')
    @mock.patch('artexinweb.utils.read_from_zip')
    @mock.patch('artexinweb.controllers.jobs.MetaForm')
    @mock.patch('artexinweb.models.jobs.Task.objects')
    def test_task_meta_edit_form_valid(self, task_objects, meta_form,
                                       read_from_zip, replace_in_zip,
                                       bottle_request, bottle_redirect):
        from artexinweb.controllers.jobs import task_meta_edit
        bottle_request.method = 'POST'
        zipball_path = '/srv/zipballs/some_id.zip'

        form_data = {'language': 'de'}
        form = mock.Mock(data=form_data)
        form.validate.return_value = True
        meta_form.return_value = form

        task_id = 'task_id'
        job_id = 'job_id'
        meta = {'language': 'en',
                'license': 'GFDL'}
        meta_filename = '{0}/info.json'.format(task_id)

        task = mock.Mock(zipball_path=zipball_path)
        task_objects.get.return_value = task

        meta_bytes = json.dumps(meta).encode('utf-8')
        read_from_zip.return_value = io.BytesIO(meta_bytes)

        task_meta_edit(job_id, task_id)

        read_from_zip.assert_called_once_with(zipball_path, meta_filename)

        merged_meta = copy.copy(meta)
        merged_meta.update(form_data)
        replacements = {meta_filename: json.dumps(merged_meta)}
        replace_in_zip.assert_called_once_with(zipball_path, **replacements)

        task_list_url = '/jobs/{0}/tasks/'.format(job_id)
        bottle_redirect.assert_called_once_with(task_list_url)

    @mock.patch('bottle.jinja2_template')
    @mock.patch('bottle.request')
    @mock.patch('artexinweb.utils.read_from_zip')
    @mock.patch('artexinweb.controllers.jobs.MetaForm')
    @mock.patch('artexinweb.models.jobs.Task.objects')
    def test_task_meta_edit_form_not_valid(self, task_objects, meta_form,
                                           read_from_zip, bottle_request,
                                           jinja2_template):
        from artexinweb.controllers.jobs import task_meta_edit
        bottle_request.method = 'POST'
        zipball_path = '/srv/zipballs/some_id.zip'

        form = mock.Mock()
        form.validate.return_value = False
        meta_form.return_value = form

        task_id = 'task_id'
        job_id = 'job_id'
        meta = {'language': 'en',
                'license': 'GFDL'}
        meta_filename = '{0}/info.json'.format(task_id)

        task = mock.Mock(zipball_path=zipball_path)
        task_objects.get.return_value = task

        meta_bytes = json.dumps(meta).encode('utf-8')
        read_from_zip.return_value = io.BytesIO(meta_bytes)

        task_meta_edit(job_id, task_id)

        read_from_zip.assert_called_once_with(zipball_path, meta_filename)
        jinja2_template.assert_called_once_with('task_meta.html',
                                                form=form,
                                                meta=meta,
                                                task=task)
