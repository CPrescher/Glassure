"""Explicit Rust backend for Glassure, backed by the bundled Rust extension.

Inputs are copied as binary f64 buffers before releasing the GIL. Rust output
allocations become NumPy arrays directly. No JSON or Python lists of floats.
"""
from __future__ import annotations

from functools import lru_cache
import os
import numpy as np
from ._glassure_numpy import Engine
from glassure.configuration import Result, FitNormalization
from glassure.pattern import Pattern
from . import _glassure_numpy as _native
from ._optional import import_legacy


def _collect(report, configs, *, return_exceptions=False):
    values = []
    for i, item in enumerate(report["items"]):
        if item["status"] == "error":
            error = ValueError(f"Job {i}: {item['error']}")
            if not return_exceptions:
                raise error
            values.append(error)
        else:
            output = item["output"]
            result = output["result"]
            if output["operation"] == "calculate":
                values.append(Result(calculation_config=configs[i].model_copy(deep=True),
                    **{key: Pattern(**result[key]) for key in ("sq", "fr", "gr")}))
            else:
                values.append(_fit_tuple(result))
    return values


def _fit_tuple(value):
    return (value["density"], value["density_error"], value["background_scale"], value["background_error"])


@lru_cache(maxsize=4)
def _engine(threads):
    return Engine(threads)


def _request(data, config):
    t, n = config.transform, config.transform.normalization
    def pattern(p):
        return None if p is None else {"x": np.asarray(p.x, dtype=np.float64),
                                      "y": np.asarray(p.y, dtype=np.float64)}
    normalization = ({"method": "fit", "q_cutoff": n.q_cutoff, "scaling": n.method,
                      "multiple": n.multiple_scattering, "container": n.container_scattering,
                      "dac": n.dac.model_dump() if n.dac else None}
                     if isinstance(n, FitNormalization) else
                     {"method": "integral", "attenuation": n.attenuation_factor})
    opt = config.optimize
    return {"data": pattern(data.data), "background": pattern(data.bkg),
        "background_scale": data.bkg_scaling, "composition": config.sample.composition,
        "density": config.sample.density, "scattering_factor_source": t.scattering_factor_source, "q_min": t.q_min, "q_max": t.q_max,
        "r_min": t.r_min, "r_max": t.r_max, "r_step": t.r_step,
        "normalization": normalization, "incoherent": n.incoherent_scattering,
        "lorch": t.use_modification_fcn, "transform": t.fourier_transform_method,
        "extrapolation": t.extrapolation.method, "overlap": t.extrapolation.overlap,
        "replace": t.extrapolation.replace, "s0": t.extrapolation.s0,
        "kn_correction": t.kn_correction, "wavelength": t.wavelength,
        "optimize": None if opt is None else {"method": opt.method,
            "r_cutoff": opt.r_cutoff, "iterations": opt.iterations,
            "lorch": opt.use_modification_fcn}}


def calculate_pdf(data_config, calculation_config):
    """Calculate from NumPy inputs, returning ordinary Glassure Result/Patterns."""
    validate_input(data_config, calculation_config)
    value = _engine(1).calculate(_request(data_config, calculation_config))
    return Result(calculation_config=calculation_config.model_copy(deep=True),
                  **{name: Pattern(**value[name]) for name in ("sq", "fr", "gr")})


def calculate_batch(jobs, *, threads=0, return_exceptions=False):
    """Ordered independent PDFs with native multicore and per-item failures."""
    jobs = list(jobs)
    if len(jobs) > 1024:
        raise ValueError("Job count exceeds limit 1024")
    if not isinstance(threads, int) or threads < 0 or threads > 64:
        raise ValueError("Thread count must be 0..64")
    effective = min(threads or min(os.cpu_count() or 1, 64), max(1, len(jobs)))
    values = [_request(data, config) for data, config in jobs]
    report = _engine(effective).batch(values)
    return _collect(report, [config for _, config in jobs], return_exceptions=return_exceptions)


