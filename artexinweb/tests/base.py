# -*- coding: utf-8 -*-
import uuid


class BaseMongoTestCase(object):

    mongodb_name = 'test_{0}'.format(uuid.uuid4())

    def setup_method(self, method):
        from mongoengine.connection import connect, disconnect
        disconnect()
        connect(self.mongodb_name)

    def teardown_method(self, method):
        from mongoengine.connection import get_connection, disconnect
        connection = get_connection()
        connection.drop_database(self.mongodb_name)
        disconnect()
