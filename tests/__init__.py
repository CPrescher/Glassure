# -*- coding: utf-8 -*-

import os

unittest_data_path = os.path.join(os.path.dirname(__file__), 'data')


def data_path(filename):
    return os.path.join(unittest_data_path, filename)
