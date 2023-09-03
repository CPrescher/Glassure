# -*- coding: utf-8 -*-
import numpy as np
from pytest import approx

from glassure.core import Pattern


def test_plus_and_minus_operators():
    x = np.linspace(0, 10, 100)
    pattern1 = Pattern(x, np.sin(x))
    pattern2 = Pattern(x, np.sin(x))

    pattern3 = pattern1 + pattern2
    assert np.array_equal(pattern3._y, np.sin(x) * 2)
    assert np.array_equal(pattern2._y, np.sin(x) * 1)
    assert np.array_equal(pattern1._y, np.sin(x) * 1)

    pattern3 = pattern1 + pattern1
    assert np.array_equal(pattern3._y, np.sin(x) * 2)
    assert np.array_equal(pattern1._y, np.sin(x) * 1)
    assert np.array_equal(pattern1._y, np.sin(x) * 1)

    pattern3 = pattern2 - pattern1
    assert np.array_equal(pattern3._y, np.sin(x) * 0)
    assert np.array_equal(pattern2._y, np.sin(x) * 1)
    assert np.array_equal(pattern1._y, np.sin(x) * 1)

    pattern3 = pattern1 - pattern1
    assert np.array_equal(pattern3._y, np.sin(x) * 0)
    assert np.array_equal(pattern1._y, np.sin(x) * 1)
    assert np.array_equal(pattern1._y, np.sin(x) * 1)


def test_multiply_operator():
    x = np.linspace(0, 10, 100)
    pattern = 2 * Pattern(x, np.sin(x))

    assert np.array_equal(pattern._y, np.sin(x) * 2)


def test_equality_operator():
    x = np.linspace(0, 10, 100)
    pattern1 = Pattern(x, np.sin(x))
    pattern2 = Pattern(x, np.sin(2 * x))

    assert pattern1 == pattern1
    assert pattern1 != pattern2


def test_binning():
    x = np.linspace(2.8, 10.8, 100)
    pattern = Pattern(x, np.sin(x))
    binned_pattern = pattern.rebin(1)
    assert np.sum(binned_pattern.y), np.sum(pattern.y)


def test_extend_to():
    x = np.arange(2.8, 10, 0.2)

    pattern = Pattern(x, x - 2)
    extended_pattern = pattern.extend_to(0, 0)

    assert np.sum(extended_pattern.limit(0, 2.7).y) == approx(0)
    assert extended_pattern.x[0] == approx(0)

    pos_extended_pattern = pattern.extend_to(20, 5)

    assert np.mean(pos_extended_pattern.limit(10.1, 21).y) == 5
    assert pos_extended_pattern.x[-1] == approx(20)


def test_to_dict():
    pattern = Pattern(np.arange(10), np.arange(10))
    pattern.name = 'test'
    pattern.scaling = 3
    pattern.smoothing = 2
    pattern.bkg_pattern = Pattern(np.arange(10), np.arange(10))
    pattern_json = pattern.to_dict()
    assert pattern_json['x'] == list(pattern.x)
    assert pattern_json['y'] == list(pattern.y)
    assert pattern_json['name'] == pattern.name
    assert pattern_json['scaling'] == pattern.scaling
    assert pattern_json['smoothing'] == pattern.smoothing
    assert pattern_json['bkg_pattern'] == pattern.bkg_pattern.to_dict()


def test_from_dict():
    pattern1 = Pattern(np.arange(10), np.arange(10))
    pattern1.name = 'test'
    pattern1.scaling = 3
    pattern1.smoothing = 2
    pattern1.bkg_pattern = Pattern(np.arange(10), np.arange(10))
    pattern_json = pattern1.to_dict()

    pattern2 = Pattern.from_dict(pattern_json)
    assert np.array_equal(pattern1.x, pattern2.x)
    assert np.array_equal(pattern1.y, pattern2.y)
    assert pattern1.name == pattern2.name
    assert pattern1.scaling == pattern2.scaling
    assert pattern1.smoothing == pattern2.smoothing
    assert np.array_equal(pattern1.bkg_pattern.x, pattern2.bkg_pattern.x)
    assert np.array_equal(pattern1.bkg_pattern.y, pattern2.bkg_pattern.y)
