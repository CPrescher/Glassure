# Density-fit benchmark: Rust/NumPy versus Python

The subsequent [preparation and buffer reuse comparison](PREPARED_DENSITY_REPORT.md)
measures the current fitter against this original implementation and verifies
unchanged numerical results. The measurements below remain the original snapshot.

Measured 2026-10-19T14:31:10.866753+00:00 to 2026-10-19T14:32:38.171850+00:00.

End-to-end density fitting through the native NumPy bridge is faster in both
tested datasets. Single-fit speedups are 3.67× for SiO₂ and 2.69× for Mg₂SiO₄.
For a batch of 16 fits at 14 workers, Rust is 3.00× and 2.51× faster than
Python’s warmed process pool. These are local warm measurements on an Apple
M4 Pro with 10 performance cores, 4 efficiency cores and 48 GiB RAM.

## Single fit

Median milliseconds per full fit, returning the ordinary four-value fit tuple.

| Dataset | Python | Rust via NumPy | Speedup |
| --- | ---: | ---: | ---: |
| SiO₂ | 128.270 | 34.968 | 3.67× |
| Mg₂SiO₄ | 184.961 | 68.822 | 2.69× |

## Batches of 16 independent fits

Median milliseconds for the entire batch, including all returned fit tuples.

| Dataset | Python serial | Rust serial | Python 4 processes | Rust 4 threads | Python 14 processes | Rust 14 threads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SiO₂ | 1740.998 | 499.060 | 420.280 | 135.755 | 201.434 | 67.247 |
| Mg₂SiO₄ | 2988.952 | 1075.329 | 785.957 | 285.140 | 454.154 | 180.637 |

| Dataset | Rust scaling, 1 → 14 threads | Rust advantage over Python at 14 workers | Rust 14 versus serial Python |
| --- | ---: | ---: | ---: |
| SiO₂ | 7.42× | 3.00× | 25.89× |
| Mg₂SiO₄ | 5.95× | 2.51× | 16.55× |

The last column combines implementation speed with multicore execution. The
middle column compares both implementations with 14 application workers.

## Fitting configuration

- Same float64 SiO₂ and ambient Mg₂SiO₄ data/background files as the PDF benchmark.
- Bounded least squares for density, minimizing low-r g(r) over 0.1–1.0 Å.
- The background scale stays fixed within each fit. It varies independently
  from 0.98 to 1.02 across the 16 jobs; the single fit is the first job (0.98).
  This benchmark does not measure simultaneous density/background refinement.
- Integral normalization, Brown–Hubbell factors, linear extrapolation, FFT,
  and three S(Q) optimization iterations per evaluation with a 1.4 Å cutoff.
- Starting densities are 2.2 g/cm³ for SiO₂ and 2.9 g/cm³ for Mg₂SiO₄. Q ranges
  are 1–17 and 1–20 Å⁻¹; the real-space grid extends to 10 Å in 0.01 Å steps.
- The DAC/container/Klein–Nishina combination from the separate full-PDF
  benchmark is not enabled in these integral-normalization fitting cases.

## Timing boundary and reproducibility

Timings call `glassure.optimization.optimize_density` and
`glassure.rust.optimize_density` / `optimize_density_batch`. Native timings
include request preparation, binary NumPy input snapshots, GIL transitions,
the entire optimization, native output handling and the returned tuple.
There is no numerical JSON conversion; native warmups also pass with Python
`json.dumps` and `json.loads` disabled. Scalar fit tuples return to Python.

Python multicore uses persistent spawned process pools, with the prepared
inputs installed once per worker. Timed calls send job indices and return
fit tuples using binary pickle transfer. A shallow Python data wrapper prevents
the reference fitter’s background-scale mutation from changing later starts.

Seven samples per path in reproducibly shuffled order. Small calls average
a fixed repetition count calibrated toward 100 ms (maximum 500 repeats). Tables
show median sample averages. File loading, initial configuration creation,
imports, pool startup and previous-result destruction are outside warm timing.
Python pool setup took 2.30 s for 4 workers and 8.01 s for 14; neither is included above.

One numerical-library thread per Python process was requested through the
environment and threadpoolctl. Detected pools were `[]`, which does not prove
Apple libraries’ exact internal thread counts. Other work/system services were
active; no processes were stopped. Sample ranges and quartiles are retained.
A complete fit can follow a different evaluation path in the two solvers, so
these ratios describe end-to-end fits rather than equal-count objective kernels.

## Agreement and the accepted qualification

Warmups and every sample’s final output are checked. Rust fit tuples agree
exactly across one, four and fourteen workers and across checked repetitions.
Both single-fit cases and all 16 Mg₂SiO₄ batch jobs meet the strict parameter
comparison. The SiO₂ batch retains the previously audited qualification at
background scale 0.9906666667:

- Python density: 9.4091271703 g/cm³; Rust: 9.4088287893 g/cm³.
- Absolute difference: 0.000298381 g/cm³, or 0.00317%.
- Conditional density error is about 0.598 g/cm³ in both implementations.
- Evaluating both fitted points through the same Python objective gives a
  relative objective difference of 1.4041 × 10⁻⁹.

For benchmarking, only this case/background scale may exceed the previous
strict density tolerance. Its absolute density difference must remain ≤0.0003
g/cm³ and relative objective difference ≤10⁻⁸. Background and error-field checks
keep their prior tolerances. Other fits retain the strict checks. The original
strict failure remains recorded as such, together with the accepted qualification.
No solver settings, equations, production tolerances or scientific tests changed.

These fits compare implementations; their numerical fitted densities are not
independent validation of a physical density. Source/data and installed release
extension hashes match the preceding PDF benchmark and remained unchanged.

## Reproduce and inspect

After building/installing the release native wheel and running the preceding
PDF benchmark to establish its source/binary fingerprints:

```sh
uv run --with threadpoolctl python rust/scripts/benchmark_density.py
```

Python 3.13.5, NumPy 2.5.1, SciPy 1.18.0, lmfit 1.3.4;
native distribution 0.1.0; rustc 1.93.0 (254b59607 2026-01-19).

[Raw samples, settings, hashes and validation](density-results.json) ·
[Original 32-fit audit](density-parity.json) ·
[PDF benchmark](BACKEND_REPORT.md)
