# Analytic derivatives for Rust density fitting

The shared Rust/WASM core now propagates analytic derivatives through supported
least-squares density fits. It also packs the value and its density derivative
into one complex FFT. Native single fits take **44–46% less time** than the
previous FFT-optimized Rust backend; batches of 16 fits with 14 workers take
**41–49% less time** on the measured M4 Pro. The Python implementation remains
available, and no numerical arrays pass through JSON in these native timings.

## Single fits

Median milliseconds, seven shuffled warm samples through the public NumPy API.
Input snapshots, per-fit preparation, calculation and result handling are timed.

| Dataset | Python | Previous Rust | Analytic Rust | Rust speedup |
| --- | ---: | ---: | ---: | ---: |
| SiO₂ | 110.974 | 29.135 | 16.427 | 1.77× |
| Mg₂SiO₄ | 170.597 | 58.177 | 31.631 | 1.84× |

## Batches of 16 fits

Python uses persistent spawned process pools; Rust uses persistent Rayon threads.
All pools are warmed. Startup, file loading and initial configuration creation
are excluded. Timed Python pool calls send job indices and return fit tuples.
Inputs already reside in each Python worker. BLAS thread pools are limited to one.

| Dataset | Workers | Python | Previous Rust | Analytic Rust | Rust speedup |
| --- | ---: | ---: | ---: | ---: | ---: |
| SiO₂ | 1 | 1775.412 | 431.727 | 261.718 | 1.65× |
| SiO₂ | 4 | 423.802 | 120.075 | 72.611 | 1.65× |
| SiO₂ | 14 | 197.220 | 58.936 | 35.010 | 1.68× |
| Mg₂SiO₄ | 1 | 3060.040 | 968.613 | 513.706 | 1.89× |
| Mg₂SiO₄ | 4 | 825.854 | 262.969 | 141.273 | 1.86× |
| Mg₂SiO₄ | 14 | 445.577 | 163.523 | 83.944 | 1.95× |

These are fixed-background low-r g(r) fits, matching the preceding benchmark:
integral normalization, Brown–Hubbell factors, linear extrapolation, FFT and
three iterative S(Q) optimization steps. Each batch varies background scale
from 0.98 to 1.02 across its 16 jobs; scale is fixed within each fit. The single
fit uses the first job (0.98). Joint background derivatives are tested but are
not timed in this comparison.

The previous and current native release extensions load side by side. The
baseline wheel is checked against its recorded binary hash. Before/after/Python
paths run sequentially in shuffled order. All samples, quartiles, ranges, source
and binary hashes, process snapshots and measurement order are retained in the
raw report. JSON encoding/decoding is disabled during native warmup checks.
Profiling is compiled out of these API measurements. Background system activity
was present; outliers are retained. These are local macOS ARM64 measurements.

## FFT counts and native profile

The profile runs 64 warmed fits per case in saved before/after release executables.
Its timers include preparation and final output generation but exclude the Python
bridge. Loading the request JSON happens before warmup and measurement.

| Dataset | Residual evaluations before → after | FFTs before → after | FFT reduction | Profile ms/fit before → after |
| --- | ---: | ---: | ---: | ---: |
| SiO₂ | 43 → 23 | 308 → 168 | 45.5% | 29.266 → 16.649 |
| Mg₂SiO₄ | 18 → 9 | 133 → 70 | 47.4% | 58.181 → 31.522 |

Each pipeline has seven transforms: three forward/backward optimization pairs
and the final forward transform. For one fitted parameter, a packed FFT computes
both the value and its tangent using conjugate symmetry. For two parameters,
the background tangent requires one additional transform, rather than two
perturbed full calculations. The stored Jacobian is reused for the trust-region
step and conditional covariance. The counts above include the ordinary final
output pipeline, which does not compute derivatives. Residual evaluation counts
are therefore not a direct count of optimizer iterations.

## Derivative implementation and scope

- Density-to-atomic-density conversion is differentiated analytically.
- Integral normalization differentiates both its density-dependent numerator
  and its background-dependent denominator. Simple fit normalization uses the
  derivative of its weighted least-squares ratio.
- Step/linear extrapolation propagates derivatives on the existing fixed grid.
- Iterative S(Q) optimization applies the product rule through each forward
  transform, density correction, inverse transform and multiplicative update.
- The final transforms and the explicit density factors in F(r)/g(r) objectives
  are differentiated. The S(Q) reference stays fixed, as in the existing fitter.
- The bounded trust-region solver accepts a supplied Jacobian; bounds, loss,
  stopping tolerances and floating-point precision are unchanged.