def _threads(threads, count):
    if not isinstance(threads, int) or not 0 <= threads <= 64:
        raise ValueError("Thread count must be 0..64")
    return min(threads or min(os.cpu_count() or 1, 64), max(1, count))


def _density_request(data, config, method="fr", min_range=None, vary_bkg_scaling=True,
                     bkg_limits=(.9, 1.1), optimization_method="lsq", max_evaluations=500):
    if config.optimize is None and min_range is None and method != "sq":
        raise ValueError(
            "For optimizing density using 'gr' or 'fr' the calculation configuration needs to have the "
            "optimize configuration or the min_range parameter needs to be set."
        )
    if method not in ("gr", "fr", "sq"):
        raise ValueError(f"Invalid optimize density method: {method}, only 'gr', 'fr' and 'sq' are supported.")
    if optimization_method not in ("lsq", "nelder", "brent", "brent_local"):
        raise ValueError(f"Invalid optimization method: {optimization_method}")
    return {"calculation": _request(data, config), "method": method, "min_range": min_range,
            "vary_background": vary_bkg_scaling, "background_limits": bkg_limits,
            "algorithm": optimization_method, "max_evaluations": max_evaluations}


def optimize_density(data_config, calculation_config, method="fr", min_range=None,
                     vary_bkg_scaling=True, bkg_limits=(.9, 1.1), optimization_method="lsq",
                     *, max_evaluations=500):
    """Refine using lsq/TRF, nelder, brent or brent_local.

    Brent minimizes the scalar squared-residual objective within the same density
    bounds; brent_local first brackets downhill from the supplied density. Both
    Brent options require vary_bkg_scaling=False and return conditional errors
    like lsq. The full-interval brent search assumes a unimodal objective within
    the bounds and may find a different minimum from the local TRF fit.
    """
    return _fit_tuple(_engine(1).density(_density_request(data_config, calculation_config,
        method, min_range, vary_bkg_scaling, bkg_limits, optimization_method, max_evaluations)))


def optimize_density_batch(jobs, *, threads=0, return_exceptions=False, **options):
    jobs = list(jobs)
    if len(jobs) > 1024:
        raise ValueError("Job count exceeds limit 1024")
    values = [{"operation": "density", "request": _density_request(data, config, **options)} for data, config in jobs]
    report = _engine(_threads(threads, len(jobs))).jobs(values)
    return _collect(report, [config for _, config in jobs], return_exceptions=return_exceptions)


def _sweep(data, config, points, operation, threads, return_exceptions, options):
    points = list(points)
    if len(points) > 1024:
        raise ValueError("Job count exceeds limit 1024")
    request = _request(data, config) if operation == "calculate" else _density_request(data, config, **options)
    report = _engine(_threads(threads, len(points))).sweep({"operation": operation, "request": request}, points)
    configs = []
    for point in points:
        c = config.model_copy(deep=True)
        if point.get("density") is not None:
            c.sample.density = point["density"]
        if point.get("q_max") is not None:
            c.transform.q_max = point["q_max"]
        if point.get("r_cutoff") is not None and c.optimize is not None:
            c.optimize.r_cutoff = point["r_cutoff"]
        configs.append(c)
    return _collect(report, configs, return_exceptions=return_exceptions)


def parameter_sweep(data_config, calculation_config, points, *, threads=0, return_exceptions=False):
    return _sweep(data_config, calculation_config, points, "calculate", threads, return_exceptions, {})


def optimize_density_sweep(data_config, calculation_config, points, *, threads=0, return_exceptions=False, **options):
    return _sweep(data_config, calculation_config, points, "density", threads, return_exceptions, options)


def _array(values):
    return np.atleast_1d(np.asarray(values, dtype=np.float64))


def _pattern(value):
    return {"x": _array(value.x), "y": _array(value.y)}


def _op(name, **values):
    return _native.run(name, values)["value"]


def parse_str_to_composition(formula):
    # Preserve the legacy Python spelling of escaped grouping braces.
    return _op("composition", composition=formula.replace(r"\{", "{").replace(r"\}", "}"))


