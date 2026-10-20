# Backend selection

Glassure includes a standalone Rust numerical core, a command-line application,
NumPy-native Python bindings and WASM support. The Python implementation remains
available with its existing imports and configuration objects.

For architecture, build instructions, Rust/Python examples, API coverage and
validation limits, see the repository's [Rust backend guide](https://github.com/CPrescher/Glassure/blob/develop/rust/README.md).
Glassure 3 bundles the native extension in the main Python package. Its only
mandatory direct Python dependencies are NumPy and Pydantic. Binary wheels need
no compiler; source builds require Rust 1.93 or newer. The Python reference
backend and dependency-specific legacy interfaces require `glassure[legacy]`.
See the [migration guide](migration-3.md).

Existing imports now use **auto** selection by default: Rust when the bundled
native extension can be loaded with the required API, Python otherwise.

```python
from glassure.calc import calculate_pdf
from glassure.optimization import optimize_density

result = calculate_pdf(data_config, calculation_config)  # auto
result = calculate_pdf(data_config, calculation_config, backend="python")
result = calculate_pdf(data_config, calculation_config, backend="rust")
fit = optimize_density(data_config, calculation_config, backend="rust")
```

An omitted `backend` argument inherits the current selection. Explicit `auto`
overrides a context's Python/Rust choice and resolves availability again.

```python
from glassure import get_backend, set_backend, use_backend

print(get_backend())  # effective selection: "rust" or "python"

with use_backend("python"):
    reference = calculate_pdf(data_config, calculation_config)

set_backend("rust")   # default for this execution context
set_backend("auto")   # restore automatic selection
```

Selections are context-local. Temporary selections restore the previous mode
even if a calculation raises. Async tasks have isolated context settings; new
threads start with `auto`. A forced Python calculation pins its nested numerical
calls to Python, including the complete inner pipeline of density fitting.

Explicit Rust selection raises `ImportError` if the extension cannot be loaded
or lacks the required engine API. Auto only falls back for extension availability:
input, adapter, unsupported-operation and calculation errors propagate from the
selected backend. The dispatcher does not retry failed Rust calculations in Python.

Selection covers full PDF calculations, density and S(Q) optimization,
normalization, transforms, extrapolation, composition/density/scattering helpers,
peak models, Pattern smoothing/rebinning, scattering-calculator methods and
Soller corrections. Existing positional arguments, Python configuration and
Result/Pattern types are retained. Soller constructors accept a keyword-only
`backend` choice and retain their selected engine throughout the object's life.

Configuration construction, validation, Pattern I/O/arithmetic and table
inspection remain Python interfaces. `calculate_transfer_function` retains its
Python implementation and complete SciPy `UnivariateSpline` return interface;
the explicit Rust adapter's transfer function provides evaluation only. Backend
selection does not replace Python-specific object interfaces with incompatible
Rust objects. Results can differ slightly within numerical/convergence tolerances.

For applications that use Rust directly, see [Using Glassure from Rust](rust.md),
including the executable file-to-fit workflow and generated Rust API reference.

The explicit Rust module remains useful for native batches and sweeps and is
independent of the context's default choice:

```python
from glassure import rust

result = rust.calculate_pdf(data_config, calculation_config)
results = rust.calculate_batch([(data_config, calculation_config)] * 16, threads=4)
```

The core itself needs no Python interpreter, NumPy, SciPy or installed xraylib
library. Native Python calls pass NumPy buffers directly, with owned input
snapshots and output buffer transfer; numerical arrays do not pass through JSON.

For use without Python at all, build the standalone executable with
`cargo build --locked --release`. It loads XY/CHI patterns and JSON requests,
and `target/release/glassure project input.json output.json` recalculates saved
web projects while preserving their settings and metadata. See the Rust guide
for file formats, standalone density fitting and validation commands. The
Python `backend="rust"` option retains Python's API and file handling; the
standalone executable provides the workflow without a Python interpreter.

Supported least-squares density fits use analytic derivatives automatically,
including derivatives through iterative S(Q) optimization. The core packs the
calculation and its density derivative into the same FFT and reuses its Jacobian
for conditional error estimates. Other configurations retain finite differences;
see the Rust guide for the supported combinations and benchmark results.

Density-only fits with background scale fixed also offer `brent_local`
(bracketed from the supplied density) and `brent` (full-interval bounded search)
through `optimization_method`. TRF remains the default; a full-interval Brent
search can select a different, worse minimum when the objective is multimodal.