- Each fit owns reusable derivative buffers and its cached Jacobian; worker
  threads share no mutable calculation storage.

Analytic derivatives are selected automatically for step/linear extrapolation
with no S(Q) optimization or iterative optimization, using either transform
method and any of the three scattering sources. Fixed-background fits support
all normalization/correction combinations. Joint background fits support integral
and simple fit normalization. Spline/poly extrapolation, polynomial S(Q)
optimization, and joint background fits with multiple/container normalization
keep bounded finite differences. Nelder–Mead keeps its derivative-free path.
These fallbacks retain their existing behavior; this is not analytic coverage
of every supported calculation configuration.

## Numerical validation

- **32 of 32 benchmark fits pass the original strict Python tolerances**,
  including conditional errors: fitted values use atol 1e-5 / rtol 1e-6;
  errors use atol 1e-5 / rtol 1e-3. No tolerance was loosened.
- Maximum density difference from Python: **1.552099e-06 g/cm³**.
- Maximum relative difference in conditional density error: **2.2e-07**.
- Independent Python evaluation of the new fitted objective differs from the
  Python fit objective by at most **8.48e-11 relative**. The new/previous Rust
  stopping points differ in objective by at most **1.42e-09 relative**, including
  the previously accepted SiO₂ case.
- The former 0.000298 g/cm³ Python/Rust density discrepancy is absent with the
  analytic gradient. Fitted positions, evaluation counts and stopping reasons
  can change slightly; before/after fit results are not claimed bit-identical.
  All grids match, and pattern differences at the fitted positions are recorded.
- Repeated native fit tuples agree exactly across 1, 4 and 14 workers.
- A central-difference derivative matrix covers all three scattering sources,
  integral/simple/combined normalization, step/linear extrapolation, FFT/integral
  transforms, optional Lorch functions, no/iterative S(Q) optimization, both
  fitted parameters where supported, and parameter changes on reused buffers.
  Its 360 differentiated evaluations / 504 parameter columns agree with central
  differences within 2e-7 relative to the pattern scale. Packed primal outputs
  agree with ordinary outputs within 2e-10 × (1 + |value|).
- Packed-transform tests exercise scalar/native planners, FFT lengths 8–65,536,
  zero/Nyquist/endpoints, unequal signal amplitudes, shrinking/growing input,
  and transitions back to ordinary real-input FFTs.
- **528 Python tests, including the density objective/algorithm/background
  matrix, and 27 Rust tests pass.** Formatting and all-feature Clippy with
  warnings denied pass. The earlier 432-evaluation reference-pipeline matrix
  remains unchanged and passes its exact comparisons or matching-error checks.
- The rebuilt WASM engine passes 36 full-PDF and 24 density fixtures (290,300
  checked PDF numbers; maximum density/background parameter difference
  4.85e-7), ordered/error batch checks and 105 scattering-source checks. Browser
  response time and worker-pool throughput were not rebenchmarked here.

## Reproduce

Preserve the preceding FFT-optimized release wheel, then build and install the
new native wheel without updating dependencies:

```sh
uv run --with maturin maturin build --release --locked \
  --manifest-path rust/glassure-python/Cargo.toml --out target/density-analytic/optimized
uv pip install --no-deps --reinstall target/density-analytic/optimized/<wheel-filename>.whl
uv run --with threadpoolctl python rust/scripts/benchmark_analytic_density.py \
  --baseline-wheel target/density-analytic/baseline/<previous-wheel-filename>.whl
```

For stage counts, save the previous profiling executable before rebuilding:

```sh
cargo build --release --locked -p glassure-core --features profiling --example profile_density
# Run both saved/current executables, sequentially, with the same fixture:
<profile-executable> target/density-profile/SiO2_density.json 64 auto
<profile-executable> target/density-profile/Mg2SiO4_density.json 64 auto
```

Fixtures come from the first jobs of `benchmark_backend.workloads(64, 16)` and
`glassure.rust._density_request`. NumPy-to-JSON conversion is only for writing
untimed profiling fixtures. Binary and fixture hashes are recorded with stages.

API benchmark: 2026-10-19T15:17:50.142967+00:00 to 2026-10-19T15:19:36.735051+00:00.
Hardware: Apple M4 Pro, 14 physical cores (10 performance + 4 efficiency), 48 GiB;
Python 3.13.5, NumPy 2.5.1, SciPy 1.18.0, lmfit 1.3.4, rustc 1.93.0.

[API timings and numerical audit](density-analytic-results.json) ·
[FFT counts and profile](density-analytic-stages.json) ·
[Previous FFT report](PROFILE_DENSITY_REPORT.md)