def normalize_composition(composition):
    return _op("fractions", composition=composition)


def get_available_elements(source="hajdu"):
    return _op("elements", source=source)


def calculate_coherent_scattering_factor(element, q, source="hajdu"):
    return _op("coherent", element=element, q=_array(q), source=source)


def calculate_incoherent_scattered_intensity(element, q, source="hajdu"):
    return _op("incoherent", element=element, q=_array(q), source=source)


def calculate_f_mean_squared(composition, q, sf_source="hajdu"):
    return _op("fm2", composition=composition, q=_array(q), source=sf_source)


def calculate_f_squared_mean(composition, q, sf_source="hajdu"):
    return _op("f2", composition=composition, q=_array(q), source=sf_source)


def calculate_incoherent_scattering(composition, q, sf_source="hajdu"):
    return _op("incoherent_mean", composition=composition, q=_array(q), source=sf_source)


def calculate_s0(composition, sf_source="hajdu"):
    return _op("s0", composition=composition, q=_array(0.), source=sf_source)


def convert_density_to_atoms_per_cubic_angstrom(composition, density):
    return _op("atomic_density", composition=composition, density=density)


def convert_density_to_grams_per_cubic_centimeter(composition, atomic_density):
    return _op("mass_density", composition=composition, density=atomic_density)


def calculate_total_atomic_number(composition):
    return _op("ztotal", composition=composition)


def calculate_effective_form_factor(composition, q, sf_source="hajdu"):
    return _op("effective", composition=composition, q=_array(q), source=sf_source)


def calculate_wkm_effective_atomic_number(composition, element, q, sf_source="hajdu"):
    return _op("keff", composition=composition, element=element, q=_array(q), source=sf_source)


def calculate_weighting_factor(composition, element_1, element_2, q, sf_source="hajdu"):
    return _op("weight", composition=composition, element_1=element_1, element_2=element_2, q=_array(q), source=sf_source)


def calculate_weighting_factor_wkm(composition, element_1, element_2, q=0., sf_source="hajdu"):
    return _op("wkm", composition=composition, element_1=element_1, element_2=element_2, q=_array(q), source=sf_source)


def calculate_kn_correction(q, wavelength):
    return _op("kn", q=_array(q), wavelength=wavelength)


def convert_two_theta_to_q_space_raw(two_theta, wavelength):
    return _op("two_theta", q=_array(two_theta), wavelength=wavelength)


def convert_two_theta_to_q_space(pattern, wavelength):
    return Pattern(convert_two_theta_to_q_space_raw(pattern.x, wavelength), pattern.y)


def calculate_sq(normalized_pattern, f_squared_mean, f_mean_squared):
    return Pattern(**_op("sq", pattern=_pattern(normalized_pattern), f2=_array(f_squared_mean), fm2=_array(f_mean_squared)))


def calculate_fr(sq_pattern, r=None, use_modification_fcn=False, method="integral"):
    if r is None:
        r = np.arange(0., 10.005, .01)
        r[0] = 1e-10
    return Pattern(**_op("fr", pattern=_pattern(sq_pattern), grid=_array(r), method=method, lorch=use_modification_fcn))


def calculate_sq_from_fr(fr_pattern, q=None, method="integral", use_modification_fcn=False):
    if q is None:
        q = np.arange(0., 25.005, .05)
        q[0] = 1e-10
    return Pattern(**_op("sq_from_fr", pattern=_pattern(fr_pattern), grid=_array(q), method=method, lorch=use_modification_fcn))


def calculate_sq_from_gr(gr_pattern, q, atomic_density, method="integral"):
    return Pattern(**_op("sq_from_gr", pattern=_pattern(gr_pattern), grid=_array(q), density=atomic_density, method=method, lorch=False))


def calculate_gr(fr_pattern, atomic_density):
    return Pattern(**_op("gr", pattern=_pattern(fr_pattern), density=atomic_density))


def calculate_rdf(gr_pattern, atomic_density):
    return Pattern(**_op("rdf", pattern=_pattern(gr_pattern), density=atomic_density))


