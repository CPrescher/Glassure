# -*- coding: utf-8 -*-
import re
from typing import Optional, Union, Dict
from collections import defaultdict
from copy import copy

import numpy as np
from scipy import interpolate
import scipy.constants as const

import lmfit

from .scattering_factors import (
    calculate_coherent_scattering_factor,
    calculate_incoherent_scattered_intensity,
)
from . import Pattern
from . import scattering_factors

__all__ = [
    "calculate_f_mean_squared",
    "calculate_f_squared_mean",
    "calculate_incoherent_scattering",
    "extrapolate_to_zero_linear",
    "extrapolate_to_zero_poly",
    "extrapolate_to_zero_spline",
    "calculate_s0",
    "extrapolate_to_zero_step",
    "convert_density_to_atoms_per_cubic_angstrom",
    "normalize_composition",
    "convert_two_theta_to_q_space",
    "convert_two_theta_to_q_space_raw",
    "calculate_weighting_factor",
]

Composition = Dict[str, Union[int, float]]


def parse_str_to_composition(formula: str) -> Composition:
    """
    Parses a chemical formula string into a dictionary with elements as keys and abundances as relative numbers.
    Typical examples are 'SiO2'-> {'Si': 1, 'O': 2} or 'Na2Si2O5' -> {'Na': 2, 'Si': 2, 'O': 5}

    :param formula: chemical formula string
    :return: Composition with elements as keys and abundances as relative numbers
    """
    # Remove all whitespace from the formula
    formula = re.sub(r"\s+", "", formula)

    def parse_segment(segment):
        element_pattern = r"([A-Z][a-z]*)(\d*\.\d+|\d*)"
        parsed = defaultdict(float)
        for element, count in re.findall(element_pattern, segment):
            parsed[element] += float(count) if count else 1.0
        return parsed

    def multiply_segment(segment_dict, multiplier):
        for element in segment_dict:
            segment_dict[element] *= multiplier
        return segment_dict

    def process_brackets(formula):
        bracket_patterns = [
            r"\(([^\(\)]+)\)(\d*\.\d+|\d*)",  # ()
            r"\[([^\[\]]+)\](\d*\.\d+|\d*)",  # []
            r"\{([^\{\}]+)\}(\d*\.\d+|\d*)",  # {}
        ]

        while any(re.search(pattern, formula) for pattern in bracket_patterns):
            for pattern in bracket_patterns:
                while re.search(pattern, formula):
                    matches = re.findall(pattern, formula)
                    for sub_formula, count in matches:
                        parsed_sub_formula = parse_segment(sub_formula)
                        multiplier = float(count) if count else 1.0
                        parsed_sub_formula = multiply_segment(
                            parsed_sub_formula, multiplier
                        )
                        sub_formula_string = "".join(
                            [
                                f"{el}{parsed_sub_formula[el]}"
                                for el in parsed_sub_formula
                            ]
                        )
                        formula = formula.replace(
                            f"({sub_formula}){count}", sub_formula_string, 1
                        )
                        formula = formula.replace(
                            f"[{sub_formula}]{count}", sub_formula_string, 1
                        )
                        formula = formula.replace(
                            f"{{{sub_formula}}}{count}", sub_formula_string, 1
                        )
        return formula

    # Process all brackets first
    formula = process_brackets(formula)

    # Parse the final expanded formula
    final_parsed = parse_segment(formula)
    return dict(final_parsed)


def calculate_f_mean_squared(
    composition: Composition, q: np.ndarray, sf_source="hajdu"
) -> np.ndarray:
    """
    Calculates the square of the mean form factor for a given composition over q.

    :param composition: dictionary with elements as key and abundances as relative numbers
    :param q: Q value or numpy array with a unit of A^-1
    :param sf_source: source of the scattering factors. Possible sources are 'hajdu' and 'brown_hubbell'.
    """
    norm_elemental_abundances = normalize_composition(composition)

    res = np.zeros_like(q)
    for element, amount in norm_elemental_abundances.items():
        res = res + amount * calculate_coherent_scattering_factor(element, q, sf_source)

    return res**2


