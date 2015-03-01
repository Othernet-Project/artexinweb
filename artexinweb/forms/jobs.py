# -*- coding: utf-8 -*-
from bottle import MultiDict

from wtforms import fields
from wtforms import form
from wtforms import validators

from artexinweb import settings, utils


def check_extension(form, field):
    ext = utils.get_extension(field.data.filename)

    valid = settings.BOTTLE_CONFIG.get('web.allowed_upload_extensions',
                                       'zip').split(',')

    if ext not in valid:
        msg = "Only {0} files are allowed.".format(",".join(valid))
        raise validators.ValidationError(msg)


class StandaloneJobForm(form.Form):
    origin = fields.StringField(validators=[validators.URL(require_tld=True)])
    files = fields.FileField(validators=[validators.InputRequired(),
                                         check_extension])


class URLListField(fields.TextAreaField):

    def _value(self):
        if self.data:
            return u'\n'.join(self.data)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = [x.strip() for x in valuelist[0].split('\n')]
        else:
            self.data = []

    def post_validate(self, parent_form, validation_stopped):
        if validation_stopped:
            return

        # FIXME: a bit hairy validation, find something more idiomatic
        url_validator = validators.URL(require_tld=True)

        class TmpForm(form.Form):
            url = fields.StringField(validators=[url_validator])

        for url in self.data:
            tmp_form = TmpForm(MultiDict(url=url))
            if not tmp_form.validate():
                raise validators.ValidationError("Invalid URL(s).")


class FetchableJobForm(form.Form):
    urls = URLListField(validators=[validators.InputRequired()])
    javascript = fields.BooleanField(validators=[validators.optional()],
                                     default=True)
    extract = fields.BooleanField(validators=[validators.optional()],
                                  default=True)