def calculate_tr(gr_pattern, atomic_density):
    return Pattern(**_op("tr", pattern=_pattern(gr_pattern), density=atomic_density))


def normalize(sample_pattern, atomic_density, f_squared_mean, f_mean_squared,
              incoherent_scattering=None, attenuation_factor=.001):
    n, p = _op("normalize", pattern=_pattern(sample_pattern), density=atomic_density,
        f2=_array(f_squared_mean), fm2=_array(f_mean_squared),
        incoherent=None if incoherent_scattering is None else _array(incoherent_scattering), attenuation=attenuation_factor)
    return n, Pattern(**p)


def normalize_fit(sample_pattern, f_squared_mean, incoherent_scattering=None, q_cutoff=3.,
                  method="squared", multiple_scattering=False, container_scattering=None):
    if method not in ("squared", "linear"):
        raise NotImplementedError(f"{method} is not a valid method")
    params, p = _op("normalize_fit", pattern=_pattern(sample_pattern), f2=_array(f_squared_mean),
        incoherent=None if incoherent_scattering is None else _array(incoherent_scattering),
        container=None if container_scattering is None else _array(container_scattering),
        cutoff=q_cutoff, scaling=method, multiple=multiple_scattering)
    return params, Pattern(**p)


def normalize_fit_lmfit(sample_pattern, f_squared_mean, incoherent_scattering=None, q_cutoff=3.,
                        method="squared", multiple_scattering=False, container_scattering=None):
    if method not in ("squared", "linear"):
        raise NotImplementedError(f"{method} is not an allowed method")
    Parameters = import_legacy("lmfit").Parameters
    values, pattern = _op("normalize_fit_lmfit", pattern=_pattern(sample_pattern), f2=_array(f_squared_mean),
        incoherent=None if incoherent_scattering is None else _array(incoherent_scattering),
        container=None if container_scattering is None else _array(container_scattering),
        cutoff=q_cutoff, scaling=method, multiple=multiple_scattering)
    params = Parameters()
    params.add("n", value=values["n"], min=0)
    params.add("multiple", value=values["multiple"], min=0, vary=multiple_scattering)
    params.add("n_container", value=values["n_container"], min=0, vary=container_scattering is not None)
    return params, Pattern(**pattern)


def _extrapolate(pattern, method, y0, x_max=0., replace=False, smooth_factor=None):
    return Pattern(**_op("extrapolate", pattern=_pattern(pattern), method=method, y0=y0,
        x_max=x_max, replace=replace, smoothing=smooth_factor))


def extrapolate_to_zero_step(pattern, y0=0.):
    return _extrapolate(pattern, "step", y0)


def extrapolate_to_zero_linear(pattern, y0=0.):
    return _extrapolate(pattern, "linear", y0)


def extrapolate_to_zero_spline(pattern, x_max, smooth_factor=None, replace=False, y0=0.):
    return _extrapolate(pattern, "spline", y0, x_max, replace, smooth_factor)


def extrapolate_to_zero_poly(pattern, x_max, replace=False, y0=0.):
    return _extrapolate(pattern, "poly", y0, x_max, replace)


def fit_polynom_through_origin(x, y, degree):
    return _op("polynomial", x=_array(x), y=_array(y), degree=degree)


def optimize_sq(sq_pattern, r_cutoff, iterations, atomic_density, r_step=.01,
                use_modification_fcn=False, attenuation_factor=1, fcn_callback=None,
                callback_period=2, fourier_transform_method="fft"):
    if fcn_callback is not None:
        if callback_period < 1:
            raise ValueError("callback_period must be positive")
        result = sq_pattern
        for iteration in range(iterations):
            result = optimize_sq(result, r_cutoff, 1, atomic_density, r_step,
                use_modification_fcn, attenuation_factor, fourier_transform_method=fourier_transform_method)
            if iteration % callback_period == 0:
                fr = calculate_fr(result, use_modification_fcn=use_modification_fcn, method=fourier_transform_method)
                fcn_callback(result, fr, calculate_gr(fr, atomic_density))
        return result
    return Pattern(**_op("optimize_sq", pattern=_pattern(sq_pattern), density=atomic_density,
        r_cutoff=r_cutoff, iterations=iterations, lorch=use_modification_fcn, method=fourier_transform_method,
        r_step=r_step, attenuation=attenuation_factor, optimization="iterative"))


