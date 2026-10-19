# Glassure core

A standalone, f64 Rust library for X-ray total-scattering analysis. It includes
embedded scattering factors, background subtraction, normalization, low-Q
extrapolation, corrections, Fourier transforms and density optimization. Native
Rust, Python/NumPy bindings and WebAssembly share this numerical implementation.
No Python interpreter, installed xraylib library or network connection is needed
at runtime. Version 0.1.0 is the first standalone Cargo release. Building requires Rust 1.93 or newer.

## Add the library to an application

Add the library with `cargo add glassure-core@0.1.0`, or use a local path dependency:

```toml
[dependencies]
glassure-core = { path = "../Glassure/rust/glassure-core" }
```

The Rust import name is `glassure_core`. The companion `glassure-cli` package
installs the standalone `glassure` executable; Python bindings are distributed
separately as the optional `glassure-native` wheel.

## Start with a calculation

Use [`request::Request::new`] to obtain defaults, change settings, then call
[`request::calculate`]. The following self-contained example synthesizes an
intensity from the embedded scattering factors, with a known normalization of 2:

```rust
use glassure_core::{
    pattern::Pattern,
    request::{calculate, Request},
    scattering::{factors, Composition},
};

let composition = Composition::Formula("SiO2".into());
let q: Vec<f64> = (1..=200).map(|i| i as f64 * 0.1).collect();
let scattering = factors(&composition, 2.2, &q)?;
let intensity = scattering.f2.iter().zip(&scattering.incoherent)
    .map(|(f2, inc)| (f2 + inc) / 2.0).collect();
let data = Pattern::new(q, intensity)?;
let request = Request::new(data, composition, 2.2)?;
let result = calculate(request)?;
assert!((result.normalization - 2.0).abs() < 1e-12);
assert_eq!(result.gr.x.len(), result.gr.y.len());
# Ok::<(), String>(())
```

This example checks a normalization identity; it is not a model of the measured
structure of silica. The pipeline strictly crops to `q_min < Q < q_max` and
extends S(Q) towards zero before transforming. Its defaults are Brown–Hubbell
factors, high-Q fit normalization above 3 Å⁻¹, step extrapolation, no S(Q)
optimization or Lorch modification, and an FFT onto 0–10 Å in 0.01 Å steps.

## Units and conventions

| Quantity | Convention |
| --- | --- |
| Q | Å⁻¹, `Q = 4π sin(θ) / wavelength` |
| r, wavelength, peak positions/widths | Å |
| [`request::Request::density`] | Mass density, g/cm³ |
| [`scattering::Factors::atomic_density`] | Number density, atoms/Å³ |
| Density arguments in [`functions`] and [`Input`] | Atomic density, atoms/Å³ |
| S(Q), g(r) | Dimensionless |
| F(r) | Å⁻², `F(r) = 4πρ r [g(r) − 1]` |
| Soller geometry and map distances | mm; angles supplied to `SollerMap::new` are degrees |
| [`request::Dac`] thicknesses | µm (converted by the DAC correction) |

[`scattering::atomic_density`] and [`scattering::mass_density`] convert the two
density conventions. Composition amounts are atomic counts or relative atomic
amounts, not mass fractions. Formula strings support fractional counts and nested
parentheses, brackets and braces; normalized fractions sum to one.

```rust
use glassure_core::scattering::{atomic_density, mass_density, Composition};
let silica = Composition::Formula("SiO2".into());
let fractions = silica.fractions()?;
assert!((fractions["O"] - 2.0 / 3.0).abs() < 1e-15);
let rho = atomic_density(&silica, 2.2)?;
assert!((rho - 0.06615).abs() < 1e-5);
assert!((mass_density(&silica, rho)? - 2.2).abs() < 1e-14);
# Ok::<(), String>(())
```

## Working with files and projects

[`pattern::Pattern::from_xy_text`] and [`pattern::Pattern::to_xy_text`] work on
native and WASM targets. Native builds also provide `Pattern::from_file`
and `Pattern::save`. Files contain whitespace-separated x/y columns;
extra columns are ignored. `#` comments and blank lines are accepted. `.chi`
files skip four header rows; other files use the supplied row count.

```rust
use glassure_core::pattern::Pattern;
let data = Pattern::from_xy_text("# Q I\n0.1 10\n0.2 12\n0.3 11\n", 0)?;
let restored = Pattern::from_xy_text(&data.to_xy_text()?, 0)?;
assert_eq!(restored.x, data.x);
assert_eq!(restored.y, data.y);
# Ok::<(), String>(())
```

