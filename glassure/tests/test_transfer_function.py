# -*- coding: utf8 -*-

import os
import unittest
import numpy as np

from core import Pattern
from core.transfer_function import calculate_transfer_function

unittest_data_path = os.path.join(os.path.dirname(__file__), 'data')
sample_path = os.path.join(unittest_data_path, 'glass_rod_SS.xy')
std_path = os.path.join(unittest_data_path, 'glass_rod_WOS.xy')


class TransferFunctionTest(unittest.TestCase):

    def test_transfer_function_calculation(self):
        std_pattern = Pattern.from_file(std_path).limit(0, 14)
        sample_pattern = Pattern.from_file(sample_path).limit(0, 14)
        transfer_function = calculate_transfer_function(std_pattern, sample_pattern)
        test_y = sample_pattern.y * transfer_function(sample_pattern.x)
        self.assertAlmostEqual(np.std(std_pattern.y/test_y), 0, delta=0.02)
