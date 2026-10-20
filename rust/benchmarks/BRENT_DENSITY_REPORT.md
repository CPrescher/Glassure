# Brent versus analytic TRF for density fitting

**Brent is not consistently faster.** Starting from a local bracket, it reduces
SiO₂ single-fit time by 14%, but increases Mg₂SiO₄ single-fit time by 66%. With
14 workers and 16 fits, the SiO₂ gain is only 4% (sample ranges overlap), while
Mg₂SiO₄ takes 76% longer. TRF remains the default.

A bounded Brent search across the entire allowed density interval reaches a
worse minimum in **20 of the 32 benchmark jobs**. This agrees with independent
Python/SciPy results. The one-dimensional objective has multiple minima; it
does not satisfy the unimodality assumption needed for a reliable full-interval
scalar search. The locally bracketed version reaches the nearby low-density
minimum in all 32 jobs.

## Single fits through the NumPy bridge

Median milliseconds, seven shuffled warm samples on the M4 Pro. Both solvers
include preparation, input snapshots, result handling and conditional error
estimation. Native numerical arrays do not pass through JSON.

| Dataset | Python TRF | Rust TRF | Rust Brent, local bracket | Change from Rust TRF |
| --- | ---: | ---: | ---: | ---: |
| SiO₂ | 108.823 | 16.399 | 14.103 | -14.0% time |
| Mg₂SiO₄ | 164.890 | 31.235 | 51.818 | +65.9% time |

## Batches of 16 fits

Python uses warmed spawned process pools; Rust uses warmed Rayon thread pools.
Worker startup, file loading and initial model creation are excluded. Python
workers retain inputs; timed calls send indices and return fit tuples. BLAS
threads are limited to one. No result cache spans separate fits or jobs.

| Dataset | Workers | Python TRF | Rust TRF | Rust Brent, local bracket | Change from Rust TRF |
| --- | ---: | ---: | ---: | ---: | ---: |
| SiO₂ | 1 | 1640.883 | 260.571 | 231.885 | -11.0% time |
| SiO₂ | 4 | 452.396 | 74.813 | 72.627 | -2.9% time |
| SiO₂ | 14 | 192.240 | 34.486 | 33.126 | -3.9% time |
| Mg₂SiO₄ | 1 | 3126.545 | 509.300 | 858.100 | +68.5% time |
| Mg₂SiO₄ | 4 | 795.416 | 140.030 | 241.222 | +72.3% time |
| Mg₂SiO₄ | 14 | 436.267 | 82.692 | 145.419 | +75.9% time |

The benchmark retains the previous scientific settings: fixed background within
each fit, low-r g(r) objective on 0.1 < r < 1 Å, integral normalization,
Brown–Hubbell factors, linear extrapolation, FFT and three iterative S(Q)
correction steps. Each batch varies background scale from 0.98 to 1.02 across
16 jobs. The single fit is the first job, with scale 0.98. Initial densities are
2.2 g/cm³ (SiO₂) and 2.9 g/cm³ (Mg₂SiO₄).

All native solvers use the same physical bounds, [1e-12, 100] g/cm³, and the same
500-evaluation budget. TRF retains its existing tolerances. Brent uses absolute
density tolerance 1e-8 plus the usual square-root-machine-precision relative
floor. These stopping rules are not equivalent to TRF’s objective/gradient/step
criteria; their final densities need not match exactly. All bracket-search and
conditional-error evaluations are included in the Brent timings.

## Evaluation counts explain the performance

TRF already obtains the analytic density derivative in the same complex FFTs
as the value. Avoiding derivatives therefore saves little per evaluation. The
number of expensive pipeline evaluations dominates the comparison.

| Dataset | Method | Pipeline evaluations | FFT calls including final output | Profile ms/fit |
| --- | --- | ---: | ---: | ---: |
| SiO₂ | TRF | 23 | 168 | 16.486 |
| SiO₂ | Brent, local bracket | 20 | 147 | 13.886 |
| SiO₂ | Brent, full interval (different minimum) | 16 | 119 | 11.384 |
| Mg₂SiO₄ | TRF | 9 | 70 | 31.506 |
| Mg₂SiO₄ | Brent, local bracket | 16 | 119 | 51.511 |
| Mg₂SiO₄ | Brent, full interval (different minimum) | 15 | 112 | 48.693 |

Each pipeline has seven transforms: three forward/backward S(Q) correction
pairs plus the final forward transform. The counted pipeline evaluations include
one final derivative evaluation for Brent’s conditional covariance. A separate
ordinary final-output pipeline is included in FFT counts and timing, matching
the existing TRF behavior. Stage profiling runs 64 warmed fits per method and
case; timers are compiled out of the API benchmark wheels.

## Local minima and numerical results

![Density objective curves and optimizer stopping points](density-brent-objectives.png)

These curves sample the ordinary native PDF pipeline after benchmarking. The
blue TRF and green local-Brent points nearly coincide. The orange full-interval
Brent points lie in different, higher minima for these representative jobs.
The numerical source for the figure is retained in `density-brent-objectives.json`.

| Dataset, first job | TRF density | Local Brent density | Absolute difference |
| --- | ---: | ---: | ---: |
| SiO₂ | 9.676537643 | 9.676024225 | 0.000513418 g/cm³ |
| Mg₂SiO₄ | 4.391068386 | 4.391087564 | 0.000019178 g/cm³ |