[`project::calculations`] converts the web app's saved project JSON into typed
requests. [`project::recalculate`] updates all S(Q), F(r) and g(r) curves while
preserving input data, settings, IDs, selections and UI metadata. It does not
rerun density fitting automatically. These functions consume numeric arrays;
the native CLI additionally resolves relative XY/CHI file references. Browser
applications must read uploaded files before calling the core. Legacy desktop
projects and Python's base64 NumPy API payloads are separate formats.

## Density fitting and multiple jobs

[`density::optimize_density`] fits mass density, optionally with background
scale. `algorithm = "lsq"` selects bounded trust-region reflective least squares
(TRF), the default for JSON requests. Each fit prepares scattering/corrections
once, reuses buffers and uses analytic derivatives when supported. `nelder`,
`brent_local` and `brent` are explicit alternatives; both Brent variants require
fixed background. Full-interval Brent can select a worse minimum on a multimodal
objective. See [`density::DensityRequest`] for objectives, ranges and bounds.

[`parallel::Executor`] retains a native Rayon pool for ordered batches and
parameter sweeps. Only independent jobs are parallelized; an individual
calculation or fit remains sequential. Inspect **every** [`parallel::Item`]: a
successful batch call can still contain individual job errors.

```rust
use glassure_core::{
    parallel::{Executor, Item, Job, SweepPoint}, pattern::Pattern,
    request::Request, scattering::Composition,
};
let q: Vec<f64> = (1..=200).map(|i| i as f64 * 0.1).collect();
let request = Request::new(Pattern::new(q, vec![100.0; 200])?,
    Composition::Formula("SiO2".into()), 2.2)?;
// Keep an executor for subsequent batches. Use 0 for native automatic selection.
let executor = Executor::new(1)?;
let mut invalid = request.clone();
invalid.density = 0.0;
let report = executor.batch(vec![Job::Calculate(request.clone()), Job::Calculate(invalid)])?;
assert!(matches!(&report.items[0], Item::Success { .. }));
assert!(matches!(&report.items[1], Item::Error { .. }));
let sweep = executor.sweep(&Job::Calculate(request), vec![
    SweepPoint { q_max: Some(15.0), ..Default::default() },
    SweepPoint { q_max: Some(17.0), ..Default::default() },
])?;
assert!(sweep.items.iter().all(|item| matches!(item, Item::Success { .. })));
# Ok::<(), String>(())
```

## API map

| Module | Purpose |
| --- | --- |
| [`request`] | Complete PDF pipeline, request/result settings and byte ABI |
| [`pattern`] | Owned x/y arrays, file/text I/O and preprocessing |
| [`scattering`] | Composition parsing, density conversions and embedded factors |
| [`functions`] | Individual normalization, transforms, extrapolation, peak models and transfer splines |
| [`corrections`] | Klein–Nishina and Soller/DAC geometry |
| [`sq_optimization`] | Iterative and polynomial S(Q) optimization |
| [`density`] | Density/background refinement and fit diagnostics |
| [`parallel`] | Ordered batches and sweeps |
| [`project`] | Saved web-project import and recalculation |
| [`numeric`] | Lower-level numerical building blocks |

## Errors, numerical agreement and WASM

High-level calls return `Result<_, String>`. Unknown options, invalid grids,
unsupported scattering states, excessive allocations and nonconverged fits are
errors. They do not trigger Python fallback. Owned patterns permit some legacy
coordinate conventions; individual algorithms impose stricter grid requirements.
Rebinning an empty bin produces NaN, which must be handled before calculation.

Scattering sources are [`scattering::Source::Hajdu`],
[`scattering::Source::BrownHubbell`] (default) and pinned Xraylib 4.2.1 FF/SF tables.
Use [`scattering::available_elements`] to check support; Xraylib tables cover
Z = 1–98. Out-of-table Q values return errors. Embedded data retain their source
provenance and licenses in the repository.

Agreement tests compare against Glassure's Python equations and FFT conventions.
They demonstrate implementation agreement, not independent physical validation.
Optimizers may stop at slightly different parameter values. Least-squares error
fields are local conditional standard errors; Nelder's legacy fields contain
sums of squared residuals. Rust's inverse g(r) transform honors its requested
method; the reference Python helper currently ignores that argument. The native
transfer spline supports evaluation, rather than the full SciPy spline interface.

The core also builds for `wasm32-unknown-unknown`. Native file methods and Rayon
are excluded there. In ordinary WASM builds `Executor::new(0)` and `new(1)` use
one thread; larger values return errors. Browser multicore execution uses a
separate Web Worker pool around independent WASM instances. The compatibility
crate `prototypes/rust-wasm` provides the current JavaScript-facing byte ABI.
