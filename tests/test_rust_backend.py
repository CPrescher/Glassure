"""Optional backend contract: compare Rust scientific APIs with the Python reference."""
import copy
import re
import numpy as np
import pytest

native = pytest.importorskip("glassure._glassure_numpy", reason="Build the bundled extension wheel")
if not hasattr(native, "run"):
    pytest.skip("Installed prototype predates the standalone backend", allow_module_level=True)
from glassure import rust, Pattern
from glassure import utility, transform, normalization, optimization, fitting, scattering_factors, soller_correction
from glassure.configuration import DataConfig, CalculationConfig
from glassure import use_backend


@pytest.fixture(autouse=True)
def python_reference(glassure_backend):
    # Expected values must remain independent of the native code under test.
    with use_backend("python"):
        yield


def close(a, b, tolerance=1e-8):
    if isinstance(a, Pattern):
        np.testing.assert_allclose(a.x, b.x, atol=tolerance, rtol=tolerance)
        np.testing.assert_allclose(a.y, b.y, atol=tolerance, rtol=tolerance)
    else:
        np.testing.assert_allclose(a, b, atol=tolerance, rtol=tolerance)


SPECIES = []
for source in ("hajdu", "brown_hubbell", "xraylib"):
    calc = scattering_factors.get_calculator(source)
    for element in list(calc.elements)[:98] if source == "xraylib" else calc.elements:
        if source == "brown_hubbell" and re.match("[A-Za-z]+", element)[0] not in calc.incoherent_intensities:
            continue
        SPECIES.append((source, str(element)))


@pytest.mark.parametrize("source,element", SPECIES)
def test_all_scattering_sources(source, element):
    q = np.linspace(0., 12., 91)
    close(rust.calculate_coherent_scattering_factor(element, q, source),
          scattering_factors.calculate_coherent_scattering_factor(element, q, source), 1e-11)
    close(rust.calculate_incoherent_scattered_intensity(element, q, source),
          scattering_factors.calculate_incoherent_scattered_intensity(element, q, source), 1e-11)


@pytest.mark.parametrize("source", ["hajdu", "brown_hubbell", "xraylib"])
def test_mixture_density_and_weights(source):
    c = {"Mg": 2, "Si": 1, "O": 4}
    q = np.linspace(0., 20., 200)
    for name in ("calculate_f_mean_squared", "calculate_f_squared_mean", "calculate_incoherent_scattering",
                 "calculate_effective_form_factor"):
        close(getattr(rust, name)(c, q, source), getattr(utility, name)(c, q, source))
    close(rust.calculate_s0(c, source), utility.calculate_s0(c, source))
    close(rust.calculate_wkm_effective_atomic_number(c, "Si", q, source),
          utility.calculate_wkm_effective_atomic_number(c, "Si", q, source))
    for a, b in (("Si", "O"), ("Mg", "Mg")):
        close(rust.calculate_weighting_factor(c, a, b, q, source), utility.calculate_weighting_factor(c, a, b, q, source))
        close(rust.calculate_weighting_factor_wkm(c, a, b, q, source), utility.calculate_weighting_factor_wkm(c, a, b, q, source))
    rho = rust.convert_density_to_atoms_per_cubic_angstrom(c, 2.9)
    close(rho, utility.convert_density_to_atoms_per_cubic_angstrom(c, 2.9))
    close(rust.convert_density_to_grams_per_cubic_centimeter(c, rho), 2.9)
    close(rust.calculate_total_atomic_number(c), utility.calculate_total_atomic_number(c))


