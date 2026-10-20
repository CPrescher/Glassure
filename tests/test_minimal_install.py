"""The installed Rust package must work without any legacy dependencies."""

import json
from pathlib import Path
import subprocess
import sys


def test_native_workflow_without_optional_imports():
    code = r'''
import importlib.abc
from importlib.metadata import requires, version
import sys

optional = {"scipy", "pandas", "lmfit", "xraylib", "urllib3"}
class NoLegacy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in optional:
            raise ModuleNotFoundError(fullname, name=fullname)
sys.meta_path.insert(0, NoLegacy())

import json
import numpy as np
import glassure
from glassure import Pattern, rust
from glassure.calc import calculate_pdf, create_calculate_pdf_configs
from glassure.configuration import CalculationConfig, IntNormalization, OptimizeConfig
from glassure.normalization import normalize_fit_lmfit
from glassure.optimization import optimize_density
from glassure.scattering_factors import get_calculator
from glassure.soller_correction import SollerCorrection
from glassure.transfer_function import calculate_transfer_function

assert glassure.get_backend() == "rust"
assert glassure.__version__ == version("glassure")
required = {entry.split(";")[0].split(">=")[0] for entry in requires("glassure") if ";" not in entry}
assert required == {"numpy", "pydantic"}, required

directory = sys.argv[1]
data = Pattern.from_file(directory + "/SiO2.xy")
background = Pattern.from_file(directory + "/SiO2_bkg.xy")
d, c = create_calculate_pdf_configs(data, "SiO2", 2.2, background, .98)
c.transform.q_min, c.transform.q_max = 1., 17.
c.transform.r_min = 1e-10
c.optimize = OptimizeConfig(r_cutoff=1.4, iterations=3)
for source in ("hajdu", "brown_hubbell", "xraylib"):
    c.transform.scattering_factor_source = source
    result = calculate_pdf(d, c)
    assert isinstance(result.sq, Pattern)
    assert all(np.isfinite(p.y).all() for p in (result.sq, result.fr, result.gr))
    calc = get_calculator(source)
    assert "Si" in calc.elements
    assert np.isfinite(calc.get_coherent_scattering_factor("Si", data.x)).all()
    assert np.isfinite(calc.get_incoherent_intensity("Si", data.x)).all()

c.transform.scattering_factor_source = "hajdu"
c.transform.normalization = IntNormalization()
result = calculate_pdf(d, c)
fit = optimize_density(d, c, method="gr", min_range=(.1, 1.), vary_bkg_scaling=False)
assert len(fit) == 4 and np.isfinite(fit[0])
batch = rust.calculate_batch([(d, c), (d, c)], threads=2)
np.testing.assert_allclose(batch[0].gr.y, result.gr.y)
assert len(rust.parameter_sweep(d, c, [{"q_max": 15.}, {"q_max": 16.}])) == 2
assert np.isfinite(data.smooth(1.).y).all()
assert len(data.rebin(.05).x) > 0
# Pattern arithmetic used to import SciPy even in a Rust installation.
assert len((data + Pattern(background.x[::2], background.y[::2])).x) > 0
combined = Pattern([0., 1., 2.], [1., 1., 1.]) + Pattern([2., 0.], [20., 0.])
np.testing.assert_allclose(combined.y, [1., 11., 21.])
restored = CalculationConfig.model_validate_json(c.model_dump_json())
assert restored.sample.composition == c.sample.composition
correction = SollerCorrection(np.linspace(1., 30., 40), .1)
assert np.isfinite(correction.transfer_function_sample(.05)).all()
transfer = rust.calculate_transfer_function(data, data)
np.testing.assert_allclose(transfer(data.x), 1., atol=1e-8)

def needs_legacy(operation):
    try:
        operation()
    except ImportError as error:
        assert "glassure[legacy]" in str(error), str(error)
    else:
        raise AssertionError("Legacy dependency was not required")

needs_legacy(lambda: normalize_fit_lmfit(data, np.ones_like(data.x)))
needs_legacy(lambda: calculate_transfer_function(data, data))
needs_legacy(lambda: get_calculator("hajdu").coherent_param)
needs_legacy(lambda: data.smooth(1., backend="python"))
needs_legacy(lambda: calculate_pdf(d, c, backend="python"))
assert not optional.intersection(sys.modules)
print(json.dumps({"version": glassure.__version__, "backend": glassure.get_backend()}))
'''
    directory = str(Path(__file__).parent / "data")
    result = subprocess.run(
        [sys.executable, "-c", code, directory], capture_output=True, text=True,
        check=True,
    )
    assert json.loads(result.stdout)["backend"] == "rust"
