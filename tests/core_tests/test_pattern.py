# -*- coding: utf-8 -*-
import numpy as np
from pytest import approx
from pydantic import BaseModel
from glassure.core.pattern import PydanticNpArray

from glassure.core import Pattern


def test_plus_and_minus_operators():
    x = np.linspace(0, 10, 100)
    pattern1 = Pattern(x, np.sin(x))
    pattern2 = Pattern(x, np.sin(x))

    pattern3 = pattern1 + pattern2
    assert np.array_equal(pattern3.y, np.sin(x) * 2)
    assert np.array_equal(pattern2.y, np.sin(x) * 1)
    assert np.array_equal(pattern1.y, np.sin(x) * 1)

    pattern3 = pattern1 + pattern1
    assert np.array_equal(pattern3.y, np.sin(x) * 2)
    assert np.array_equal(pattern1.y, np.sin(x) * 1)
    assert np.array_equal(pattern1.y, np.sin(x) * 1)

    pattern3 = pattern2 - pattern1
    assert np.array_equal(pattern3.y, np.sin(x) * 0)
    assert np.array_equal(pattern2.y, np.sin(x) * 1)
    assert np.array_equal(pattern1.y, np.sin(x) * 1)

    pattern3 = pattern1 - pattern1
    assert np.array_equal(pattern3.y, np.sin(x) * 0)
    assert np.array_equal(pattern1.y, np.sin(x) * 1)
    assert np.array_equal(pattern1.y, np.sin(x) * 1)


def test_plus_and_minus_operators_with_different_x():
    x1 = np.linspace(1, 9, 1000)
    x2 = np.linspace(0, 10, 998)
    pattern1 = Pattern(x1, np.sin(x1))
    pattern2 = Pattern(x2, np.sin(x2))

    pattern3 = pattern1 + pattern2
    assert np.array_equal(pattern3.x, x1)
    np.testing.assert_array_almost_equal(pattern3.y, np.sin(x1) * 2, decimal=5)

    pattern3 = pattern1 - pattern2
    np.testing.assert_array_almost_equal(pattern3.y, np.sin(x1) * 0, decimal=5)


def test_plus_and_minus_operators_with_floats():
    x = np.linspace(0, 10, 100)
    pattern = Pattern(np.linspace(0, 10, 100), np.ones_like(x))

    pattern1 = pattern + 1
    assert np.array_equal(pattern1.y, np.ones_like(x) + 1)

    pattern2 = 1 + pattern
    assert np.array_equal(pattern2.y, np.ones_like(x) + 1)

    pattern3 = pattern - 1
    assert np.array_equal(pattern3.y, np.ones_like(x) - 1)

    pattern4 = 1 - pattern
    assert np.array_equal(pattern4.y, 1 - np.ones_like(x))


def test_multiply_operator():
    x = np.linspace(0, 10, 100)
    pattern = 2 * Pattern(x, np.sin(x))

    assert np.array_equal(pattern.y, np.sin(x) * 2)

    pattern = Pattern(x, np.sin(x)) * 2
    assert np.array_equal(pattern.y, np.sin(x) * 2)


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
    pattern = Pattern(np.arange(10), np.arange(10), "test")
    pattern_json = pattern.to_dict()
    assert pattern_json["x"] == list(pattern.x)
    assert pattern_json["y"] == list(pattern.y)
    assert pattern_json["name"] == pattern.name


def test_from_dict():
    pattern1 = Pattern(np.arange(10), np.arange(10))
    pattern1.name = "test"
    pattern_json = pattern1.to_dict()

    pattern2 = Pattern.from_dict(pattern_json)
    assert np.array_equal(pattern1.x, pattern2.x)
    assert np.array_equal(pattern1.y, pattern2.y)
    assert pattern1.name == pattern2.name


class TestModel(BaseModel):
    x: PydanticNpArray


def test_pydantic_nparray_with_array_input():
    input_array = np.linspace(0, 10, 1000)
    t = TestModel(x=input_array)
    json = t.model_dump()
    t = TestModel(**json)
    assert np.array_equal(t.x, input_array)

def test_pydantic_nparray_with_list_input():
    input_array = np.array([1, 2, 3])
    t = TestModel(x=input_array.tolist())
    assert np.array_equal(t.x, input_array)
    json = t.model_dump()
    t = TestModel(**json)
    assert np.array_equal(t.x, input_array)

def test_pydantic_nparray_from_json():
    input = {"x": [1, 2, 3]}
    t = TestModel(**input)
    assert np.array_equal(t.x, np.array([1, 2, 3]))