def calculate_f_squared_mean(
    composition: Composition, q: np.ndarray, sf_source: str = "hajdu"
) -> np.ndarray:
    """
    Calculates the mean of the squared form factors for a given composition for a given q vector.

    :param composition: dictionary with elements as key and abundances as relative numbers
    :param q: Q value or numpy array with a unit of A^-1
    :param sf_source: source of the scattering factors. Possible sources are 'hajdu' and 'brown_hubbell'.

    :return: mean of the squared form factors
    """
    norm_elemental_abundances = normalize_composition(composition)

    res = np.zeros_like(q)
    for key, value in norm_elemental_abundances.items():
        res = res + value * calculate_coherent_scattering_factor(key, q, sf_source) ** 2
    return res


def calculate_incoherent_scattering(
    composition: Composition, q: np.ndarray, sf_source: str = "hajdu"
) -> np.ndarray:
    """
    Calculates compton/incoherent scattering for a given composition

    :param composition: dictionary with elements as key and abundances as relative numbers
    :param q: Q value or numpy array with a unit of A^-1
    :param sf_source: source of the scattering factors. Possible sources are 'hajdu' and 'brown_hubbell'.

    :return: incoherent scattering array
    """
    norm_elemental_abundances = normalize_composition(composition)

    res = np.zeros_like(q)
    for key, value in norm_elemental_abundances.items():
        res += value * calculate_incoherent_scattered_intensity(key, q, sf_source)
    return res


def calculate_s0(composition: Composition, sf_source: str = "hajdu") -> float:
    """
    Calculates the I0 value for a given composition by extrapolating the coherent scattering factor to zero where I(Q)
    and the Compton scattering should have zero intensities.

    :param composition: dictionary with elements as keys and abundances as relative numbers
    :param sf_source: source of the scattering factors. Possible sources are 'hajdu' and 'brown_hubbell'.

    :return: I0 value
    """
    f_mean_squared = calculate_f_mean_squared(composition, np.array([0]), sf_source)
    f_squared_mean = calculate_f_squared_mean(composition, np.array([0]), sf_source)

    s0 = -f_squared_mean / f_mean_squared + 1
    return s0[0]


def calculate_kn_correction(
    q: Union[np.ndarray, float], wavelength: float
) -> np.ndarray:
    """
    Calculates the Klein-Nishina correction for given q-values and wavelength. This
    is a correction which should be applied to the incoherent scattering intensity, due
    to the fact that the Compton scattering is chaning Energy with the scattering angle.

    :param q: Q value or numpy array with a unit of A^-1
    :param wavelength: wavelength in Angstrom

    :return: Klein-Nishina correction array for the given q-values
    """

    tth = 2 * np.arcsin(q * wavelength / (4 * np.pi))

    def P(wavelength, tth):
        return 1 / (
            1
            + (const.h / (wavelength * 1e-10 * const.m_e * const.c)) * (1 - np.cos(tth))
        )

    def KN_correction(p_values, tth):
        return (p_values**3 - p_values**2 * np.sin(tth) ** 2 + p_values) / (
            1 + np.cos(tth) ** 2
        )

    return KN_correction(P(wavelength, tth), tth)


def calculate_weighting_factor(
    composition: Composition,
    element_1: str,
    element_2: str,
    q: np.ndarray,
    sf_source="hajdu",
):
    """
    Calculates the weighting factor for an element-element contribution in a given composition (e.g. for Si-O in SiO2)

    :param composition: dictionary with elements as key string and abundances as relative numbers
    :param element_1: string giving element 1
    :param element_2: string giving element 2
    :param q: Q value or numpy array with a unit of A^-1
    :param sf_source: source of the scattering factors. Possible sources are 'hajdu' and 'brown_hubbell'.

    :return: weighting factor array
    """
    if element_1 == element_2:
        factor = 1
    else:
        factor = 2

    num_atoms = sum([val for _, val in composition.items()])
    f = {}  # form factors
    c = {}  # concentrations
    for element, val in composition.items():
        f[element] = calculate_coherent_scattering_factor(element, q, sf_source)
        c[element] = val / num_atoms

    f_sum_squared = np.zeros_like(q)
    for element, conc in c.items():
        f_sum_squared += f[element] * conc
    f_sum_squared = f_sum_squared**2

    return (
        factor
        * c[element_1]
        * c[element_2]
        * f[element_1]
        * f[element_2]
        / f_sum_squared
    )


