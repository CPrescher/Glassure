# Using Glassure from Rust

Glassure's Rust core runs the calculation pipeline without a Python interpreter.
Use it as a library in a Rust application, through the standalone command line,
or compiled to WebAssembly. The Python API remains supported. This release snapshot contains the standalone
Rust packages; Python and browser integrations are built separately.

The first Rust release contains `glassure-core`
0.1.0 (Rust library) and `glassure-cli` 0.1.0 (the `glassure` executable), with
a Rust 1.93 minimum build version. No runtime network connection or installed
xraylib library is required: scattering data are embedded in the core.

## Build and open the API reference

From the repository root:

```sh
cargo build --locked --release
cargo test --locked
cargo doc --locked --no-deps -p glassure-core --open
```

The default workspace members build the Rust core and CLI without the Python
extension. The searchable API reference is generated at
`target/doc/glassure_core/index.html`. It documents request fields, units,
defaults, errors and individual processing operations. To check documentation:

```sh
RUSTDOCFLAGS="-D warnings" cargo doc --locked --no-deps -p glassure-core
cargo test --locked -p glassure-core --doc
```

The second command executes the self-contained examples in the crate overview.
The first treats broken Rust API links and other documentation warnings as
errors. CI runs these checks and retains the generated reference as an artifact;
the reference has not been deployed to a public documentation host.

For another local Rust application, add a path dependency in its `Cargo.toml`,
adjusting the path relative to that application's manifest:

```toml
[dependencies]
glassure-core = { path = "../Glassure/rust/glassure-core" }
```

