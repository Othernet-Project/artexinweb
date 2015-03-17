# -*- coding: utf-8 -*-
import codecs
import datetime
import imghdr
import logging
import os
import shutil
import tempfile
import urllib

import bs4

from artexin import extract
from artexin import pack

from artexinweb import settings, utils, exceptions
from artexinweb.decorators import registered
from artexinweb.handlers.base import BaseJobHandler
from artexinweb.models import Job


logger = logging.getLogger(__name__)


class StandaloneHandler(BaseJobHandler):

    extractors = {
        'zip': utils.unzip
    }

    def is_html_file(self, filename):
        return any(filename.endswith(ext) for ext in ('htm', 'html'))

    def is_valid_target(self, target):
        if not os.path.isfile(target):
            msg = "File: {0} not found.".format(target)
            logger.error(msg)
            return False

        files = utils.list_zipfile(target)
        if not any(self.is_html_file(filename) for filename in files):
            msg = "No HTML file found in: {0}".format(target)
            logger.error(msg)
            return False

        return True

    def get_extractor(self, src_filepath):
        """Attempt to return a function which can perform extraction over the
        file, which path was passed in.

        :param src_filepath:  Full path of the to-be-extracted archive
        :returns:             An extractor function"""
        ext = utils.get_extension(src_filepath)
        try:
            return self.extractors[ext]
        except KeyError:
            msg = "Unsupported extension: {0}".format(src_filepath)
            raise exceptions.TaskHandlingError(msg)

    def extract_target(self, src_filepath):
        """Extract the passed in archive to a temporary folder for further
        processing.

        :param src_filepath:  Full path of the to-be-extraced archive
        :returns:             Full path to the destionation directory
        """
        extract = self.get_extractor(src_filepath)
        temp_dir = tempfile.mkdtemp()
        extract(src_filepath, temp_dir)

        return temp_dir

    def handle_task(self, task, options):
        temp_dir = self.extract_target(task.target)

        meta = options.get('meta', {})
        meta['url'] = options['origin']
        meta['domain'] = urllib.parse.urlparse(options['origin']).netloc
        # pre-specified title has precedence
        meta['title'] = meta.get('title') or self.read_title(temp_dir)
        meta['images'] = self.count_images(temp_dir)
        meta['timestamp'] = datetime.datetime.utcnow()

        out_dir = settings.BOTTLE_CONFIG['artexin.out_dir']
        meta = pack.create_zipball(src_dir=temp_dir,
                                   meta=meta,
                                   out_dir=out_dir)

        shutil.rmtree(temp_dir)

        return meta

    def read_title(self, target_dir):
        """Find the index html file in the passed in folder, then read and
        return it's title. If there are multiple html files in the folder,
        index.html takes precedence over the others. If there is no index.html,
        it falls back to any available html file.

        :param target_dir:  Full path to the folder to-be-scanned
        :returns:           str: title of html
        """
        html_files = [filename for filename in os.listdir(target_dir)
                      if self.is_html_file(filename)]
        try:
            # attempt to get an index.htm or index.html file
            (index_filename,) = [candidate for candidate in html_files
                                 if candidate.startswith('index.')]
        except ValueError:
            # fall back to any available html file
            index_filename = html_files[0]

        html_path = os.path.join(target_dir, index_filename)
        with codecs.open(html_path, 'r', 'utf-8') as html_file:
            soup = bs4.BeautifulSoup(html_file.read())

        return extract.get_title(soup)

    def count_images(self, target_dir):
        """Return the number of recursively counted image files in the passed
        in folder.

        :param target_dir:  Full path to the folder to-be-counted
        :returns:           int
        """
        is_image = lambda filename: imghdr.what(os.path.join(target_dir,
                                                             filename))

        count = 0
        for (dirpath, dirnames, filenames) in os.walk(target_dir):
            count += len([fname for fname in filenames if is_image(fname)])

        return count

    def handle_task_result(self, task, result, options):
        task.size = result['size']
        task.md5 = result['hash']
        task.title = result['title']
        task.images = result['images']
        task.timestamp = result['timestamp']
        task.mark_finished()  # implicit save


@registered(Job.STANDALONE)
def fetchable_handler(job_data):
    handler_instance = StandaloneHandler()
    handler_instance.run(job_data)
