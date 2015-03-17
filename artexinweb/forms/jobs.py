# -*- coding: utf-8 -*-
from bottle import MultiDict

from wtforms import fields
from wtforms import form
from wtforms import validators

from artexinweb import settings, utils


LICENSES = (
    ('CC-BY', "Creative Commons Attribution"),
    ('CC-BY-ND', "Creative Commons Attribution-NoDerivs"),
    ('CC-BY-NC', "Creative Commons Attribution-NonCommercial"),
    ('CC-BY-ND-NC', "Creative Commons Attribution-NonCommercial-NoDerivs"),
    ('CC-BY-SA', "Creative Commons Attribution-ShareAlike"),
    ('CC-BY-NC-SA', "Creative Commons Attribution-NonCommercial-ShareAlike"),
    ('GFDL', "GNU Free Documentation License"),
    ('OPL', "Open Publication License"),
    ('OCL', "Open Content License"),
    ('ADL', "Against DRM License"),
    ('FAL', "Free Art License"),
    ('PD', "Public Domain"),
    ('OF', "Other free license"),
    ('ARL', "All rights reserved"),
    ('ON', "Other non-free license"),
)
LANGUAGE_CODES = [(lang_code, lang_label)
                  for (lang_code, lang_label) in utils.collect_locales()
                  if len(lang_code) < 3]


class MetaForm(form.Form):
    title = fields.StringField()
    language = fields.SelectField(choices=LANGUAGE_CODES)
    license = fields.SelectField(choices=LICENSES)
    archive = fields.StringField()
    is_partner = fields.BooleanField(default=False)
    partner = fields.StringField()
    is_sponsored = fields.BooleanField(default=False)
    keep_formatting = fields.BooleanField(default=False)

    def validate_partner(self, field):
        if self.is_partner.data and not field.data:
            raise validators.ValidationError("A partner must be specified")

    def get_meta(self):
        return {'title': self.title.data,
                'language': self.language.data,
                'license': self.license.data,
                'archive': self.archive.data,
                'is_partner': self.is_partner.data,
                'partner': self.partner.data,
                'is_sponsored': self.is_sponsored.data,
                'keep_formatting': self.keep_formatting.data}


def check_extension(form, field):
    ext = utils.get_extension(field.data.filename)

    valid = settings.BOTTLE_CONFIG.get('web.allowed_upload_extensions',
                                       'zip').split(',')

    if ext not in valid:
        msg = "Only {0} files are allowed.".format(",".join(valid))
        raise validators.StopValidation(msg)


def has_html_file(form, field):
    is_html_file = lambda fn: any(fn.endswith(ext) for ext in ('htm', 'html'))
    files = utils.list_zipfile(field.data.file)
    if not any(is_html_file(filename) for filename in files):
        msg = "No HTML file found in: {0}".format(field.data.filename)
        raise validators.StopValidation(msg)
    # must seek to the beginning of file to save them properly
    field.data.file.seek(0)


class StandaloneJobForm(MetaForm):
    origin = fields.StringField(validators=[validators.URL(require_tld=True)])
    files = fields.FileField(validators=[validators.InputRequired(),
                                         check_extension,
                                         has_html_file])


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


class FetchableJobForm(MetaForm):
    urls = URLListField(validators=[validators.InputRequired()])
    javascript = fields.BooleanField(validators=[validators.optional()],
                                     default=True)
    extract = fields.BooleanField(validators=[validators.optional()],
                                  default=True)
