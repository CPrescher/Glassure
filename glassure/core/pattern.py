# -*- coding: utf-8 -*-
from __future__ import annotations
import os

import numpy as np
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d


class Pattern(object):
    """
    A Pattern is a set of x and y values.
    It can be loaded from a file or created from scratch and can be modified by
    different methods.
    It builds the basis for all calculations in glassure.

    :param x: x values of the pattern
    :param y: y values of the pattern
    :param name: name of the pattern
    """

    def __init__(self, x: np.ndarray = None, y: np.ndarray = None, name: str = ''):
        """
        Creates a new Pattern object, x and y should have the same shape.
        """
        if x is None:
            self._x = np.linspace(0.1, 15, 100)
        else:
            self._x = x
        if y is None:
            self._y = np.log(self._x ** 2) - (self._x * 0.2) ** 2
        else:
            self._y = y
        self.name = name
        self.offset = 0.0
        self._scaling = 1.0
        self.smoothing = 0.0
        self.bkg_pattern = None

    def load(self, filename: str, skiprows: int = 0):
        """
        Loads a pattern from a file. The file can be either a .xy or a .chi file. The .chi file will be loaded with
        skiprows=4 by default.

        :param filename: path to the file
        :param skiprows: number of rows to skip when loading the data (header)
        """
        try:
            if filename.endswith('.chi'):
                skiprows = 4
            data = np.loadtxt(filename, skiprows=skiprows)
            self._x = data.T[0]
            self._y = data.T[1]
            self.name = os.path.basename(filename).split('.')[:-1][0]

        except ValueError:
            print('Wrong data format for pattern file! - ' + filename)
            return -1

    @staticmethod
    def from_file(filename: str, skip_rows: int = 0) -> Pattern | '-1':
        """
        Loads a pattern from a file. The file can be either a .xy or a .chi file. The .chi file will be loaded with
        skiprows=4 by default.

        :param filename: path to the file
        :param skip_rows: number of rows to skip when loading the data (header)
        """
        try:
            if filename.endswith('.chi'):
                skip_rows = 4
            data = np.loadtxt(filename, skiprows=skip_rows)
            x = data.T[0]
            y = data.T[1]
            name = os.path.basename(filename).split('.')[:-1][0]
            return Pattern(x, y, name)

        except ValueError:
            print('Wrong data format for pattern file! - ' + filename)
            return -1

    def save(self, filename: str, header: str = ''):
        """
        Saves the Pattern to a two-column xy file.

        :param filename: path to the file
        :param header: header to be written to the file
        """
        data = np.dstack((self._x, self._y))
        np.savetxt(filename, data[0], header=header)

    def set_background(self, pattern: Pattern):
        """
        Sets a background pattern to the current pattern. The background will be subtracted from the current pattern
        when calling the data property.

        :param pattern: Pattern to be used as background
        """
        self.bkg_pattern = pattern

    def reset_background(self):
        """
        Resets the background pattern to None.
        """
        self.bkg_pattern = None

    def set_smoothing(self, amount: float):
        """
        Sets the smoothing amount for the pattern. The smoothing will be applied when calling the data property.

        :param amount: amount of smoothing to be applied
        """
        self.smoothing = amount

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
        new_y = (np.histogram(x, bins, weights=y)
                 [0] / np.histogram(x, bins)[0])

        return Pattern(new_x, new_y)

    @property
    def data(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Returns the data of the pattern. If a background pattern is set, the background will be subtracted from the
        pattern. If smoothing is set, the pattern will be smoothed.

        :return: Tuple of x and y values
        """
        if self.bkg_pattern is not None:
            # create background function
            x_bkg, y_bkg = self.bkg_pattern.data

            if not np.array_equal(x_bkg, self._x):
                # the background will be interpolated
                f_bkg = interp1d(x_bkg, y_bkg, kind='linear')

                # find overlapping x and y values:
                ind = np.where((self._x <= np.max(x_bkg)) &
                               (self._x >= np.min(x_bkg)))
                x = self._x[ind]
                y = self._y[ind]

                if len(x) == 0:
                    # if there is no overlapping between background and pattern, raise an error
                    raise BkgNotInRangeError(self.name)

                y = y * self._scaling + self.offset - f_bkg(x)
            else:
                # if pattern and bkg have the same x basis we just delete y-y_bkg
                x, y = self._x, self._y * self._scaling + self.offset - y_bkg
        else:
            x, y = self.original_data

        if self.smoothing > 0:
            y = gaussian_filter1d(y, self.smoothing)
        return x, y

    @data.setter
    def data(self, data: tuple[np.ndarray, np.ndarray]):
        """
        Sets the data of the pattern. Also resets the scaling and offset to 1 and 0 respectively.

        :param data: tuple of x and y values
        """
        (x, y) = data
        self._x = x
        self._y = y
        self.scaling = 1.0
        self.offset = 0

    @property
    def original_data(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Returns the original data of the pattern without any background subtraction or smoothing.

        :return: tuple of x and y values
        """
        return self._x, self._y * self._scaling + self.offset

    @property
    def x(self) -> np.ndarray:
        """ Returns the x values of the pattern """
        return self._x

    @x.setter
    def x(self, new_value: np.ndarray):
        """ Sets the x values of the pattern """
        self._x = new_value

    @property
    def y(self) -> np.ndarray:
        """ Returns the y values of the pattern """
        return self._y

    @y.setter
    def y(self, new_y: np.ndarray):
        """ Sets the y values of the pattern """
        self._y = new_y

    @property
    def scaling(self) -> float:
        """ Returns the scaling of the pattern """
        return self._scaling

    @scaling.setter
    def scaling(self, value):
        """ 
        Sets the scaling of the pattern, if below 0, it will be set to 0 
        instead.
        """
        if value < 0:
            self._scaling = 0.0
        else:
            self._scaling = value

    def limit(self, x_min: float, x_max: float) -> Pattern:
        """
        Limits the pattern to a specific x-range. Does not modify inplace but returns a new limited Pattern

        :param x_min: lower limit of the x-range
        :param x_max: upper limit of the x-range
        :return: limited Pattern
        """
        x, y = self.data
        return Pattern(x[np.where((x_min < x) & (x < x_max))],
                       y[np.where((x_min < x) & (x < x_max))])

    def extend_to(self, x_value: float, y_value: float) -> Pattern:
        """
        Extends the current pattern to a specific x_value by filling it with the y_value. Does not modify inplace but
        returns a new filled Pattern

        :param x_value: Point to which extending the pattern should be smaller than the lowest x-value in the pattern or
        vice versa
        :param y_value: number to fill the pattern with
        :return: extended Pattern
        """
        x_step = np.mean(np.diff(self.x))
        x_min = np.min(self.x)
        x_max = np.max(self.x)
        if x_value < x_min:
            x_fill = np.arange(x_min - x_step, x_value -
                               x_step * 0.5, -x_step)[::-1]
            y_fill = np.zeros(x_fill.shape)
            y_fill.fill(y_value)

            new_x = np.concatenate((x_fill, self.x))
            new_y = np.concatenate((y_fill, self.y))
        elif x_value > x_max:
            x_fill = np.arange(x_max + x_step, x_value + x_step * 0.5, x_step)
            y_fill = np.zeros(x_fill.shape)
            y_fill.fill(y_value)

            new_x = np.concatenate((self.x, x_fill))
            new_y = np.concatenate((self.y, y_fill))
        else:
            return self

        return Pattern(new_x, new_y)

    def to_dict(self) -> dict:
        """
        Returns a dictionary representation of the pattern which can be used to save the pattern to a json file.

        :return: dictionary representation of the pattern
        """
        return {
            'name': self.name,
            'x': self.x.tolist(),
            'y': self.y.tolist(),
            'scaling': self.scaling,
            'offset': self.offset,
            'smoothing': self.smoothing,
            'bkg_pattern': self.bkg_pattern.to_dict() if self.bkg_pattern is
                                                         not None else None
        }

    @staticmethod
    def from_dict(json_dict: dict) -> Pattern:
        """
        Creates a new Pattern from a dictionary representation of a Pattern.

        :param json_dict: dictionary representation of a Pattern
        :return: new Pattern
        """
        pattern = Pattern(np.array(json_dict['x']),
                          np.array(json_dict['y']),
                          json_dict['name'])

        pattern.scaling = json_dict['scaling']
        pattern.offset = json_dict['offset']
        pattern.smoothing = json_dict['smoothing']

        if json_dict['bkg_pattern'] is not None:
            bkg_pattern = Pattern.from_dict(json_dict['bkg_pattern'])
        else:
            bkg_pattern = None
        pattern.bkg_pattern = bkg_pattern

        return pattern

    ###########################################################
    # Operators:

    def __sub__(self, other: Pattern) -> Pattern:
        """
        Subtracts the other pattern from the current one. If the other pattern
        has a different shape, the subtraction will be done on the overlapping
        x-values and the background will be interpolated. If there is no
        overlapping between the two patterns, a BkgNotInRangeError will be
        raised.

        :param other: Pattern to be subtracted
        :return: new Pattern
        """
        orig_x, orig_y = self.data
        other_x, other_y = other.data

        if orig_x.shape != other_x.shape:
            # todo different shape subtraction of spectra seems the fail somehow...
            # the background will be interpolated
            other_fcn = interp1d(other_x, other_y, kind='linear')

            # find overlapping x and y values:
            ind = np.where((orig_x <= np.max(other_x)) &
                           (orig_x >= np.min(other_x)))
            x = orig_x[ind]
            y = orig_y[ind]

            if len(x) == 0:
                # if there is no overlapping between background and pattern, raise an error
                raise BkgNotInRangeError(self.name)
            return Pattern(x, y - other_fcn(x))
        else:
            return Pattern(orig_x, orig_y - other_y)

    def __add__(self, other: Pattern) -> Pattern:
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
        other_x, other_y = other.data

        if orig_x.shape != other_x.shape:
            # the background will be interpolated
            other_fcn = interp1d(other_x, other_y, kind='linear')

            # find overlapping x and y values:
            ind = np.where((orig_x <= np.max(other_x)) &
                           (orig_x >= np.min(other_x)))
            x = orig_x[ind]
            y = orig_y[ind]

            if len(x) == 0:
                # if there is no overlapping between background and pattern, raise an error
                raise BkgNotInRangeError(self.name)
            return Pattern(x, y + other_fcn(x))
        else:
            return Pattern(orig_x, orig_y + other_y)

    def __rmul__(self, other: float) -> Pattern:
        """
        Multiplies the pattern with a scalar.

        :param other: scalar to multiply with
        :return: new Pattern
        """
        orig_x, orig_y = self.data
        return Pattern(np.copy(orig_x), np.copy(orig_y) * other)

    def __eq__(self, other: Pattern) -> bool:
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


class BkgNotInRangeError(Exception):
    def __init__(self, pattern_name: str):
        self.pattern_name = pattern_name

    def __str__(self):
        return "The background range does not overlap with the Pattern range for " + self.pattern_name