def optimize_sq_fit(sq_pattern, r_cutoff):
    return Pattern(**_op("optimize_sq", pattern=_pattern(sq_pattern), density=1., r_cutoff=r_cutoff,
        iterations=0, lorch=False, method="fft", r_step=.01, attenuation=1., optimization="fit"))


def _peak(name, q, n, position, sigma, composition, element_1, element_2, **options):
    return _op(name, q=_array(q), n=n, position=position, sigma=sigma,
        composition=composition, element_1=element_1, element_2=element_2, source="hajdu", **options)


def i_q_peak(q, n, position, sigma, composition, element_1, element_2):
    return _peak("iq_peak", q, n, position, sigma, composition, element_1, element_2)


def t_r_peak(r, n, position, sigma, composition, element_1, element_2, q, use_modification_fcn=False, method="fft"):
    return _peak("tr_peak", q, n, position, sigma, composition, element_1, element_2,
        r=_array(r), lorch=use_modification_fcn, method=method)


def t_r_peak_gaussian(r, n, position, sigma, composition, element_1, element_2, q=0.):
    return _peak("gaussian", q, n, position, sigma, composition, element_1, element_2, r=_array(r))


class _TransferFunction:
    def __init__(self, standard, sample, smoothing):
        self._native = _native.TransferFunction(_pattern(standard), _pattern(sample), smoothing)

    def __call__(self, x):
        value = self._native(_array(x))
        return value[0] if np.ndim(x) == 0 else value


def calculate_transfer_function(std_pattern, sample_pattern, smooth_factor=1.):
    return _TransferFunction(std_pattern, sample_pattern, smooth_factor)


class SollerCorrection:
    def __init__(self, two_theta, max_thickness, inner_radius=62., outer_radius=210.,
                 inner_width=.05, outer_width=.2, inner_length=8., outer_length=6.):
        from types import SimpleNamespace
        self._native = _native.Soller(_array(two_theta), max_thickness, dict(
            inner_radius=inner_radius, outer_radius=outer_radius, inner_width=inner_width,
            outer_width=outer_width, inner_length=inner_length, outer_length=outer_length))
        data = self._native.map()
        x, y = np.meshgrid(data["two_theta"], data["distance"])
        self.dispersion_angle_map = SimpleNamespace(X=x, Y=y, data=data["angles"].reshape(x.shape))

    def calculate_dispersion_angle_map(self):
        return self.dispersion_angle_map

    def transfer_function_from_region(self, d1, d2):
        return self._native.region(d1, d2)

    def transfer_function_sample(self, sample_thickness, shift=0.):
        return self._native.sample(sample_thickness, shift)

    def transfer_function_dac(self, sample_thickness, initial_thickness):
        return self._native.dac(sample_thickness, initial_thickness)


class SollerCorrectionGui(SollerCorrection):
    def __init__(self, q, wavelength, max_thickness, **geometry):
        self.q, self.wavelength = _array(q), wavelength
        # This is input-coordinate preparation; the geometry/acceptance is native.
        two_theta = np.arcsin(self.q * wavelength / (4 * np.pi)) * 360 / np.pi
        super().__init__(two_theta, max_thickness, **geometry)


def vector_length(vec):
    return _op("vector_length", x=_array(vec).ravel())


def smooth(pattern, amount):
    return Pattern(**_op("smooth", pattern=_pattern(pattern), amount=amount))


def rebin(pattern, bin_size):
    return Pattern(**_op("rebin", pattern=_pattern(pattern), amount=bin_size))


def calculate_angles(point1, point2, p):
    p = np.asarray(p, dtype=float)
    value = _op("angles", point1=point1, point2=point2, x=_array(p[0]), y=_array(p[1]))
    return value[0] if p.ndim == 1 else value