def normalize_composition(composition: Composition) -> dict[str, float]:
    """
    normalizes elemental abundances to 1

    :param composition: dictionary with elements as key and abundances as relative numbers
    :return: normalized elemental abundances dictionary
    """
    sum = 0.0
    for key, val in composition.items():
        sum += val

    result = copy(composition)

    for key in result:
        result[key] /= sum

    return result


def convert_density_to_atoms_per_cubic_angstrom(
    composition: Composition, density: float
) -> float:
    """
    Converts densities given in g/cm3 into atoms per A^3

    :param composition: dictionary with elements as key and abundances as relative numbers
    :param density: density in g/cm^3
    :return: density in atoms/A^3
    """

    # get_smallest abundance
    norm_elemental_abundances = normalize_composition(composition)
    mean_z = 0.0
    for element, concentration in norm_elemental_abundances.items():
        element = re.findall("[A-zA-Z]*", element)[0]
        mean_z += concentration * scattering_factors.atomic_weights["AW"][element]
    return density / mean_z * 0.602214129


def convert_density_to_grams_per_cubic_centimeter(
    composition: Composition, atomic_density: float
) -> float:
    """
    Converts densities given in atoms/A^3 into g/cm3

    :param composition: dictionary with elements as key and abundances as relative numbers
    :param atomic_density: density in atoms/A^3
    :return: density in g/cm^3
    """

    # get_smallest abundance
    norm_elemental_abundances = normalize_composition(composition)
    mean_z = 0.0
    for element, concentration in norm_elemental_abundances.items():
        element = re.findall("[A-zA-Z]*", element)[0]
        mean_z += concentration * scattering_factors.atomic_weights["AW"][element]
    return atomic_density * mean_z / 0.602214129


def extrapolate_to_zero_step(pattern: Pattern, y0: float = 0) -> Pattern:
    """
    Extrapolates a pattern to (0, y0) by setting everything below the q_min of the pattern to y0 (default=0)

    :param pattern: input Pattern
    :param y0: y value at x = 0

    :return: extrapolated Pattern
    """
    x, y = pattern.data
    step = x[1] - x[0]
    low_x = np.arange(min(x), 0 - step / 2, -step)[::-1]
    low_y = np.zeros(low_x.shape) + y0

    return Pattern(np.concatenate((low_x, x)), np.concatenate((low_y, y)))


def extrapolate_to_zero_linear(pattern: Pattern, y0: float = 0) -> Pattern:
    """
    Extrapolates a pattern to (0, y0) using a linear function from the leftest point in the pattern

    :param pattern: input Pattern
    :param y0: y value at x = 0

    :return: new extrapolated Pattern (includes the original data)
    """
    x, y = pattern.data
    step = x[1] - x[0]
    low_x = np.arange(min(x), 0 - step / 2, -step)[::-1]
    low_y = (y[0] - y0) / x[0] * low_x + y0
    return Pattern(np.concatenate((low_x, x)), np.concatenate((low_y, y)))


