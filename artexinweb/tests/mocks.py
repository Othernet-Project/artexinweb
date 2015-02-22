# -*- coding: utf-8 -*-
from contextlib import ContextDecorator
from unittest import mock


class mock_bottle_config(ContextDecorator):

    def __init__(self, config_path, mock_config):
        self.config_path = config_path
        self.mock_config = mock_config

    def __enter__(self):
        self.patcher = mock.patch(self.config_path)
        self.config = self.patcher.start()
        self.config.__getitem__ = lambda inst, key: self.mock_config.__getitem__(key)

    def __exit__(self, *exc):
        self.patcher.stop()
