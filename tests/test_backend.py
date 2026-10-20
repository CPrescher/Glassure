"""Backend policy, isolation, fallback boundaries and existing-API integration."""
import asyncio
import inspect
import json
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from glassure import Pattern, get_backend, set_backend, use_backend
from glassure import backend as selection
from glassure.calc import calculate_pdf, create_calculate_pdf_configs
from glassure.configuration import IntNormalization, OptimizeConfig
from glassure.methods import ExtrapolationMethod


@pytest.fixture
def engines(monkeypatch):
    state = SimpleNamespace(available=True, called=[])
    native = SimpleNamespace(Engine=object, run=object())
    adapter = SimpleNamespace()
    def load(name):
        if name == "glassure._glassure_numpy":
            if not state.available:
                raise ModuleNotFoundError("No module named 'glassure._glassure_numpy'", name=name)
            return native
        assert name == "glassure.rust"
        return adapter
    monkeypatch.setattr(selection, "import_module", load)
    with use_backend("auto"):
        yield state, native, adapter


@pytest.mark.parametrize("available", [False, True])
def test_auto_and_keyword_overrides_restore_default(engines, available):
    state, _, rust = engines
    state.available = available
    @selection.dispatch
    def operation(x):
        return "python", x, get_backend()
    rust.operation = lambda x: ("rust", x, get_backend())
    expected = "rust" if available else "python"
    assert operation(3) == (expected, 3, expected)
    assert operation(3, backend="python") == ("python", 3, "python")
    assert get_backend() == expected
    if available:
        with use_backend("python"):
            assert operation(4, backend="rust") == ("rust", 4, "rust")
            assert get_backend() == "python"
    else:
        with pytest.raises(ImportError, match="glassure wheel"):
            operation(3, backend="rust")
        with pytest.raises(ImportError):
            set_backend("rust")
        assert get_backend() == "python"


def test_python_never_loads_native_and_nested_calls_stay_python(monkeypatch):
    def forbidden(_):
        pytest.fail("A forced Python calculation tried to load Rust")
    monkeypatch.setattr(selection, "import_module", forbidden)
    @selection.dispatch
    def child():
        return get_backend()
    @selection.dispatch
    def parent():
        return child()
    assert parent(backend="python") == "python"


def test_auto_fallback_is_pinned_for_entire_python_call(engines):
    state, _, _ = engines
    state.available = False
    @selection.dispatch
    def child():
        return get_backend()
    @selection.dispatch
    def parent():
        state.available = True
        return child()
    assert parent() == "python"
    assert get_backend() == "rust"


@pytest.mark.parametrize("error", [ValueError("invalid input"), RuntimeError("failed fit"),
                                  ImportError("adapter dependency"), NotImplementedError("unsupported")])
def test_native_calculation_errors_never_trigger_fallback(engines, error):
    _, _, rust = engines
    @selection.dispatch
    def operation():
        pytest.fail("Unexpected Python fallback")
    def fail():
        raise error
    rust.operation = fail
    with pytest.raises(type(error)) as caught:
        operation()
    assert caught.value is error
    assert get_backend() == "rust"


@pytest.mark.parametrize("problem", [ImportError("incompatible extension"), OSError("missing shared library")])
def test_unloadable_extension_is_unavailable_in_auto(monkeypatch, problem):
    def fail(_):
        raise problem
    monkeypatch.setattr(selection, "import_module", fail)
    with use_backend("auto"):
        assert get_backend() == "python"
        with pytest.raises(ImportError, match="Rust backend is unavailable") as caught:
            set_backend("rust")
        assert caught.value.__cause__ is problem


def test_old_native_api_is_unavailable(engines):
    _, native, _ = engines
    del native.run
    assert get_backend() == "python"
    with pytest.raises(ImportError, match="unavailable"):
        with use_backend("rust"):
            pytest.fail("Missing backend API accepted")


def test_scoped_selection_restores_after_errors_and_async_tasks(engines):
    with pytest.raises(RuntimeError):
        with use_backend("python"):
            assert get_backend() == "python"
            raise RuntimeError("callback")
    assert get_backend() == "rust"
    async def task(mode):
        set_backend(mode)
        await asyncio.sleep(0)
        return get_backend()
    async def run():
        return await asyncio.gather(task("python"), task("rust"))
    assert asyncio.run(run()) == ["python", "rust"]
    assert get_backend() == "rust"
    set_backend("python")
    assert get_backend() == "python"
    set_backend("auto")
    assert get_backend() == "rust"


@pytest.mark.parametrize("mode", ["invalid", "Rust", "", None])
def test_invalid_setting_is_rejected(mode):
    with pytest.raises(ValueError, match="backend must be"):
        set_backend(mode)
    with pytest.raises(ValueError, match="backend must be"):
        with use_backend(mode):
            pass
    if mode is not None:
        with pytest.raises(ValueError, match="backend must be"):
            calculate_pdf(None, None, backend=mode)


def test_signature_keeps_positional_arguments_and_adds_keyword_only_backend():
    params = inspect.signature(calculate_pdf).parameters
    assert list(params) == ["data_config", "calculation_config", "backend"]
    assert params["backend"].kind == inspect.Parameter.KEYWORD_ONLY
    assert calculate_pdf.__name__ == "calculate_pdf"