@pytest.mark.parametrize("method", ["integral", "fft"])
@pytest.mark.parametrize("lorch", [False, True])
def test_standalone_transforms(method, lorch):
    q = np.linspace(.02, 20., 501)
    r = np.linspace(1e-10, 6., 601)
    sq = Pattern(q, 1 + .3 * np.sin(q * 1.6) * np.exp(-q / 10))
    a = rust.calculate_fr(sq, r, lorch, method)
    b = transform.calculate_fr(sq, r, lorch, method)
    close(a, b)
    close(rust.calculate_sq_from_fr(a, q, method, lorch), transform.calculate_sq_from_fr(b, q, method, lorch))
    gr = rust.calculate_gr(a, .066)
    close(gr, transform.calculate_gr(b, .066))
    close(rust.calculate_rdf(gr, .066), transform.calculate_rdf(gr, .066))
    close(rust.calculate_tr(gr, .066), transform.calculate_tr(gr, .066))
    # Python calculate_sq_from_gr currently ignores its method argument. Check
    # the requested Rust method against the explicitly equivalent reference.
    expected = transform.calculate_sq_from_fr(Pattern(r, (gr.y - 1) * 4 * np.pi * r * .066), q, method)
    close(rust.calculate_sq_from_gr(gr, q, .066, method), expected)


@pytest.mark.parametrize("multiple,container", [(False, False), (True, False), (False, True), (True, True)])
@pytest.mark.parametrize("scaling", ["linear", "squared"])
def test_normalization(multiple, container, scaling):
    q = np.linspace(.05, 20, 501)
    f2 = rust.calculate_f_squared_mean({"Si": 1, "O": 2}, q)
    fm2 = rust.calculate_f_mean_squared({"Si": 1, "O": 2}, q)
    inc = rust.calculate_incoherent_scattering({"Si": 1, "O": 2}, q)
    cont = rust.calculate_incoherent_scattering({"C": 1}, q) if container else None
    data = Pattern(q, (f2 + inc + (cont * .3 if container else 0) + (3 if multiple else 0)) / 2.3)
    a, b = rust.normalize_fit(data, f2, inc.copy(), method=scaling, multiple_scattering=multiple, container_scattering=cont), normalization.normalize_fit(data, f2, inc.copy(), method=scaling, multiple_scattering=multiple, container_scattering=cont)
    for key in ("n", "multiple", "n_container", "residual"):
        close(a[0][key], b[0][key])
    close(a[1], b[1])
    a, b = rust.normalize(data, .066, f2, fm2, inc), normalization.normalize(data, .066, f2, fm2, inc)
    close(a[0], b[0]); close(a[1], b[1])
    close(rust.calculate_sq(a[1], f2, fm2), transform.calculate_sq(b[1], f2, fm2))
    a, b = rust.normalize_fit_lmfit(data, f2, inc.copy(), method=scaling, multiple_scattering=multiple, container_scattering=cont), normalization.normalize_fit_lmfit(data, f2, inc.copy(), method=scaling, multiple_scattering=multiple, container_scattering=cont)
    close(a[1], b[1], 1e-5)


@pytest.mark.parametrize("name", ["step", "linear", "spline", "poly"])
@pytest.mark.parametrize("replace", [False, True])
def test_extrapolation(name, replace):
    x = np.linspace(.5, 10., 501)
    p = Pattern(x, 1 - np.exp(-x))
    fn = "extrapolate_to_zero_" + name
    options = {} if name in ("step", "linear") else {"x_max": 1.2, "replace": replace}
    close(getattr(rust, fn)(p, **options), getattr(utility, fn)(p, **options), 1e-6 if name == "poly" else 1e-8)


@pytest.mark.parametrize("method", ["fft", "integral"])
def test_optimization_and_callback(method):
    q = np.linspace(.02, 20, 501)
    p = Pattern(q, 1 + .3 * np.sin(q * 1.6) * np.exp(-q / 10))
    options = dict(r_cutoff=1.2, iterations=3, atomic_density=.066, fourier_transform_method=method)
    close(rust.optimize_sq(p, **options), optimization.optimize_sq(p, **options))
    calls = []
    close(rust.optimize_sq(p, **options, fcn_callback=lambda *args: calls.append(args)), optimization.optimize_sq(p, **options))
    assert len(calls) == 2
    close(rust.optimize_sq_fit(p, 1.2), optimization.optimize_sq_fit(p, 1.2))
    close(rust.fit_polynom_through_origin(q, q**2 - 3*q, 2), optimization.fit_polynom_through_origin(q, q**2 - 3*q, 2))