- Maximum density shift over 32 locally bracketed fits: **0.000513418013 g/cm³**
  (**0.00531%** relative to TRF), or **0.0008637** of the conditional
  density standard error.
- Local Brent gives slightly lower objectives in all 32 jobs: relative changes
  range from **-1.63e-08 to -8.22e-11**.
- Maximum relative change in conditional density error: **3.66e-05**.
- The 32 local-Brent fits do **not** pass the preceding strict comparison to
  Python TRF (density atol 1e-5 / rtol 1e-6). This is recorded explicitly; no
  tolerance was widened to hide the different stopping points.
- All 64 Brent results (local and full-interval) independently match the
  corresponding Python/SciPy scalar fits within the original strict density
  tolerance. Scalar objectives agree within rtol 1e-9 / atol 1e-14. Python
  evaluates the scientific calculation independently; no Rust answer or fitted
  bracket is supplied to SciPy.
- The locally bracketed SciPy reference starts from the supplied density and
  a 10% higher density, then uses its own bracketing and Brent implementation.
  Its bracketing path and evaluation count can differ from the native method.
- All 32 TRF fit tuples, objective values, evaluation counts and stopping reasons
  exactly retain the previous analytic-TRF benchmark results.
- Native repeated results agree exactly across 1, 4 and 14 workers.

## Full-interval Brent diagnostics

The full-interval search ignores the starting density when choosing its initial
probe. It is an opt-in diagnostic, not a replacement for the local TRF fit.
It selects worse minima in 4/16 SiO₂ jobs and 16/16 Mg₂SiO₄ jobs.

| Dataset, first job | Full-interval density | Objective / TRF objective | Full-interval ms |
| --- | ---: | ---: | ---: |
| SiO₂ | 64.712837 | 18.153× | 11.353 |
| Mg₂SiO₄ | 28.957143 | 1.755× | 49.196 |

Full-interval batch timings remain in the raw report. They must be interpreted
with the recorded minima and objective differences, rather than as timings for
equivalent solutions. Neither the locally bracketed nor full-interval Brent
method establishes a global minimum on an arbitrary multimodal objective.

## API and validation

Both scalar variants are available in the shared standalone Rust/CLI/WASM core
and the optional NumPy adapter. They require a fixed background:

```python
from glassure import rust

fit = rust.optimize_density(
    data_config, calculation_config,
    method="gr", min_range=(0.1, 1.0),
    vary_bkg_scaling=False,
    optimization_method="brent_local",
)
```

Use the same option with `optimize_density_batch` or `optimize_density_sweep`.
`brent_local` probes ±0.1 × max(|initial density|, 1), follows the lower side
with golden-ratio expansion until it brackets a local minimum or reaches a
physical bound, and then uses safeguarded parabolic interpolation with
golden-section fallback. Repeated scalar probes are cached within one fit.
Bracketing is included in its budget and timing; no prior TRF answer is used.
`brent` applies bounded Brent directly to the complete physical interval.
Both retain least-squares conditional error estimates, using the existing
analytic Jacobian when supported and bounded differences otherwise.

- **532 Python tests and 31 Rust tests pass.** New tests cover known scalar
  minima, physical endpoints, flat objectives, budgets and error propagation,
  downhill local bracketing, independent SciPy/native fit comparisons,
  conditional errors checked by central differences, and ordered multicore
  results. Existing TRF, derivative, correction and reference-pipeline tests pass.
- Formatting and all-feature Clippy with warnings denied pass.
- Rebuilt WASM passes the existing 36 PDF / 24 density fixtures, 290,300 PDF
  numbers, ordered/error batches and 105 scattering checks. Six additional
  TRF/Brent fixtures agree with native results (maximum density difference
  1.62e-10 g/cm³), with scalar background/budget validation and ordered
  batches/sweeps. Browser latency and worker-pool throughput were not retimed.
- The existing Python optimizer and the Rust default remain unchanged.

## Reproduce

Build and install the release wheel without changing dependencies, then run:
```sh
uv run --with threadpoolctl python rust/scripts/benchmark_brent_density.py
node rust/scripts/verify_brent.mjs
uv run --with threadpoolctl --with matplotlib python rust/scripts/plot_brent_density.py
```

The benchmark emits untimed native/WASM fixtures under `target/density-brent/`.
For transform counts, build `profile_density` with the `profiling` feature and
run each emitted request 64 times with `auto`; record all methods sequentially.
Native API paths are warmed with JSON encoding and decoding disabled. SciPy
cross-checks, objective sampling and plotting run outside timed measurements.
All medians, individual samples, ranges, quartiles, randomized order, input
configurations, per-fit numerical checks, process snapshots and source/binary
hashes are retained. Background system activity was present and outliers were
retained. These are local macOS ARM64 results.

API run: 2026-10-19T15:32:55.120474+00:00 to 2026-10-19T15:34:55.735054+00:00.
Hardware: Apple M4 Pro, 14 physical cores (10 performance + 4 efficiency),
48 GiB; Python 3.13.5, NumPy 2.5.1, SciPy 1.18.0, lmfit 1.3.4.

[Timing and numerical audit](density-brent-results.json) ·
[FFT counts and stage profile](density-brent-stages.json) ·
[Objective source data](density-brent-objectives.json) ·
[Previous analytic-TRF report](ANALYTIC_DENSITY_REPORT.md)