Use `glassure_core` in Rust imports. The library accepts owned arrays and typed
requests; Rust callers do not need to serialize numerical arrays as JSON.
`cargo add glassure-core@0.1.0` selects the registry dependency, and
`cargo install --locked glassure-cli --version 0.1.0` installs the executable.
For a local source build, use `cargo install --locked --path rust/glassure-cli`
from the checkout. Archive verification and release steps are documented in the
[Rust release guide](https://github.com/CPrescher/Glassure/blob/codex/rust-release-0.1.0/rust/RELEASING.md).

## A complete native workflow

This executable example loads the repository's SiO₂ measurement and background,
calculates a PDF, fits density with TRF, executes a mixed batch and sweeps Q_max.
It exports all curves as XY files and writes reusable CLI request templates:

```sh
cargo run --locked --release -p glassure-core --example workflow -- tests/data/SiO2.xy tests/data/SiO2_bkg.xy target/rust-doc-example
```

The composition and initial density in the example are specific to that dataset.
For another sample, change the composition, density, Q range and low-r cutoff.
Density fitting minimizes a selected low-r objective; its physical applicability
depends on that interval and the sample/model assumptions.

For the bundled files and these settings, the numerical fit returns approximately
9.288 g/cm³. This is the minimum reached by this example's objective, not a
physically validated SiO₂ density or a reproduction of the 2.2 g/cm³ starting
value. The example demonstrates execution and API usage; selecting physically
appropriate normalization, corrections and fit constraints is a separate task.

```{literalinclude} ../rust/glassure-core/examples/workflow.rs
:language: rust
```

`Request::new` fills calculation defaults, then fields can be changed directly.
It uses fit normalization above 3 Å⁻¹, Brown–Hubbell scattering, step
extrapolation, FFT and r = 0–10 Å in 0.01 Å increments. Incoherent scattering
subtraction is enabled; S(Q) optimization and other corrections are disabled.
The example explicitly changes extrapolation and enables iterative optimization.

## Units and data conventions

| Input/output | Unit or meaning |
| --- | --- |
| Q coordinates, q_min, q_max, normalization cutoff | Å⁻¹ |
| r coordinates, r_cutoff, r_step, wavelength, peak positions/widths | Å |
| `Request::density`, fitted `DensityResult::density` | Mass density, g/cm³ |
| `Factors::atomic_density`, density in individual transform functions | Atomic density, atoms/Å³ |
| Composition | Formula or relative atomic amounts; not mass fractions |
| S(Q), g(r) | Dimensionless |
| F(r) | Å⁻²; F(r) = 4πρr[g(r) − 1] |
| General Soller geometry, sample thickness and shifts | mm |
| High-level `request::Dac` thicknesses and `soller_dac` thickness inputs | µm |
| Two-theta for `SollerMap::new` | Degrees |

Use `scattering::atomic_density` and `mass_density` to convert between density
conventions. For example, SiO₂ at 2.2 g/cm³ has an atomic density of approximately
0.06615 atoms/Å³ with Glassure's reference atomic weights and conversion constant.
The crate's executable documentation checks that conversion and its inverse.

Full PDF inputs require at least two strictly increasing, finite, nonnegative Q
values and finite intensities. Cropping is strict: `q_min < Q < q_max`. Equal-length
backgrounds are combined by index, matching Python, even if their coordinates
differ. Different-length backgrounds are interpolated over the common domain.
Align equally sized backgrounds before calculation if their Q grids differ.

`Pattern::from_file` reads whitespace-separated XY columns, ignores additional
columns, comments beginning with `#` and blank lines, and skips four header rows
for `.chi` files. Other files use the supplied `skip_rows`. Use `from_xy_text`
and `to_xy_text` for in-memory input/output, including WASM. Smoothing widths
are in sample indices. Rebinning empty bins yields NaN, which must be handled
before passing the pattern into a calculation.

## Corrections and scattering

`scattering::Source` selects `Hajdu`, `BrownHubbell` or `Xraylib`. Check supported
symbols with `available_elements(source)`. Xraylib uses pinned 4.2.1 FF/SF tables
for Z = 1–98; tabulated methods reject out-of-range Q values. Data provenance and
license notices are retained in the Rust source tree.

`Normalization::Integral` selects integral normalization. `Normalization::Fit`
supports Q/Q² weighting, constant multiple scattering and fitted incoherent
container scattering. Klein–Nishina and Soller/DAC corrections require wavelength.
Following the Python pipeline, Klein–Nishina is applied in the fit branch; setting
it does not change the integral-normalization branch. DAC correction also requires
a container composition and current thickness smaller than initial thickness.

`request.lorch` controls the final Fourier transform. `request.optimize` selects
iterative or polynomial S(Q) correction; iterative optimization has its own Lorch
setting. These are separate choices. Low-Q extrapolation supports `step`,
`linear`, `poly` and `spline`; `s0 = None` uses the mixture's theoretical S(0).

## Density fitting and uncertainties

Construct `DensityRequest` from an initial calculation. Its density is a starting
value, and the fitter returns a separate result without updating the caller's
configuration. Density bounds are 1e-12–100 g/cm³. Optional background bounds are
multipliers of the starting scale, with a JSON default of `[0.9, 1.1]`.

| `method` | Residual before multiplying by grid spacing | Range unit |
| --- | --- | --- |
| `gr` | g(r) | Å |
| `fr` | F(r) + 4πρr | Å |
| `sq` | Optimized S(Q) minus the initial unoptimized reference S(Q) | Å⁻¹ |

`min_range` selects a strict interval. When omitted, gr/fr use zero to the
S(Q)-optimization r_cutoff and therefore require enabled optimization; sq uses
zero to q_max. The objective is the sum of squared residuals after each residual
is multiplied by the selected grid spacing.

`algorithm = "lsq"` selects bounded TRF. Supported combinations use analytic
derivatives and reused FFT buffers; other combinations use finite differences
within the same solver. `nelder` selects Nelder–Mead. Density-only fits can also
select `brent_local` or `brent`, with background fixed. Full-interval Brent assumes
a unimodal objective and has selected worse minima in the benchmark datasets;
TRF remains the default.

Inspect `evaluations`, `termination`, `sum_squared_residuals` and `error_kind`.
`evaluations` counts residual evaluations, not FFTs or iterations. The JSON default
budget is 500 and the allowed range is 10–10000. Exhaustion and nonconvergence
return errors. Least-squares/Brent uncertainties are local conditional standard
errors, not complete experimental uncertainty estimates; unidentified errors are
`None`. Nelder preserves Python's legacy residual-sum-of-squares error fields.

## Batches and sweeps

Keep a `parallel::Executor` to reuse its Rayon pool. `new(0)` selects available
native processors up to 64; `new(1)` runs serially. Up to 1024 jobs or sweep points
are accepted per call. Each single calculation/fit remains sequential.

`Job::Calculate` and `Job::Density` may be mixed. Results retain input order.
Always inspect every `Item`: a batch-level `Ok` may contain per-job `Error`
entries. The example above demonstrates handling both variants.

`SweepPoint` overrides mass density, background scale, Q_max and/or r_cutoff on
a clone of the base request. For a density job, density changes the **starting
guess**. An r_cutoff override requires S(Q) optimization. `points` is an explicit
list; it does not implicitly form a Cartesian product. The base request is retained.

## Command line and saved projects

After `cargo build --locked --release`, the executable is `target/release/glassure`
(`glassure.exe` on Windows). Obtain a complete request template directly from XY:

```sh
target/release/glassure init tests/data/SiO2.xy SiO2 2.2 tests/data/SiO2_bkg.xy > target/request.json
target/release/glassure pdf target/request.json target/result.json
```

For settings generated by the complete workflow example:

```sh
target/release/glassure density target/rust-doc-example/density-request.json target/rust-doc-example/fit.json
target/release/glassure batch target/rust-doc-example/batch-request.json target/rust-doc-example/batch.json
target/release/glassure sweep target/rust-doc-example/sweep-request.json target/rust-doc-example/sweep.json
```

The full command set is `init`, `pdf`, `density`, `batch`, `sweep`, `factors` and
`project`. Read help with `target/release/glassure --help`. Calculation commands
accept a request filename or `-`/stdin and an optional output filename. Without
an output filename, they write JSON to stdout. Errors go to stderr with a nonzero
exit status. Batch per-item failures remain in the returned report.

Patterns may contain numeric `x`/`y` arrays or
`{"file": "sample.xy", "skip_rows": 0}`. Paths are relative to the JSON file;
stdin resolves them from the working directory. `Request::new` defaults apply to
the Rust constructor, not to every missing JSON field; use `init` or the generated
templates rather than assuming a minimal request will deserialize.

Saved web-project JSON is a distinct schema with `dataFiles` and `backgroundFiles`:

```sh
target/release/glassure project experiment.json recalculated.json
```

This recalculates every stored configuration and updates sq/fr/gr curves, retaining
input arrays, backgrounds, settings, fitted densities, IDs, selections and metadata.
The output can be reopened by the web app. It does not automatically rerun stored
density-fitting settings. `project::calculations` extracts typed requests for
programmatic fitting/batches; `project::recalculate` updates a whole project.

The importer handles numeric arrays and the native CLI's file references. It does
not import legacy desktop schemas or Python's base64 NumPy payloads. Saved array
precision is retained; the current web server transport separately rounds input
arrays to Float32, which can introduce additional numerical differences.

## WebAssembly and the Python bridge

```sh
rustup target add wasm32-unknown-unknown
cargo check --locked -p glassure-core --target wasm32-unknown-unknown
cargo build --locked --release -p glassure-core --target wasm32-unknown-unknown
```

Native filesystem methods and Rayon are excluded on WASM. A WASM executor accepts
0/1 threads and runs serially. Browser multicore execution uses separate Web
Workers with separate WASM instances. The core supplies a byte ABI; browser worker adapters are distributed separately.
Compiling the core does not deploy a website.

For Python, the optional NumPy/PyO3 wheel accepts array buffers, snapshots owned
inputs before releasing the GIL and transfers output buffers to NumPy. Numerical
arrays do not pass through JSON. The ordinary Python container and API remain available. The Python native bindings and
backend-selection integration use a separate distribution/release process.

## Numerical scope

Rust follows Glassure's reference normalization, FFT indexing and extrapolation
conventions. Convergence and floating-point evaluation can yield small differences.
Rust's inverse g(r) helper honors its method argument; the current Python helper
ignores it. The Rust transfer spline supports evaluation, while Python retains
the full SciPy object interface. Agreement tests establish implementation
agreement, not independent validation of the physical assumptions.

See the [Rust package release guide](https://github.com/CPrescher/Glassure/blob/codex/rust-release-0.1.0/rust/RELEASING.md)
for archive checks and publication procedure. Source changes,
local checks, configured remote CI and published packages are separate states.