def test_peaks_transfer_and_smoothing():
    from glassure.transfer_function import calculate_transfer_function
    c = {"Mg": 2, "Si": 1, "O": 4}
    q, r = np.linspace(.01, 20, 1001), np.linspace(.01, 8, 1001)
    close(rust.i_q_peak(q, 4., 1.6, .15, c, "Si", "O"), fitting.i_q_peak(q, 4., 1.6, .15, c, "Si", "O"))
    close(rust.t_r_peak(r, 4., 1.6, .15, c, "Si", "O", q), fitting.t_r_peak(r, 4., 1.6, .15, c, "Si", "O", q))
    close(rust.t_r_peak_gaussian(r, 4., 1.6, .15, c, "Si", "O", q), fitting.t_r_peak_gaussian(r, 4., 1.6, .15, c, "Si", "O", q))
    sample, standard = Pattern(q, 2 + np.cos(q)), Pattern(q, (2 + np.cos(q)) * (1 + q / 100))
    close(rust.calculate_transfer_function(standard, sample)(q), calculate_transfer_function(standard, sample)(q), 1e-7)
    close(rust.smooth(sample, 2.), sample.smooth(2.))
    close(rust.rebin(sample, .2), sample.rebin(.2))


@pytest.mark.parametrize("geometry", [{}, {"inner_radius": 70., "outer_radius": 220., "inner_width": .1, "outer_width": .25}])
def test_general_soller(geometry):
    q = np.linspace(1., 40., 80)
    a, b = rust.SollerCorrection(q, .3, **geometry), soller_correction.SollerCorrection(q, .3, **geometry)
    close(a.dispersion_angle_map.data, b.dispersion_angle_map.data, 1e-8)
    close(a.transfer_function_sample(.05, .01), b.transfer_function_sample(.05, .01))
    for x, y in zip(a.transfer_function_dac(.04, .1), b.transfer_function_dac(.04, .1)):
        close(x, y)
    close(rust.calculate_angles([0, 1], [1, 0], [np.linspace(-.5, .5), np.zeros(50)]), soller_correction.calculate_angles([0, 1], [1, 0], [np.linspace(-.5, .5), np.zeros(50)]))


def test_density_and_sweeps_preserve_inputs():
    from glassure.calc import create_calculate_pdf_configs
    from glassure.configuration import OptimizeConfig
    from pathlib import Path
    directory = Path(__file__).parent / "data"
    data, config = create_calculate_pdf_configs(Pattern.from_file(str(directory / "SiO2.xy")), "SiO2", 2.2,
        Pattern.from_file(str(directory / "SiO2_bkg.xy")))
    config.transform.q_min = 1.; config.transform.q_max = 17.
    config.optimize = OptimizeConfig(r_cutoff=1.2, iterations=3)
    before = copy.deepcopy(data), config.model_dump()
    options = dict(method="gr", min_range=(.1, 1.), vary_bkg_scaling=False)
    a, b = rust.optimize_density(data, config, **options), optimization.optimize_density(data, config, **options)
    close(a, b, 1e-5)
    points = [{"q_max": 15.}, {"q_max": 16.}, {"q_max": 17.}]
    serial = rust.optimize_density_sweep(data, config, points, threads=1, **options)
    parallel = rust.optimize_density_sweep(data, config, points, threads=4, **options)
    close(serial, parallel, 0)
    fits = rust.optimize_density_batch([(data, config)] * 2, threads=2, **options)
    close(fits[0], a, 0)
    for actual, point in zip(rust.parameter_sweep(data, config, points, threads=4), points):
        c = config.model_copy(deep=True); c.transform.q_max = point["q_max"]
        from glassure.calc import calculate_pdf
        close(actual.sq, calculate_pdf(data, c).sq)
    close(data.data.x, before[0].data.x, 0); close(data.data.y, before[0].data.y, 0)
    assert config.model_dump() == before[1]


