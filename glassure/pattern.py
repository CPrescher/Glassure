# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from typing_extensions import Annotated
from typing import Union, Optional, TYPE_CHECKING, Sequence, Any
from pydantic import (
    PlainSerializer,
    PlainValidator,
    BaseModel,
    ConfigDict,
    model_validator,
)
import numpy as np
import base64
import gzip

import io
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d


class Pattern(BaseModel):
    """
    A Pattern is a set of x and y values.
    It can be loaded from a file or created from scratch and can be modified by
    different methods.
    It builds the basis for all calculations in glassure.

    :param x: x values of the pattern
    :param y: y values of the pattern
    :param name: name of the pattern
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    x: PydanticNpArray
    y: PydanticNpArray
    name: str = ""

    def __init__(
        self,
        x: Optional[PydanticNpArray] = None,
        y: Optional[PydanticNpArray] = None,
        name: str = "",
        **data: Any,
    ):
        """
        Initialize a Pattern with x and y values.

        If both x and y are None, creates a default pattern.
        If only one of x or y is provided, raises ValueError.
        """
        if x is None and y is None:
            x = np.linspace(0, 10, 101)
            y = np.log(x**2) - (x * 0.2) ** 2
        elif x is None or y is None:
            raise ValueError("Either both x and y must be provided or neither.")

        super().__init__(x=x, y=y, name=name, **data)

    @model_validator(mode="after")
    def _validate_lengths(self) -> "Pattern":
        """Validate that x and y have the same length."""
        if len(self.x) != len(self.y):
            raise ValueError("x and y values must have the same length")
        return self

    def load(self, filename: str, skiprows: int = 0):
        """
        Loads a pattern from a file. The file can be either a .xy or a .chi file. The .chi file will be loaded with
        skiprows=4 by default.

        :param filename: path to the file
        :param skiprows: number of rows to skip when loading the data (header)
        :raises PatternLoadError: if the file cannot be loaded
        """
        try:
            if filename.endswith(".chi"):
                skiprows = 4
            data = np.loadtxt(filename, skiprows=skiprows)
            self.x = data.T[0]
            self.y = data.T[1]
            self.name = os.path.basename(filename).split(".")[:-1][0]

        except FileNotFoundError:
            raise PatternLoadError(filename, "File not found")
        except OSError as e:
            raise PatternLoadError(filename, f"OS error: {e}")
        except ValueError as e:
            raise PatternLoadError(filename, f"Wrong data format: {e}")
        except Exception as e:
            raise PatternLoadError(filename, f"Unexpected error: {e}")

    @staticmethod
    def from_file(filename: str, skip_rows: int = 0) -> Pattern:
        """
        Loads a pattern from a file. The file can be either a .xy or a .chi file. The .chi file will be loaded with
        skiprows=4 by default.

        :param filename: path to the file
        :param skip_rows: number of rows to skip when loading the data (header)
        :return: Pattern object loaded from the file
        :raises PatternLoadError: if the file cannot be loaded
        """
        try:
            if filename.endswith(".chi"):
                skip_rows = 4
            data = np.loadtxt(filename, skiprows=skip_rows)
            x = data.T[0]
            y = data.T[1]
            name = os.path.basename(filename).split(".")[:-1][0]
            return Pattern(x, y, name)

        except FileNotFoundError:
            raise PatternLoadError(filename, "File not found")
        except OSError as e:
            raise PatternLoadError(filename, f"OS error: {e}")
        except ValueError as e:
            raise PatternLoadError(filename, f"Wrong data format: {e}")
        except Exception as e:
            raise PatternLoadError(filename, f"Unexpected error: {e}")

    def save(self, filename: str, header: str = ""):
        """
        Saves the Pattern to a two-column xy file.

        :param filename: path to the file
        :param header: header to be written to the file
        """
        x, y = self.data
        data = np.dstack((x, y))
        np.savetxt(filename, data[0], header=header)

    def smooth(self, amount: float) -> Pattern:
        """
        Smoothing the pattern by applying a gaussian filter. Returns the smoothed pattern.
        :param amount: amount of smoothing to be applied
        """
        x, y = self.data
        return Pattern(x, gaussian_filter1d(y, amount))

    def rebin(self, bin_size: float) -> Pattern:
        """
        Returns a new pattern, which is a rebinned version of the current one.

        :param bin_size: Size of the bins
        :return: rebinned Pattern
        """
        x, y = self.data
        x_min = np.round(np.min(x) / bin_size) * bin_size
        x_max = np.round(np.max(x) / bin_size) * bin_size
        new_x = np.arange(x_min, x_max + 0.1 * bin_size, bin_size)

        bins = np.hstack((x_min - bin_size * 0.5, new_x + bin_size * 0.5))
        new_y = np.histogram(x, bins, weights=y)[0] / np.histogram(x, bins)[0]

        return Pattern(new_x, new_y)

    @property
    def data(self) -> tuple[PydanticNpArray, PydanticNpArray]:
        """
        Returns the data of the pattern as a tuple of x and y values.

        :return: tuple of x and y values
        """
        return self.x, self.y

    @data.setter
    def data(self, data: tuple[np.ndarray, np.ndarray]):
        """
        Sets the data of the pattern. Also resets the scaling and offset to 1 and 0 respectively.

        :param data: tuple of x and y values
        """
        x_values, y_values = data
        if len(x_values) != len(y_values):
            raise ValueError("x and y values must have the same length")
        self.x = x_values
        self.y = y_values

    def limit(self, x_min: float, x_max: float) -> Pattern:
        """
        Limits the pattern to a specific x-range. Does not modify inplace but returns a new limited Pattern

        :param x_min: lower limit of the x-range
        :param x_max: upper limit of the x-range
        :return: limited Pattern
        """
        x, y = self.data
        x_limited = x[np.where((x_min < x) & (x < x_max))]
        y_limited = y[np.where((x_min < x) & (x < x_max))]
        return Pattern(x_limited, y_limited)

    def extend_to(self, x_value: float, y_value: float) -> Pattern:
        """
        Extends the current pattern to a specific x_value by filling it with the y_value. Does not modify inplace but
        returns a new filled Pattern

        :param x_value: Point to which extending the pattern should be smaller than the lowest x-value in the pattern or
        vice versa
        :param y_value: number to fill the pattern with
        :return: extended Pattern
        """
        x, y = self.data
        x_step = np.mean(np.diff(x))
        x_min = np.min(x)
        x_max = np.max(x)
        if x_value < x_min:
            x_fill = np.arange(x_min - x_step, x_value - x_step * 0.5, -x_step)[::-1]
            y_fill = np.zeros(x_fill.shape)
            y_fill.fill(y_value)

            new_x = np.concatenate((x_fill, x))
            new_y = np.concatenate((y_fill, y))
        elif x_value > x_max:
            x_fill = np.arange(x_max + x_step, x_value + x_step * 0.5, x_step)
            y_fill = np.zeros(x_fill.shape)
            y_fill.fill(y_value)

            new_x = np.concatenate((x, x_fill))
            new_y = np.concatenate((y, y_fill))
        else:
            return self

        return Pattern(new_x, new_y)

    def to_dict(self) -> dict:
        """
        Returns a dictionary representation of the pattern with x and y as plain lists.
        For JSON serialization with base64-encoded arrays, use model_dump() instead.

        :return: dictionary representation of the pattern
        """
        x, y = self.data
        return {
            "name": self.name,
            "x": x.tolist(),
            "y": y.tolist(),
        }

    @staticmethod
    def from_dict(json_dict: dict) -> Pattern:
        """
        Creates a new Pattern from a dictionary representation of a Pattern.

        :param json_dict: dictionary representation of a Pattern
        :return: new Pattern
        """
        return Pattern(
            np.array(json_dict["x"]), np.array(json_dict["y"]), json_dict.get("name", "")
        )

    ###########################################################
    # Operators:

    def __sub__(self, other: Union[float, Pattern]) -> Pattern:
        """
        Subtracts a float or another pattern from the current one. If the other pattern
        has a different shape, the subtraction will be done on the overlapping
        x-values and the background will be interpolated. If there is no
        overlapping between the two patterns, a BkgNotInRangeError will be
        raised.

        :param other: Pattern to be subtracted
        :return: new Pattern
        """
        return self.__add__(-1 * other)

    def __rsub__(self, other: Union[float, Pattern]) -> Pattern:
        """
        Subtracts the pattern from a float or another pattern. If the other
        pattern has a different shape, the subtraction will be done on the
        overlapping x-values and the background will be interpolated. If there
        is no overlapping between the two patterns, a BkgNotInRangeError will
        be raised.

        :param other: float or Pattern to be subtracted
        :return: new Pattern
        """
        return -1 * self.__sub__(other)

    def __add__(self, other: Union[float, Pattern]) -> Pattern:
        """
        Adds the other pattern to the current one. If the other pattern
        has a different shape, the addition will be done on the overlapping
        x-values and the y-values of the other pattern will be interpolated.
        If there is no overlapping between the two patterns, a BkgNotInRangeror
        will be raised.

        :param other: Pattern to be added
        :return: new Pattern
        """
        orig_x, orig_y = self.data

        if isinstance(other, (int, float)):
            return Pattern(orig_x, orig_y + other)

        other_x, other_y = other.data

        if orig_x.shape != other_x.shape:
            # the background will be interpolated
            other_fcn = interp1d(other_x, other_y, kind="linear")

            # find overlapping x and y values:
            ind = np.where((orig_x <= np.max(other_x)) & (orig_x >= np.min(other_x)))
            x = orig_x[ind]
            y = orig_y[ind]

            if len(x) == 0:
                # if there is no overlapping between background and pattern, raise an error
                raise BkgNotInRangeError(self.name)
            return Pattern(x, y + other_fcn(x))
        else:
            return Pattern(orig_x, orig_y + other_y)

    def __radd__(self, other: Union[float, Pattern]) -> Pattern:
        """
        Adds the other pattern to the current one. If the other pattern
        has a different shape, the addition will be done on the overlapping
        x-values and the y-values of the other pattern will be interpolated.
        If there is no overlapping between the two patterns, a BkgNotInRangeror
        will be raised.

        :param other: Pattern to be added
        :return: new Pattern
        """
        return self.__add__(other)

    def __rmul__(self, other: Union[float, np.ndarray, Sequence[float]]) -> Pattern:
        """
        Multiplies the pattern with a scalar or an array-like of the same shape as the y-values.

        :param other: scalar or array-like to multiply with
        :return: new Pattern
        """
        orig_x, orig_y = self.data
        multiplier = self._normalize_multiplier(other, orig_y.shape)
        return Pattern(np.copy(orig_x), np.multiply(orig_y, multiplier))

    def __mul__(self, other: Union[float, np.ndarray, Sequence[float]]) -> Pattern:
        """
        Multiplies the pattern with a scalar or an array-like of the same shape as the y-values.

        :param other: scalar or array-like to multiply with
        :return: new Pattern
        """
        return self.__rmul__(other)

    def __eq__(self, other: object) -> bool:
        """
        Checks if two patterns are equal. Two patterns are equal if their data
        is equal.

        :param other: Pattern to compare with
        :return: True if equal, False otherwise
        """
        if not isinstance(other, Pattern):
            return False
        if np.array_equal(self.data, other.data):
            return True
        return False

    @staticmethod
    def _normalize_multiplier(
        multiplier: Union[float, np.ndarray, Sequence[float]], target_shape: tuple[int, ...]
    ) -> np.ndarray:
        """
        Normalizes the multiplier to a float or an array of the same shape as the target shape.
        :param multiplier: The multiplier to normalize
        :param target_shape: The shape of the target array
        :return: The normalized multiplier
        """
        array_multiplier = np.asarray(multiplier, dtype=float)
        if array_multiplier.ndim == 0:
            return array_multiplier
        if array_multiplier.shape != target_shape:
            raise ValueError(
                "Array multiplier must have the same shape as the pattern's y values."
            )
        return array_multiplier


class BkgNotInRangeError(Exception):
    def __init__(self, pattern_name: str):
        self.pattern_name = pattern_name

    def __str__(self):
        return (
            "The background range does not overlap with the Pattern range for "
            + self.pattern_name
        )


class PatternLoadError(Exception):
    """Exception raised when a pattern file cannot be loaded."""

    def __init__(self, filename: str, reason: str):
        self.filename = filename
        self.reason = reason

    def __str__(self):
        return f"Failed to load pattern from file '{self.filename}': {self.reason}"


def validate(value):
    """
    Validates a numpy array. If the value is a list, it is converted to a numpy array.
    If the value is a string, it is decoded from a base64 encoded string.
    If the value is already a numpy array, it is returned as is.

    :param value: The value to validate
    :return: The validated numpy array
    """
    if isinstance(value, list):
        return np.array(value)
    if isinstance(value, str):
        try:
            v = base64.b64decode(value)
            v = gzip.decompress(v)
            numpy_array = np.load(io.BytesIO(v), allow_pickle=False)
            return numpy_array
        except Exception as e:
            raise ValueError(f"Could not decode numpy array: {e}")
    if isinstance(value, np.ndarray):
        return value
    raise TypeError(f"Invalid type for numpy array: {type(value)}")


def serialize(value):
    """
    Serializes a numpy array to a base64 encoded string.
    If the value is a numpy array, it is saved to a compressed bytes buffer and then encoded to a base64 string.
    If the value is a list, it is converted to a numpy array and then serialized.
    If the value is a string, it is decoded from a base64 encoded string and then deserialized.
    If the value is already a numpy array, it is returned as is.

    :param value: The value to serialize
    :return: The serialized numpy array
    """
    if isinstance(value, (list, np.ndarray)):
        # Save numpy array to compressed bytes buffer
        with io.BytesIO() as buffer:
            np.save(buffer, value, allow_pickle=False)
            binary_data = buffer.getvalue()
        compressed_data = gzip.compress(binary_data)
        base_64_data = base64.b64encode(compressed_data).decode("utf-8")
        return base_64_data
    raise TypeError(f"Invalid type for numpy array: {type(value)}")


"""
This is a workaround to allow numpy arrays to be used as fields in a pydantic model.
It is necessary because pydantic does not support numpy arrays as fields.
We use a custom validator and serializer to convert the numpy array to a base64 encoded string
and back again.
"""
if TYPE_CHECKING:
    PydanticNpArray = np.ndarray
else:
    PydanticNpArray = Annotated[
        np.ndarray, PlainValidator(validate), PlainSerializer(serialize)
    ]