def test_fresh_import_and_auto_pipeline_without_native_extension():
    # A fresh interpreter proves fallback isn't being supplied by a module that
    # was loaded before the missing-extension simulation in this test process.
    code = """
import importlib.abc, sys, json
class Missing(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'glassure._glassure_numpy':
            raise ModuleNotFoundError(fullname, name=fullname)
sys.meta_path.insert(0, Missing())
import glassure, numpy as np
assert 'glassure._glassure_numpy' not in sys.modules
assert 'glassure.rust' not in sys.modules
from glassure.calc import create_calculate_pdf_configs, calculate_pdf
p = glassure.Pattern(np.linspace(.1,10,200), np.full(200,100.))
d,c = create_calculate_pdf_configs(p,'SiO2',2.2)
r = calculate_pdf(d,c)
assert np.isfinite(r.gr.y).all()
assert glassure.get_backend() == 'python'
assert 'glassure.rust' not in sys.modules
try:
    calculate_pdf(d,c,backend='rust')
except ImportError as error:
    assert 'glassure wheel' in str(error)
else:
    raise AssertionError('Explicit Rust did not fail')
print(json.dumps({'fallback':True,'points':len(r.sq.x)}))
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["fallback"]


@pytest.fixture
def pdf_inputs():
    from pathlib import Path
    directory = Path(__file__).parent / "data"
    with use_backend("python"):
        data, config = create_calculate_pdf_configs(
            Pattern.from_file(str(directory/"SiO2.xy")), "SiO2", 2.2,
            Pattern.from_file(str(directory/"SiO2_bkg.xy")), bkg_scaling=.98)
    config.transform.q_min = 1.; config.transform.q_max = 17.; config.transform.r_min = 1e-13
    config.transform.extrapolation.method = ExtrapolationMethod.LINEAR
    config.transform.normalization = IntNormalization()
    config.optimize = OptimizeConfig(r_cutoff=1.4, iterations=3)
    return data, config


def native_required():
    available, _ = selection._native_status()
    if not available:
        pytest.skip("Build the bundled extension for numerical integration checks")


def test_existing_full_pipeline_dispatches_once_and_keeps_python_types(pdf_inputs, monkeypatch):
    native_required()
    from glassure import calc, rust
    data, config = pdf_inputs
    expected = calculate_pdf(data, config, backend="python")
    original = rust.calculate_pdf
    calls = []
    def calculate(*args, **kwargs):
        calls.append("rust")
        return original(*args, **kwargs)
    monkeypatch.setattr(rust, "calculate_pdf", calculate)
    def forbidden(*args, **kwargs):
        pytest.fail("Rust pipeline called a Python numerical stage")
    monkeypatch.setattr(calc, "normalize", forbidden)
    monkeypatch.setattr(calc, "calculate_fr", forbidden)
    actual = calculate_pdf(data, config, backend="auto")
    assert calls == ["rust"]
    assert type(actual) is type(expected)
    for name in ("sq", "fr", "gr"):
        a,b = getattr(actual,name),getattr(expected,name)
        assert isinstance(a,Pattern) and isinstance(a.y,np.ndarray)
        np.testing.assert_allclose(a.x,b.x,atol=1e-10,rtol=1e-10)
        np.testing.assert_allclose(a.y,b.y,atol=1e-8,rtol=1e-8)


def test_forced_python_pipeline_never_enters_rust(pdf_inputs, monkeypatch):
    native_required()
    from glassure import rust
    def forbidden(*args, **kwargs):
        pytest.fail("Forced Python reached a native adapter")
    for name in ("calculate_pdf", "calculate_f_mean_squared", "calculate_fr", "normalize"):
        monkeypatch.setattr(rust,name,forbidden)
    with use_backend("auto"):
        assert isinstance(calculate_pdf(*pdf_inputs,backend="python").sq,Pattern)


def test_density_and_low_level_imports_select_either_backend(pdf_inputs):
    native_required()
    from glassure import calculate_fr
    from glassure.optimization import optimize_density
    data,config = pdf_inputs
    options = dict(method="gr",min_range=(.1,1.),vary_bkg_scaling=False)
    py = optimize_density(data.model_copy(),config,backend="python",**options)
    native = optimize_density(data,config,backend="rust",**options)
    for i,(a,b) in enumerate(zip(native,py)):
        np.testing.assert_allclose(a,b,atol=1e-5,rtol=1e-3 if i in (1,3) else 1e-6)
    sq = calculate_pdf(data,config,backend="python").sq
    for method in ("fft","integral"):
        a = calculate_fr(sq,method=method,backend="python")
        b = calculate_fr(sq,method=method,backend="rust")
        np.testing.assert_allclose(a.y,b.y,atol=1e-8,rtol=1e-8)


def test_soller_objects_keep_their_types_and_constructor_selection():
    native_required()
    from glassure.soller_correction import SollerCorrection, SollerCorrectionGui, Map
    theta = np.linspace(1.,30.,40)
    python = SollerCorrection(theta,.1,backend="python")
    native = SollerCorrection(theta,.1,backend="rust")
    assert isinstance(native,SollerCorrection) and isinstance(native.dispersion_angle_map,Map)
    np.testing.assert_allclose(native.dispersion_angle_map.data,python.dispersion_angle_map.data,atol=1e-8,rtol=1e-8)
    with use_backend("python"):
        np.testing.assert_allclose(native.transfer_function_sample(.05),python.transfer_function_sample(.05),atol=1e-8,rtol=1e-8)
    gui = SollerCorrectionGui(np.linspace(.1,10.,40),.29,.1,backend="rust")
    assert isinstance(gui,SollerCorrectionGui) and isinstance(gui,SollerCorrection)
