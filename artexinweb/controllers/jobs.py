# -*- coding: utf-8 -*-
import os
import uuid

import bottle

from artexinweb import settings
from artexinweb.forms import FetchableJobForm, StandaloneJobForm
from artexinweb.models import Job


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


class JobController(object):

    forms = {
        Job.FETCHABLE: FetchableJobForm,
        Job.STANDALONE: StandaloneJobForm
    }

    @classmethod
    def fetchable(cls, job_type, form):
        Job.create(job_type=job_type,
                   targets=form.urls.data,
                   extract=form.extract.data,
                   javascript=form.javascript.data)
        return bottle.redirect('/jobs/')

    @classmethod
    def standalone(cls, job_type, form):
        folder_name = str(uuid.uuid4())
        media_root = settings.BOTTLE_CONFIG['web.media_root']
        upload_path = os.path.join(media_root, folder_name)

        os.makedirs(upload_path)

        for uploaded_file in bottle.request.files.getlist('files'):
            uploaded_file.save(upload_path)

        Job.create(targets=[upload_path],
                   job_type=job_type,
                   origin=form.origin.data)
        return bottle.redirect('/jobs/')


@bottle.post('/jobs/')
def jobs_create():
    job_type = bottle.request.forms.get('type')

    if Job.is_valid_type(job_type):
        form_cls = JobController.forms[job_type]
        form_data = bottle.request.forms.decode()
        form_data.update(bottle.request.files)
        form = form_cls(form_data)

        if form.validate():
            return getattr(JobController, job_type.lower())(job_type, form)

        template_name = 'job_{0}.html'.format(job_type.lower())
        return bottle.jinja2_template(template_name,
                                      form=form,
                                      job_type=job_type)

    return bottle.jinja2_template('job_wizard.html')


@bottle.get('/jobs/actions/new/')
def jobs_new():
    job_type = bottle.request.query.get('type')
    if Job.is_valid_type(job_type):
        form_cls = JobController.forms[job_type]
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
