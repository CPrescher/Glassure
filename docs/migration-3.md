# Migrating to Glassure 3

Glassure 3 includes its Rust numerical engine in the `glassure` Python package.
The release is currently being prepared as **3.0.0rc1**; it has not been published.

## Installation

```sh
python -m pip install --pre 'glassure==3.0.0rc1'
```

Use that command once the release candidate is published. Supported wheels include
Python 3.10–3.13 on Linux x86-64, Windows x86-64, and macOS on Intel and Apple
Silicon. Installing a matching wheel needs no Rust compiler. Source installations
require Rust 1.93 or newer and a platform C linker; maturin is installed by the
Python build frontend. Other platforms require a source build and are not part
of the initial wheel matrix.

Only **NumPy >=1.26** and **Pydantic >=2.7.1,<3** are mandatory direct Python
runtime dependencies. Those packages have their own dependencies. The Rust engine,
including its scattering tables, is bundled; there is no separate `glassure-native`
installation step or runtime xraylib requirement.

## Existing calculations

The existing imports, `Pattern` arrays, Pydantic configurations and result objects
remain available:

```python
from glassure import get_backend
from glassure.calc import calculate_pdf

assert get_backend() == "rust"
result = calculate_pdf(data_config, calculation_config)
```

The default `auto` mode uses the bundled Rust engine. `backend="rust"` explicitly
requires it. If an extension is missing or unloadable, `auto` can use the Python
reference implementation when its optional dependencies are installed. Calculation
errors in Rust propagate and never trigger a retry with another engine.

The extension is now private to the package (`glassure._glassure_numpy`). Use
public `glassure` functions or `glassure.rust` rather than importing it directly.
The Python package version is independent of the standalone Rust crate versions.

Gaussian real-space pair peaks use the corrected pair weight and neighbouring
atomic fraction. Polynomial S(Q) optimization uses a scaled least-squares fit and
handles exactly Q=0. These corrections also apply to the Python reference backend;
results involving these operations can change compared with Glassure 2.

Numerical outputs are compared against the Python reference within tolerances;
optimizer convergence and floating-point results need not be identical. Embedded
Xraylib tables cover Z=1–98 and their documented Q domain; unsupported elements
and out-of-table values raise errors. These tests establish implementation
agreement, not the physical validity of a fitted density for a particular sample.

## Optional legacy interfaces

```sh
python -m pip install 'glassure[legacy]'
```

This extra installs SciPy, lmfit, pandas and xraylib. It supports:

- The independent Python reference backend (`backend="python"` or
  `with glassure.use_backend("python"):`).
- `normalize_fit_lmfit`, which returns an `lmfit.Parameters` object even when Rust
  solves the fit. Prefer `normalize_fit` for a dictionary of normalization values.
- `glassure.transfer_function.calculate_transfer_function`, which retains its
  SciPy `UnivariateSpline` return type and methods. For native evaluation without
  SciPy, use `glassure.rust.calculate_transfer_function`; its result is callable
  but does not implement the full SciPy spline interface.
- pandas table inspection through `scattering_factors.atomic_weights` and the
  scattering calculators' existing parameter-table attributes. These are loaded
  lazily. Ordinary native scattering calculations need no pandas.

Importing Glassure does not import the legacy dependencies. Calling an interface
that needs a missing optional dependency raises an error with the extra's install
command. Installing the extra leaves `auto` using Rust; select Python explicitly
when reproducing a reference calculation.

## Development and validation

```sh
uv sync --extra dev
uv run pytest tests --glassure-backend=rust
uv run pytest tests --glassure-backend=python
cargo test --locked --workspace --all-features
uv build
python scripts/check_python_dist.py dist
```

`dev` and `docs` include the legacy extra for reference comparisons and API docs.
The first Python sync/build now compiles the extension and requires Rust. Release
CI tests installed wheels outside the checkout, verifies a minimal environment,
runs both backends with the legacy extra, and rebuilds the source distribution.
