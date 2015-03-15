# -*- coding: utf-8 -*-
import codecs
import json
import os
import uuid

import bottle

from artexinweb import settings, utils
from artexinweb.forms import FetchableJobForm, StandaloneJobForm, MetaForm
from artexinweb.models import Job, Task


@bottle.get('/')
@bottle.jinja2_view('job_dashboard.html')
def job_dashboard():
    return {'erred_job_count': Job.objects.filter(status=Job.ERRED).count(),
            'erred_status': Job.ERRED}


@bottle.get('/jobs/')
@bottle.jinja2_view('job_list.html')
def jobs_list():
    status = bottle.request.query.get('status')
    if status:
        job_list = Job.objects.filter(status=status)
    else:
        job_list = Job.objects.all()

    return {'job_list': job_list,
            'current_status': status,
            'statuses': Job.STATUSES}


class CreateJobController(object):

    forms = {
        Job.FETCHABLE: FetchableJobForm,
        Job.STANDALONE: StandaloneJobForm
    }

    @classmethod
    def fetchable(cls, job_type, form):
        meta = form.get_meta()
        Job.create(job_type=job_type,
                   targets=form.urls.data,
                   extract=form.extract.data,
                   javascript=form.javascript.data,
                   meta=meta)
        return bottle.redirect('/jobs/')

    @classmethod
    def standalone(cls, job_type, form):
        folder_name = str(uuid.uuid4())
        media_root = settings.BOTTLE_CONFIG.get('web.media_root', '')
        upload_dir = os.path.join(media_root, folder_name)

        os.makedirs(upload_dir)

        targets = []
        for uploaded_file in bottle.request.files.getlist('files'):
            upload_path = os.path.join(upload_dir, uploaded_file.filename)
            uploaded_file.save(upload_path)
            targets.append(upload_path)

        meta = form.get_meta()
        Job.create(job_type=job_type,
                   targets=targets,
                   origin=form.origin.data,
                   meta=meta)
        return bottle.redirect('/jobs/')

    @classmethod
    def get_handler(cls, job_type):
        return getattr(cls, job_type)


@bottle.post('/jobs/')
def jobs_create():
    job_type = bottle.request.forms.get('type')

    if Job.is_valid_type(job_type):
        form_cls = CreateJobController.forms[job_type]
        form_data = bottle.request.forms.decode()
        form_data.update(bottle.request.files)
        form = form_cls(form_data)

        if form.validate():
            handler = CreateJobController.get_handler(job_type.lower())
            return handler(job_type, form)

        template_name = 'job_{0}.html'.format(job_type.lower())
        return bottle.jinja2_template(template_name,
                                      form=form,
                                      job_type=job_type)

    return bottle.jinja2_template('job_wizard.html')


@bottle.get('/jobs/actions/new/')
def jobs_new():
    job_type = bottle.request.query.get('type')
    if Job.is_valid_type(job_type):
        form_cls = CreateJobController.forms[job_type]
        form = form_cls()

        return bottle.jinja2_template('job_{0}.html'.format(job_type.lower()),
                                      form=form,
                                      job_type=job_type)

    return bottle.jinja2_template('job_wizard.html')


@bottle.route('/jobs/<job_id:re:[a-zA-Z0-9]+>/actions/retry/',
              method=['GET', 'POST'])
def jobs_retry(job_id):
    if bottle.request.method == 'POST':
        job = Job.objects.get(job_id=job_id)
        if not job.is_finished:
            job.retry()

        return bottle.redirect('/jobs/')

    return bottle.jinja2_template('job_retry.html', job_id=job_id)


@bottle.get('/jobs/<job_id:re:[a-zA-Z0-9]+>/')
@bottle.jinja2_view('job_details.html')
def jobs_details(job_id):
    job = Job.objects.get(job_id=job_id)
    return {'job': job}


@bottle.get('/jobs/<job_id:re:[a-zA-Z0-9]+>/tasks/')
@bottle.jinja2_view('task_list.html')
def task_list(job_id):
    job = Job.objects.get(job_id=job_id)
    return {'task_list': job.tasks, 'job_id': job_id}


@bottle.route('/jobs/<job_id:re:[a-zA-Z0-9]+>/tasks/<task_id:re:[a-zA-Z0-9]+>/actions/meta/',  # NOQA
              method=['GET', 'POST'])
def task_meta_edit(job_id, task_id):
    task = Task.objects.get(job_id=job_id, md5=task_id)
    meta_filename = '{0}/info.json'.format(task_id)
    meta_bytes = utils.read_from_zip(task.zipball_path, meta_filename)
    reader = codecs.getreader("utf-8")
    meta = json.load(reader(meta_bytes))

    if bottle.request.method == 'POST':
        form_data = bottle.request.forms.decode()
        form = MetaForm(form_data)
        if form.validate():
            meta.update(form.data)
            replacements = {meta_filename: json.dumps(meta)}
            utils.replace_in_zip(task.zipball_path, **replacements)
            return bottle.redirect('/jobs/{0}/tasks/'.format(job_id))
    else:
        form = MetaForm(**meta)

    return bottle.jinja2_template('task_meta.html',
                                  form=form,
                                  meta=meta,
                                  task=task)