@pytest.mark.parametrize("source", ["hajdu", "xraylib"])
@pytest.mark.parametrize("stem,formula,rho,qmax", [("SiO2", "SiO2", 2.2, 17.), ("Mg2SiO4_ambient", "Mg2SiO4", 2.9, 20.)])
def test_complete_pdf_with_alternate_source(source, stem, formula, rho, qmax):
    from pathlib import Path
    from glassure.calc import create_calculate_pdf_configs, calculate_pdf
    from glassure.configuration import OptimizeConfig, DACConfig
    directory = Path(__file__).parent / "data"
    data, config = create_calculate_pdf_configs(Pattern.from_file(str(directory / (stem + ".xy"))), formula, rho,
        Pattern.from_file(str(directory / (stem + "_bkg.xy"))))
    config.transform.q_min = 1.; config.transform.q_max = qmax
    config.transform.scattering_factor_source = source
    config.transform.normalization.multiple_scattering = True
    config.transform.normalization.container_scattering = {"C": 1}
    config.transform.normalization.dac = DACConfig(initial_thickness=40., sample_thickness=20.)
    config.transform.kn_correction = True; config.transform.wavelength = .29
    config.optimize = OptimizeConfig(r_cutoff=1.4, iterations=3)
    a, b = rust.calculate_pdf(data, config), calculate_pdf(data, config)
    for name in ("sq", "fr", "gr"):
        close(getattr(a, name), getattr(b, name))


@pytest.mark.parametrize("stem,formula,rho,qmax", [("SiO2", "SiO2", 2.2, 17.), ("Mg2SiO4_ambient", "Mg2SiO4", 2.9, 20.)])
@pytest.mark.parametrize("algorithm", ["lsq", "nelder"])
@pytest.mark.parametrize("objective", ["gr", "fr", "sq"])
@pytest.mark.parametrize("vary", [False, True])
def test_density_objective_algorithm_matrix(stem, formula, rho, qmax, algorithm, objective, vary, monkeypatch):
    from pathlib import Path
    from glassure.calc import create_calculate_pdf_configs
    from glassure.configuration import OptimizeConfig, IntNormalization
    directory = Path(__file__).parent / "data"
    data, config = create_calculate_pdf_configs(Pattern.from_file(str(directory / (stem + ".xy"))), formula, rho,
        Pattern.from_file(str(directory / (stem + "_bkg.xy"))))
    config.transform.q_min = 1.; config.transform.q_max = qmax; config.transform.r_min = 1e-13
    config.transform.normalization = IntNormalization()
    config.optimize = OptimizeConfig(r_cutoff=1.4, iterations=5)
    metadata = {}
    import lmfit
    minimize = lmfit.minimize
    def capture(*args, **kwargs):
        if kwargs.get("method") == "least_squares":
            # Independently approximate the Python Jacobian with central differences.
            # Two-point differences can cross the default gradient stopping threshold
            # at different iterates on Linux and macOS for shallow objectives.
            kwargs["jac"] = "3-point"
        result = minimize(*args, **kwargs)
        metadata["success"] = result.success
        return result
    monkeypatch.setattr(lmfit, "minimize", capture)
    options = dict(method=objective, min_range=(0., 2.) if objective == "sq" else (.1, 1.2),
                   vary_bkg_scaling=vary, optimization_method=algorithm)
    # The reference optimizer mutates DataConfig.bkg_scaling while evaluating.
    # Give it an independent input so both optimizers start at the same bounds.
    expected = optimization.optimize_density(copy.deepcopy(data), config, **options)
    if not metadata["success"]:
        with pytest.raises(ValueError, match="evaluation_budget"):
            rust.optimize_density(data, config, **options)
        return
    actual = rust.optimize_density(data, config, **options)
    for i, (a, b) in enumerate(zip(actual, expected)):
        if b is None:
            assert a is None
        else:
            np.testing.assert_allclose(a, b, atol=1e-5, rtol=1e-3 if i in (1, 3) else 1e-6)


def test_single_coordinate_integral_and_formula_groups():
    p = Pattern(np.linspace(.01, 10., 200), np.ones(200))
    close(rust.calculate_fr(p, np.array([1.2])), transform.calculate_fr(p, np.array([1.2])))
    for formula in ("(Mg0.5Fe0.5)2SiO4", " Mg2 [SiO4] ", "Na{SiO2}2"):
        assert rust.parse_str_to_composition(formula) == utility.parse_str_to_composition(formula)
    c = {"Mg": 0., "Fe": 2., "Si": 1., "O": 4.}
    close(rust.calculate_f_mean_squared(c, p.x), utility.calculate_f_mean_squared(c, p.x))
    assert len(rust.get_available_elements("xraylib")) == 98