def calculate_x_axis_intercept(p1, p2):
    return _op("x_intercept", point1=p1, point2=p2)


def calculate_y_axis_intercept(p1, p2):
    return _op("y_intercept", point1=p1, point2=p2)


def calculate_rectangular_side_points(radius, angle, width):
    a, b = _op("side_points", radius=radius, angle=angle, width=width)
    return np.array(a), np.array(b)


class ScatteringFactorCalculator:
    source = None

    @property
    def elements(self):
        return get_available_elements(self.source)

    def get_coherent_scattering_factor(self, element, q):
        return calculate_coherent_scattering_factor(element, q, self.source)

    def get_incoherent_intensity(self, element, q):
        return calculate_incoherent_scattered_intensity(element, q, self.source)


class ScatteringFactorCalculatorHajdu(ScatteringFactorCalculator):
    source = "hajdu"


class ScatteringFactorCalculatorBrownHubbell(ScatteringFactorCalculator):
    source = "brown_hubbell"


class ScatteringFactorCalculatorXraylib(ScatteringFactorCalculator):
    source = "xraylib"


def get_calculator(source):
    return {"hajdu": ScatteringFactorCalculatorHajdu, "brown_hubbell": ScatteringFactorCalculatorBrownHubbell,
            "xraylib": ScatteringFactorCalculatorXraylib}[source]()


def create_calculate_pdf_configs(data, composition, density, bkg=None, bkg_scaling=1.):
    # Configuration construction is shared with the existing Python API.
    from .calc import create_calculate_pdf_configs as create
    return create(data, composition, density, bkg, bkg_scaling)


def validate_input(data_config, calculation_config):
    from .calc import validate_input as validate
    return validate(data_config, calculation_config)


__all__ = ['calculate_pdf',
 'calculate_batch',
 'optimize_density',
 'optimize_density_batch',
 'parameter_sweep',
 'optimize_density_sweep',
 'parse_str_to_composition',
 'normalize_composition',
 'get_available_elements',
 'calculate_coherent_scattering_factor',
 'calculate_incoherent_scattered_intensity',
 'calculate_f_mean_squared',
 'calculate_f_squared_mean',
 'calculate_incoherent_scattering',
 'calculate_s0',
 'convert_density_to_atoms_per_cubic_angstrom',
 'convert_density_to_grams_per_cubic_centimeter',
 'calculate_total_atomic_number',
 'calculate_effective_form_factor',
 'calculate_wkm_effective_atomic_number',
 'calculate_weighting_factor',
 'calculate_weighting_factor_wkm',
 'calculate_kn_correction',
 'convert_two_theta_to_q_space_raw',
 'convert_two_theta_to_q_space',
 'calculate_sq',
 'calculate_fr',
 'calculate_sq_from_fr',
 'calculate_sq_from_gr',
 'calculate_gr',
 'calculate_rdf',
 'calculate_tr',
 'normalize',
 'normalize_fit',
 'normalize_fit_lmfit',
 'extrapolate_to_zero_step',
 'extrapolate_to_zero_linear',
 'extrapolate_to_zero_spline',
 'extrapolate_to_zero_poly',
 'fit_polynom_through_origin',
 'optimize_sq',
 'optimize_sq_fit',
 'i_q_peak',
 't_r_peak',
 't_r_peak_gaussian',
 'calculate_transfer_function',
 'SollerCorrection',
 'SollerCorrectionGui',
 'vector_length',
 'smooth',
 'rebin',
 'calculate_angles',
 'calculate_x_axis_intercept',
 'calculate_y_axis_intercept',
 'calculate_rectangular_side_points',
 'ScatteringFactorCalculator',
 'ScatteringFactorCalculatorHajdu',
 'ScatteringFactorCalculatorBrownHubbell',
 'ScatteringFactorCalculatorXraylib',
 'get_calculator',
 'create_calculate_pdf_configs',
 'validate_input',
 'Pattern']
