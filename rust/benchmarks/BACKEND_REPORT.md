# Rust/NumPy versus Python — full PDF pipeline

Measured 2026-10-19T14:18:41.948682+00:00 to 2026-10-19T14:22:52.408179+00:00.

The public native NumPy backend is faster in all four measured workloads. The
combined pipeline is 16.1–17.6× faster for one calculation. For 64 independent
calculations at 14 workers it is 13.3–15.8× faster than a warmed Python process
pool. These are warm local measurements on an Apple M4 Pro (10 performance and
4 efficiency cores, 48 GiB RAM); they do not establish a universal speed ratio.

## Single calculation

Median milliseconds per complete call, including the normal Glassure result.

| Workload | Python | Rust via NumPy | Python / Rust |
| --- | ---: | ---: | ---: |
| SiO₂ basic | 0.854 | 0.175 | 4.88× |
| SiO₂ all corrections + optimization | 38.033 | 2.364 | 16.09× |
| Mg₂SiO₄ basic | 2.874 | 0.843 | 3.41× |
| Mg₂SiO₄ all corrections + optimization | 261.151 | 14.823 | 17.62× |

## Batches of 64 calculations

Milliseconds for the entire ordered batch, including all returned results.

| Workload | Python serial | Rust serial | Python 4 processes | Rust 4 threads | Python 14 processes | Rust 14 threads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SiO₂ basic | 57.508 | 11.355 | 17.428 | 4.137 | 10.525 | 3.246 |
| SiO₂ all corrections + optimization | 2485.505 | 151.924 | 628.976 | 40.719 | 249.225 | 18.706 |
| Mg₂SiO₄ basic | 185.093 | 52.745 | 51.909 | 16.587 | 23.694 | 10.146 |
| Mg₂SiO₄ all corrections + optimization | 16879.077 | 947.292 | 4272.686 | 245.387 | 1647.015 | 104.277 |

| Workload | Rust 14 / Rust 1 speedup | Rust advantage over Python 14 processes | Rust 14 versus serial Python |
| --- | ---: | ---: | ---: |
| SiO₂ basic | 3.50× | 3.24× | 17.71× |
| SiO₂ all corrections + optimization | 8.12× | 13.32× | 132.87× |
| Mg₂SiO₄ basic | 5.20× | 2.34× | 18.24× |
| Mg₂SiO₄ all corrections + optimization | 9.08× | 15.79× | 161.87× |

The last column combines a faster implementation with parallel execution. The
middle column compares both implementations using 14 application workers.

## Workloads and measurement boundary

- Both implementations receive the same prepared float64 NumPy data, background
  and configurations from the repository’s SiO₂ and ambient Mg₂SiO₄ datasets.
  Each batch varies background scale from 0.98 to 1.02. A single call is the
  first batch item, with scale 0.98. No final results are cached.
- Basic: background subtraction, Brown–Hubbell scattering factors, incoherent
  scattering, high-Q fit normalization above 5 Å⁻¹, linear extrapolation and FFT.
- Combined: additionally multiple scattering, carbon container, DAC Soller
  correction (40 → 20 µm), Klein–Nishina correction at 0.29 Å, smoothing-spline
  extrapolation, Lorch modification and three S(Q) optimization iterations
  with a 1.4 Å cutoff. Factors and corrections are calculated inside each call.
- Q ranges are 1–17 Å⁻¹ for SiO₂ and 1–20 Å⁻¹ for Mg₂SiO₄. The real-space
  grid runs from approximately zero to 10 Å in 0.01 Å steps.
- Rust timings call `glassure.rust.calculate_pdf` or `calculate_batch`. They
  include scalar extraction, owned binary input snapshots, GIL transitions,
  computation, NumPy output ownership transfer, and Result/Pattern/config
  wrapping. They contain no numerical JSON or Python-float-list conversion.
  Warmups also pass with `json.dumps` and `json.loads` disabled.
- Python timings call `glassure.calc.calculate_pdf`. Python multiprocessing
  uses persistent spawned processes with prepared inputs installed once per
  worker; only job indices and returned Results cross the timed process boundary.
  Output NumPy arrays use binary pickle transfer. Inputs are not repeatedly
  serialized for each job. This gives Python a favorable persistent-worker setup.
- Seven samples per path, measured sequentially in reproducibly shuffled order.
  Small calls average a fixed repeat count calibrated toward 100 ms per sample
  (maximum 500 repeats); large batches use one repeat. Tables show the median
  sample average. Previous-result destruction is outside the timed interval.
- File I/O, initial configuration creation, imports and pool startup are outside
  warm timing for both implementations. Python pool initialization took
  2.18 s for 4 workers and 7.43 s for 14; these costs are excluded above.
- One numerical-library thread per Python process was requested through
  environment variables and threadpoolctl. Detected pools were `[]`; this does
  not independently verify Apple numerical libraries’ exact internal thread count.
- This was not an isolated machine. Pre/post process snapshots are recorded in
  the raw data. Background activity and scheduling caused occasional outliers;
  raw samples, quartiles and ranges are retained rather than discarded.

## Numerical checks

Every coordinate and value of S(Q), F(r) and g(r) is checked against Python
for warmup and every sample’s final output at `atol=1e-8, rtol=1e-8`.
The largest absolute difference is 3.1761e-09.
Rust results agree exactly between one, four and fourteen workers and across
the checked repetitions. Source and extension hashes remained unchanged during
the run. All eight PDF timing scenarios pass.

## Supplemental density-fit qualification

Density fitting was audited separately before accepting its batch timings.
For each material, 16 background scales were tested using integral normalization,
three S(Q) iterations and a low-r g(r) least-squares objective with fixed background.
31 of 32 fits pass the existing strict parameter/error tolerances. One SiO₂ fit
at background scale 0.9906666667 exceeds the fitted-parameter tolerance:

- Python density: 9.4091271703 g/cm³; Rust: 9.4088287893 g/cm³.
- Absolute difference: 0.000298381 g/cm³ (0.00317%).
- Conditional density error is about 0.598 g/cm³ in both implementations.
- Evaluating both fitted points through the same Python objective gives only
  a 1.40 × 10⁻⁹ relative objective difference. Rust stops on cost tolerance.

This is consistent with different stopping positions near a shallow minimum,
but the strict parameter comparison remains failed. No tolerances or solver
equations were changed. Density-fit timings are excluded from these speed tables.
The numerical fit is a solver comparison, not a claim about the physical density.
See [density-parity.json](density-parity.json) for all 32 comparisons.

After review, the small difference was accepted for benchmarking. Single-fit and
multicore density timings are now available in the separate
[density benchmark report](DENSITY_REPORT.md), with the qualification retained.

## Reproduce

Build and install the release native wheel using [the backend guide](../README.md), then:

```sh
uv run --with threadpoolctl python rust/scripts/benchmark_backend.py
uv run --with threadpoolctl python rust/scripts/check_density_benchmark.py
```

The optional benchmark flag `--include-density` requires strict parameter parity
and currently stops at the qualified SiO₂ density case described above.

Python 3.13.5, NumPy 2.5.1, SciPy 1.18.0, lmfit 1.3.4;
native distribution 0.1.0; rustc 1.93.0 (254b59607 2026-01-19).

Raw timing samples, inputs/settings, source/data hashes and the installed extension
hash are in [backend-results.json](backend-results.json). These measurements use
the current dirty working tree, not solely its Git HEAD; the hashes identify it.
No browser, WASM, server or network latency is measured here.