@pytest.mark.parametrize("stem,formula,rho,qmax", [("SiO2", "SiO2", 2.2, 17.), ("Mg2SiO4_ambient", "Mg2SiO4", 2.9, 20.)])
@pytest.mark.parametrize("algorithm", ["brent", "brent_local"])
def test_brent_density_against_independent_scipy(stem, formula, rho, qmax, algorithm):
    from pathlib import Path
    from scipy.optimize import minimize_scalar
    from glassure.calc import create_calculate_pdf_configs, calculate_pdf
    from glassure.configuration import IntNormalization, OptimizeConfig
    from glassure.methods import ExtrapolationMethod
    directory = Path(__file__).parent / "data"
    data, config = create_calculate_pdf_configs(Pattern.from_file(str(directory / (stem + ".xy"))), formula, rho,
        Pattern.from_file(str(directory / (stem + "_bkg.xy"))))
    data.bkg_scaling = .98
    config.transform.q_min = 1.; config.transform.q_max = qmax; config.transform.r_min = 1e-13
    config.transform.extrapolation.method = ExtrapolationMethod.LINEAR
    config.transform.normalization = IntNormalization()
    config.optimize = OptimizeConfig(r_cutoff=1.4, iterations=3)
    options = dict(method="gr", min_range=(.1,1.), vary_bkg_scaling=False)
    request = rust._density_request(data, config, **options, optimization_method=algorithm)
    actual = rust._engine(1).density(request)
    working = config.model_copy(deep=True)
    def residual(density):
        working.sample.density = density
        pattern = calculate_pdf(data.model_copy(), working).gr.limit(.1,1.)
        return pattern.y * (pattern.x[1]-pattern.x[0])
    def objective(density):
        r = residual(density)
        return float(r @ r)
    if algorithm == "brent":
        expected = minimize_scalar(objective, bounds=(1e-12,100.), method="bounded", options={"xatol":1e-8})
    else:
        # SciPy's own bracketing/Brent code, with no Rust/TRF answer supplied.
        expected = minimize_scalar(objective, bracket=(rho,1.1*rho), method="brent", options={"xtol":1e-8})
    assert expected.success
    np.testing.assert_allclose(actual["density"], expected.x, atol=1e-5, rtol=1e-6)
    np.testing.assert_allclose(actual["sum_squared_residuals"], expected.fun, atol=1e-14, rtol=1e-9)
    # The returned uncertainty remains a conditional least-squares standard error.
    h = 1e-4 * actual["density"]
    derivative = (residual(actual["density"]+h)-residual(actual["density"]-h))/(2*h)
    error = np.sqrt(actual["sum_squared_residuals"] / (derivative.size-1) / (derivative @ derivative))
    np.testing.assert_allclose(actual["density_error"], error, atol=1e-5, rtol=1e-3)
    assert actual["error_kind"] == "conditional_standard_error"
    assert actual["background_error"] == 0.
    trf = rust._engine(1).density(rust._density_request(data, config, **options))
    if algorithm == "brent_local":
        assert actual["sum_squared_residuals"] <= trf["sum_squared_residuals"] * (1.+1e-10)
    else:
        # A full-interval scalar search is not interchangeable on these
        # multimodal objectives. Keep this observed distinction explicit.
        assert actual["sum_squared_residuals"] > trf["sum_squared_residuals"] * 1.1
    serial = rust.optimize_density_batch([(data,config)]*3, threads=1, **options, optimization_method=algorithm)
    parallel = rust.optimize_density_batch([(data,config)]*3, threads=3, **options, optimization_method=algorithm)
    assert serial == parallel
    with pytest.raises(ValueError, match="evaluation_budget"):
        rust.optimize_density(data, config, **options, optimization_method=algorithm, max_evaluations=10)
    with pytest.raises(ValueError, match="fixed background"):
        rust.optimize_density(data, config, optimization_method=algorithm)
