# Glassure Rust backend

Glassure's numerical implementation is available as a standalone Rust library,
command-line application, Python extension and WebAssembly engine. The Rust core
has no Python, NumPy, SciPy, xraylib shared-library or runtime network dependency.
Its numerical arrays and results are owned Rust values. The standalone
`glassure-core` 0.1.2 and `glassure-cli` 0.1.0 packages are published on crates.io.
The native Python wheel and browser integration have separate release processes.

The existing Python implementation remains available. Selecting the Rust backend
does not require changing the scientific input/configuration models.

## Documentation

- [Density fitting tutorial](../docs/rust-density-fitting.md): corrections,
  fixed/joint background fits, diagnostics and native multicore jobs.

- [Step-by-step analysis tutorial](../docs/rust-analysis.md): measured Mg₂SiO₄
  data through normalization, S(Q), transforms, optimization, Lorch and export,
  with intermediate plots and an equivalent high-level calculation.

- [Rust user guide](../docs/rust.md): library setup, units, complete file-to-fit
  example, corrections, batches/sweeps, CLI requests and saved projects.
- [Crate overview](glassure-core/README.md): self-contained executable examples
  and an API map, also used as the generated Rust reference's landing page.
- [Python backend selection](../docs/rust-backend.md): auto/explicit selection
  and NumPy extension installation.
- [Rust packages and release checks](RELEASING.md): verified `.crate` archives,
  isolated installation checks and the separate publication step.

The published Cargo packages are `glassure-core` 0.1.2 and `glassure-cli` 0.1.0,
requiring Rust 1.93 or newer. The core is imported as `glassure_core`; the CLI
installs `glassure`. Both packages are published on crates.io. Native Python wheels remain
separate, and the existing Python API continues to work.

Build the searchable Rust API reference locally:

```sh
cargo doc --locked --no-deps -p glassure-core --open
```

It is generated at `target/doc/glassure_core/index.html`. Check the reference
and run its examples with:

```sh
RUSTDOCFLAGS="-D warnings" cargo doc --locked --no-deps -p glassure-core
cargo test --locked -p glassure-core --doc
```