def extrapolate_to_zero_spline(
    pattern: Pattern,
    x_max: float,
    smooth_factor: Optional[float] = None,
    replace: bool = False,
    y0: float = 0,
) -> Pattern:
    """
    Extrapolates a pattern to (0, y0) using a spline function.
    If the spline hits zero on the y-axis at an x value higher than 0 all values below this intersection
    will be set to zero

    :param pattern: input pattern
    :param x_max: defines the maximum x value within the spline will be fitted to the input pattern.
        this parameter should be larger than the minimum of the pattern x
    :param smooth_factor: defines the smoothing of the spline extrapolation please see numpy.UnivariateSpline manual for
        explanations
    :param replace: boolean flag whether to replace the data values in the fitted region (default = False)
    :param y0: y value at x = 0

    :return: extrapolated Pattern (includes the original one)
    """

    x, y = pattern.data
    x_step = x[1] - x[0]
    x_low = np.arange(min(x), 0 - x_step / 2, -x_step)[::-1]

    x_overlap_ind = np.where(x < x_max)[0]

    x_intersection = np.concatenate(([0], x[x_overlap_ind]))
    y_intersection = np.concatenate(([y0], y[x_overlap_ind]))

    if replace:
        x_low = np.concatenate((x_low, x_intersection[1:]))
        ind = x > x_max
        x = x[ind]
        y = y[ind]

    spl = interpolate.UnivariateSpline(x_intersection, y_intersection, s=smooth_factor)
    y_low = spl(x_low)

    if type(y_low) is not np.ndarray:
        raise ValueError("Spline extrapolation failed")

    ind_below_zero = np.where(y_low < y0)[0]

    if len(ind_below_zero) > 0:
        y_low[: ind_below_zero[-1]] = y0

    return Pattern(np.concatenate((x_low, x)), np.concatenate((y_low, y)))


def extrapolate_to_zero_poly(
    pattern: Pattern, x_max: float, replace: bool = False, y0: float = 0
) -> Pattern:
    """
    Extrapolates a pattern to (0, y0) using a 2nd order polynomial:

    .. math::
        y = a*(x-c)+b*(x-c)^2 + y0


    if the polynomial extrapolation hits the value of y0 (default=0) at an x value higher than zero all y values below
    this intersection will be set to y0.

    :param pattern: input pattern
    :param x_max: defines the maximum x value within the polynomial will be fit
    :param replace: boolean flag whether to replace the data values in the fitted region (default = False)
    :param y0: y value at x = 0

    :return: extrapolated Pattern
    """

    x, y = pattern.data
    x_step = x[1] - x[0]

    x_fit = x[x < x_max]
    y_fit = y[x < x_max]

    params = lmfit.Parameters()
    params.add("a", value=1, min=0)
    params.add("b", value=1, min=0)
    params.add("c", value=1)

    def optimization_fcn(params):
        a = params["a"].value
        b = params["b"].value
        c = params["c"].value

        return y_fit - (x_fit - c) * a - (x_fit - c) ** 2 * b + y0

    result = lmfit.minimize(optimization_fcn, params)
    if not hasattr(result, "params") or result.params is None:
        raise ValueError("Polynomial extrapolation failed")

    a = result.params["a"].value
    b = result.params["b"].value
    c = result.params["c"].value

    x_low = np.arange(min(x), 0, -x_step)[::-1]

    if replace:
        x_low = np.concatenate((x_low, x_fit[1:]))
        ind = x > x_max
        x = x[ind]
        y = y[ind]

    y_low = a * (x_low - c) + b * (x_low - c) ** 2 - y0
    y_low[y_low < y0] = y0

    return Pattern(np.concatenate((x_low, x)), np.concatenate((y_low, y)))


def convert_two_theta_to_q_space_raw(
    two_theta: Union[float, np.ndarray], wavelength: float
) -> Union[float, np.ndarray]:
    """
    Converts two theta values into q space
    """
    return 4 * np.pi * np.sin(two_theta / 360.0 * np.pi) / wavelength


def convert_two_theta_to_q_space(pattern: Pattern, wavelength: float) -> Pattern:
    """
    Returns a new pattern with the x-axis converted from two theta into q space
    """
    q_pattern = copy(pattern)
    q_pattern.x = convert_two_theta_to_q_space_raw(q_pattern.x, wavelength)
    return q_pattern