CI retains the generated reference as a build artifact. The public API reference
is available on [docs.rs](https://docs.rs/glassure-core/0.1.2/glassure_core/),
including the WASM target.

## Layout

- `glassure-core`: scientific operations, embedded scattering tables, complete
  PDF/density calculations, deterministic batches and parameter sweeps.
- `glassure-cli`: the `glassure` executable, using the core directly.
- `glassure-python`: native NumPy/PyO3 bindings, bundled in the `glassure` Python wheels.
- `../glassure/rust.py`: the Python API using those bindings.

The earlier `prototypes/rust-wasm` crate re-exports this core to preserve its
native/JSON/WASM experiments and the sibling web application's build entry point.
Its NumPy adapter aliases `glassure.rust`. There is one shared implementation of
the Rust numerical equations. The historical benchmark reports retain their dated
source/binary fingerprints. Current measurements of the public NumPy API, including
single calls and multicore batches against Python process pools, are in the
[backend benchmark report](benchmarks/BACKEND_REPORT.md). Single-fit and multicore
density timings are in the [density benchmark report](benchmarks/DENSITY_REPORT.md),
which retains the accepted small convergence difference as an explicit qualification.
The [preparation/buffer reuse comparison](benchmarks/PREPARED_DENSITY_REPORT.md)
measures the current fitter against the original release binary: single fits are
5–8% faster in these workloads, with exactly matching Rust results. The 14-worker
Mg₂SiO₄ case is unchanged within timing variation.
Subsequent [profile-guided FFT optimization](benchmarks/PROFILE_DENSITY_REPORT.md)
identifies FFT execution as about 97% of native fit time. Avoiding FFT copy-back
and padding resets reduces single-fit time by another 5–7% in the measured cases,
with exactly matching results. Stage timers are opt-in (`profiling` feature).
The [analytic-derivative comparison](benchmarks/ANALYTIC_DENSITY_REPORT.md)
measures the next change: derivatives propagated through normalization,
extrapolation, iterative S(Q) optimization and transforms. Packing a value and
its density derivative into one complex FFT reduces transform calls; the cached
Jacobian also supplies the conditional covariance calculation.

Least-squares density fits select analytic derivatives automatically for step or
linear extrapolation with no S(Q) optimization or iterative optimization. Integral
and fit normalization, both transform methods and all three scattering sources
are supported. Joint background refinement is analytic for integral or simple
fit normalization. Joint background fits with multiple/container normalization,
spline/poly extrapolation and polynomial S(Q) optimization retain bounded finite
differences. Nelder–Mead retains its existing derivative-free path. Solver bounds,
tolerances and precision are unchanged; analytic gradients can change the final
stopping point slightly. The ordinary Python implementation remains available.

For fixed-background, density-only fits, the Rust API also accepts
`optimization_method="brent_local"` or `"brent"`. `brent_local` first brackets
a downhill minimum from the supplied density (initial probes ±10% of
`max(|density|, 1)`, followed by golden-ratio expansion within the existing
positive density bounds). It then uses safeguarded parabolic/golden-section
minimization in that bracket. `brent` searches the full density interval directly.
Both return conditional least-squares standard errors, including the final
Jacobian evaluation in their cost. Neither Brent option supports simultaneous
background fitting. These are opt-in alternatives; `lsq`/TRF remains the default.
The [Brent/TRF comparison](benchmarks/BRENT_DENSITY_REPORT.md) records performance
and convergence differences. The full-interval search assumes a unimodal
objective; it selects a worse minimum in the benchmark datasets.

## Rust without Python

From the repository root:

```sh
cargo build --locked --release
cargo test --locked
```

The workspace's default members build the core and executable. They do not build
the Python extension or need a Python interpreter. To use the core from another
Rust project, add a path dependency on `rust/glassure-core`:

```rust
use glassure_core::{
    pattern::Pattern,
    request::{calculate, Request},
    scattering::{Composition, Source},
};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let data = Pattern::from_file("sample.xy", 0)?;
    let mut request = Request::new(data, Composition::Formula("SiO2".into()), 2.2)?;
    request.background = Some(Pattern::from_file("background.xy", 0)?);
    request.q_min = 1.0;
    request.q_max = 17.0;
    request.scattering_factor_source = Source::BrownHubbell;
    let result = calculate(request)?;
    result.sq.save("sq.xy")?;
    result.fr.save("fr.xy")?;
    result.gr.save("gr.xy")?;
    Ok(())
}
```

`Request::new` uses the Python helper's defaults: high-Q fit normalization with a
3 Å⁻¹ cutoff, Brown–Hubbell factors, step extrapolation, FFT, 0–10 Å at 0.01 Å
spacing and strict Q cropping. Composition may also be a map of atomic amounts.
Mass density is g/cm³; atomic density is atoms/Å³; Q is Å⁻¹ and r is Å. The full
request can also be serialized/deserialized with serde. Native Rust callers do
not serialize numerical arrays when calling the library.

An executable example is included:

```sh
cargo run --release -p glassure-core --example pdf -- tests/data/SiO2.xy tests/data/SiO2_bkg.xy target/example-pdf
```

### Command-line calculation

```sh
target/release/glassure init tests/data/SiO2.xy SiO2 2.2 tests/data/SiO2_bkg.xy > target/request.json
target/release/glassure pdf target/request.json target/result.json
```

Edit the request JSON to select ranges, normalization, corrections or optimization.
`pdf`, `density`, `batch`, `sweep` and `factors` accept a request file or `-`/stdin,
with optional output filename. A pattern can contain `x`/`y` arrays or
`{"file":"sample.xy","skip_rows":0}`. File paths are relative to the request
file, or the working directory for stdin. `.chi` files skip four header rows.
Extra numeric columns after x/y are ignored, as in Python's loader. JSON is only
the CLI/legacy browser interchange format, not the Rust library or NumPy binding.
Batch reports retain input order and contain explicit per-item errors.

### Saved browser projects without Python

The executable can read the web app's saved JSON projects directly and
recalculate every data/configuration pair:

```sh
target/release/glassure project experiment.json recalculated.json
```

The output is a project JSON with updated `sq`, `fr` and `gr` arrays, suitable
for reopening in the web app. Input data, backgrounds, selections, configuration
IDs, fitted densities and UI metadata are retained. The command recalculates
PDFs; it does not automatically rerun saved density-optimization settings.
It supports the `dataFiles` / `backgroundFiles` project format with numeric
pattern arrays, including older configurations with missing fields. Defaults
follow the web app's configuration migration and calculation payload. Unknown
numerical settings, missing referenced backgrounds and invalid input produce
errors before an output file is written. Python's base64 NumPy API payloads and
legacy desktop project schemas are separate formats and are not imported here.

Project patterns can also use relative XY/CHI file references as described
above; the saved output then embeds the loaded arrays. The shared Rust API is
`project::calculations(&project)` for extracting typed requests (also usable for
density fitting or multicore batches), and `project::recalculate(project)` for
updating all curves. These APIs compile for native Rust and WASM. Native file
access is handled by the CLI; browser applications still supply file contents
through their normal upload interfaces.

The importer retains the precision of the saved arrays. The current web app's
network payload converts arrays to Float32, so comparison with that transport
can include additional input-rounding differences.

Standalone verification:

```sh
cargo test --locked
uv run python rust/scripts/check_standalone.py
```

The Rust CLI integration test disables Python discovery and exercises XY and
CHI loading, relative JSON file references, project recalculation/reopening,
TRF density fitting and XY output round trips. The separate Python audit
compares independently configured Python calculations against the executable;
it covers normalization, all extrapolation methods, both S(Q) optimizations,
and combined container/DAC/Klein–Nishina corrections. Its report is written to
`target/backend-selection/standalone-project-parity.json`.

## Python capability

Glassure 3 bundles the extension in the main `glassure` wheel. From the root,
`uv sync --extra dev` builds an editable native installation and installs the
optional reference dependencies. Build distributable wheels/source with `uv build`.
Source builds require Rust 1.93 or newer; matching published wheels need no compiler.
See the [migration guide](../docs/migration-3.md) and
[Python release guide](../docs/python-releasing.md).

```python
from glassure import rust

result = rust.calculate_pdf(data_config, calculation_config)
results = rust.calculate_batch([(data_config, calculation_config)] * 64, threads=4)
density, density_error, background, background_error = rust.optimize_density(
    data_config, calculation_config, method="gr", min_range=(0.1, 1.2)
)
points = [{"q_max": 15}, {"q_max": 16}, {"q_max": 17}]
pdfs = rust.parameter_sweep(data_config, calculation_config, points, threads=4)
fits = rust.optimize_density_sweep(
    data_config, calculation_config, points, threads=4,
    method="gr", min_range=(0.1, 1.2), vary_bkg_scaling=False,
)
```

The ordinary `glassure.calc.calculate_pdf` and compatible numerical functions now
default to `auto`: use Rust when its bundled native extension can be loaded,
otherwise the optional Python reference implementation. A keyword-only `backend="python"` / `"rust"` / `"auto"` selects
a backend per call. `glassure.use_backend(...)` scopes a selection;
`set_backend(...)` sets the current context's default; `get_backend()` reports
the effective mode. See [backend selection](../docs/rust-backend.md) for examples
and coverage. Explicit Rust selection requires the bundled native extension. There is no
silent Python fallback for an unsupported or failed Rust calculation. The
`glassure.rust` module continues to explicitly call Rust regardless of this
default. Pydantic configuration creation,
validation and the ordinary Python Pattern container remain Python capabilities;
the core performs the numerical calculation. The native extension receives NumPy
buffers, snapshots f64 inputs before releasing the GIL, and transfers Rust output
allocations directly to NumPy. Result/Pattern wrappers preserve those arrays.
Fitting and sweeps preserve caller-owned data/configurations. `threads=0` selects
available CPUs; 1 is serial; batches/sweeps are capped at 1024 jobs and 64 threads.
Only independent jobs are parallelized; each individual optimizer is sequential.

## Implemented scientific capabilities

| Area | Native Rust capability | Python capability |
| --- | --- | --- |
| Patterns | Owned arrays, XY/CHI loading, XY writing, strict range cropping, interpolation, arithmetic, extension, Gaussian smoothing, rebinning | Existing Pattern objects; `rust.smooth`, `rust.rebin` call Rust |
| Composition/density | Nested formulas with (), [] and {}, fractional amounts, normalized abundances, masses and density conversions | Parsing/conversion functions in `glassure.rust` |
| Scattering | Hajdu, Brown–Hubbell, pinned Xraylib FF/SF tables; mixture moments, incoherent scattering, S(0), pair weights and WKM quantities | Source functions and calculator interfaces |
| Normalization | Integral, weighted linear fit, multiple/container terms, nonnegative fit for the deprecated lmfit interface | `normalize`, `normalize_fit`, `normalize_fit_lmfit` |
| Transforms | Forward/inverse integral and FFT, Lorch, S(Q), F(r), g(r), RDF and T(r) | Functions with the existing argument conventions |
| Extrapolation | Step, linear, polynomial and smoothing spline, overlap replacement | All four extrapolation functions |
| Optimization | Iterative and polynomial S(Q); bounded density/background fitting for g(r), F(r), S(Q); least squares and Nelder–Mead | Optimizers, callback orchestration and result tuples |
| Corrections | Klein–Nishina; full configurable Soller map, shifted sample/regions, DAC transfer functions | Soller classes, maps and geometry helpers |
| Peak models | Reciprocal-space Gaussian-broadened pair peaks, Fourier-space T(r), WKM Gaussian real-space peaks | `i_q_peak`, `t_r_peak`, `t_r_peak_gaussian` |
| Transfer function | Normalized smoothing-spline response and evaluation | Callable `calculate_transfer_function` result |
| Multiple jobs | Persistent Rayon executors; ordered calculate/density batches and parameter sweeps | NumPy-native batch/sweep adapters |

Rust operations are available in `pattern`, `functions`, `scattering`,
`corrections`, `sq_optimization`, `density`, `parallel` and `request`. Generate
Rust API documentation with `cargo doc --no-deps -p glassure-core`.

The native transfer spline supports evaluation, rather than reproducing every
SciPy `UnivariateSpline` method. Python's lmfit normalization compatibility
wrapper uses lmfit only to construct its returned Parameters object; Rust solves
the constrained fit. Source-specific Pandas tables are not duplicated as Python
DataFrames. Formula parsing rejects malformed formulas explicitly.

## WebAssembly

```sh
rustup target add wasm32-unknown-unknown
cargo check --locked -p glassure-core --target wasm32-unknown-unknown
cargo build --locked --release --manifest-path prototypes/rust-wasm/Cargo.toml --target wasm32-unknown-unknown --lib
```

The same core compiles for WASM without PyO3 or Rayon. Existing JSON byte-ABI
exports remain available through the compatibility crate. Browser worker adapters
are distributed separately. Independent workers provide browser multicore execution. The sibling app's
existing browser adapter still selects Brown–Hubbell; the shared core supports the
other sources as well. Python backend selection does not deploy the web app or
change its independent backend settings.

## Provenance, checks and limits

`cargo test` includes standalone operation checks and an executable test with an
empty PATH and nonexistent PYTHONHOME. Python tests compare every implemented
operation against the current reference, all supported scattering states, the
full combined-correction pipeline, 24 density objective/algorithm/background
combinations, buffer ownership and parallel ordering. CI definitions cover the
core/CLI on Linux, macOS and Windows; selected Python versions/platforms; and
WASM compilation. Local results are recorded separately in
[VALIDATION.md](VALIDATION.md); configured remote jobs are not claimed to have run.

Polynomial extrapolation and nonlinear fitting retain the numerical tolerances
and convergence qualifications of the earlier experiments. A nonconverged fit
raises an explicit error; it does not present its final iterate as successful.
Least-squares errors are local conditional standard errors. Nelder's legacy error
fields contain sums of squared residuals, as in Python. These checks demonstrate
implementation agreement, not independent validation of physical assumptions.

The standalone inverse g(r) transform honors its requested method; the reference
Python helper currently ignores that argument. Removable zero-coordinate limits
are evaluated explicitly. Empty rebinning bins remain NaN. The core rejects
invalid/nonfinite calculation inputs and bounds allocations. Xraylib's FF/SF
tables support Z=1–98. Rust lists these actually supported elements; the reference
Python calculator advertises Z=1–107 even though its FF/SF tables stop at 98.
Out-of-table Q values are errors, not silently extrapolated.

Hajdu and Brown–Hubbell table provenance remains with the original Glassure data
and generated Rust sources. Xraylib data are pinned to 4.2.1, with original tables,
lossless binary copies, hashes and BSD notices in `glassure-core/data/xraylib`.
`scripts/generate_tables.py` is an explicit maintainer conversion using Python's
standard library. Ordinary builds use committed data and do not run that script.
SciPy-derived solver and Xraylib notices are included in source packages and
native wheel license metadata. Cargo dependencies retain their own licenses.

The Rust library 0.1.2 and CLI 0.1.0 are published, with Linux/macOS/Windows release
qualification and registry installation verified. Native Python wheel release
automation remains separate release work. Python auto-selection is available
locally; it uses the legacy Python implementation without an installed native wheel.
