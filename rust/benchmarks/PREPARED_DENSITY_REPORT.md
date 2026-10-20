# Density fitting after preparation and buffer reuse

The subsequent [profile-guided FFT report](PROFILE_DENSITY_REPORT.md) compares
the next optimization against this prepared release. These measurements remain
the preparation/buffer-reuse snapshot.

Measured 2026-10-19T14:47:58.159340+00:00 to 2026-10-19T14:49:51.584549+00:00 on the Apple M4 Pro (14 cores, 48 GiB RAM).

Preparing the fixed calculation data once per fit and retaining numerical buffers
reduces single-fit time by 8.0% for SiO₂ and 5.4% for Mg₂SiO₄. Serial 16-fit
batches improve by 6.4% for both. At 14 workers the SiO₂ median improves by 7.7%;
Mg₂SiO₄ is effectively unchanged (0.4% slower, within the observed variation).
The improvement is modest for these workloads. No solver settings changed.

## Single fit

Median milliseconds per complete public NumPy API call, including preparation.

| Dataset | Python | Original Rust | Prepared Rust | Reduction in Rust time |
| --- | ---: | ---: | ---: | ---: |
| SiO₂ | 126.601 | 34.738 | 31.947 | 8.0% |
| Mg₂SiO₄ | 180.846 | 68.351 | 64.683 | 5.4% |

## Batches of 16 fits

Median milliseconds for the whole batch, including all returned fit tuples.

| Dataset | Workers | Python | Original Rust | Prepared Rust | Reduction in Rust time |
| --- | ---: | ---: | ---: | ---: | ---: |
| SiO₂ | 1 | 1851.510 | 497.163 | 465.257 | 6.4% |
| SiO₂ | 4 | 447.243 | 139.094 | 129.010 | 7.2% |
| SiO₂ | 14 | 234.938 | 73.958 | 68.239 | 7.7% |
| Mg₂SiO₄ | 1 | 2897.592 | 1077.997 | 1008.812 | 6.4% |
| Mg₂SiO₄ | 4 | 895.023 | 295.779 | 285.353 | 3.5% |
| Mg₂SiO₄ | 14 | 493.016 | 189.200 | 189.985 | -0.4% |

Python uses serial execution at one worker and spawned processes otherwise;
Rust uses native Rayon workers for batches. Both process/thread pools are warm.

| Dataset | Prepared Rust advantage over Python, single fit | Prepared Rust advantage over Python, 14-worker batch |
| --- | ---: | ---: |
| SiO₂ | 3.96× | 3.44× |
| Mg₂SiO₄ | 2.80× | 2.60× |

## Implementation

- Each density fit owns a prepared calculation. It validates and crops the input,
  aligns the background, evaluates scattering tables, and prepares fixed corrections,
  real-space/extrapolation grids, window factors and FFT interpolation coordinates once.
- Composition-to-atomic-density conversion retains the original operation order.
  Background-dependent intensity/normalization work is refreshed whenever the
  trial background scale changes; density-dependent quantities are recomputed.
- Intensity, normalization and S(Q) arrays, transform outputs, iterative correction
  arrays, FFT complex buffers and FFT scratch storage persist for the fit.
  All padded and imaginary FFT entries are reset before each execution.
- Every parallel fit has its own mutable workspace. No mutable cache is shared
  between jobs. Preparation is repeated for every new fit/configuration and is
  included in these timings; there is no cross-fit final-result cache.
- The ordinary standalone PDF calculation remains available as the reference
  implementation. Optimizer equations, derivatives, tolerances, evaluation limits,
  FFT lengths, interpolation order and floating-point expression order are retained.
- This is not an allocation-free fitter: nonlinear spline/polynomial helpers,
  least-squares factorizations, residual vectors and final owned outputs can still allocate.

## Numerical verification

- **32 original/prepared native fit results match bit for bit**, including density,
  errors, background, objective, evaluation count, termination and complete S(Q),
  F(r), g(r) results: **192 arrays / 258,048 array values**, plus scalar metadata.
- Warmups and every timing sample’s final Rust fit tuples match the original
  Rust results exactly across one, four and fourteen workers.
- A Rust differential test checks **432 evaluations across 144 configurations**:
  all three scattering sources; integral/simple-fit/combined-correction normalization;
  four extrapolation methods; integral/FFT transforms; iterative/polynomial S(Q)
  optimization; and repeated changes of density and background. Successful outputs
  agree bit for bit; reference nonconvergence errors are preserved.
- Buffer-address and padding-reset checks guard against reallocating the tested
  work arrays or retaining values from a preceding transform.
- **609 Python tests and 24 Rust tests pass**. Formatting and Clippy with warnings
  denied pass. Rebuilt WASM passes 36 PDF and 24 density fixtures, ordered/error
  batch checks and all three scattering-source checks.
- The previously accepted Python/Rust difference of 0.000298381 g/cm³ occurs in
  the same SiO₂ batch item; its relative objective difference remains 1.4041 × 10⁻⁹.
  The qualified benchmark policy is unchanged. There are no additional discrepancies.

## Measurement method

The original and prepared release extensions are loaded side by side. The original
binary is extracted from the saved wheel and checked against the prior density
report’s binary hash. Both use identical public `glassure.rust` adapter code.
Seven samples per mode run sequentially in shuffled order, interleaving Python,
original Rust and prepared Rust. Native warmups pass with JSON encoding/decoding
disabled. Timings include input snapshots, preparation, optimization and output
handling. Previous-result destruction is outside each timed call.

The fitting configuration is unchanged: fixed background within each fit, varying
0.98–1.02 across the batch; bounded least squares on g(r) over 0.1–1.0 Å; integral
normalization; Brown–Hubbell factors; linear extrapolation; FFT; and three S(Q)
iterations per evaluation. The single fit is the first batch item (scale 0.98).
These cases do not enable DAC/container corrections or simultaneous background fitting.

File I/O, initial model creation, imports and worker startup are excluded. Python
worker inputs are installed once, and timed calls exchange job indices and fit tuples.
A single numerical-library thread per Python process is requested; detected pools
are `[]`, which does not establish Apple libraries’ exact internal threading.
Other work/system services were active. Raw ranges, quartiles, measurement order
and pre/post load snapshots are retained. In particular, the Mg₂SiO₄ 14-worker
before/after timing ranges overlap; no multicore improvement is claimed there.

## Reproduce

Install the prepared release wheel, retain the original release wheel, and run:

```sh
uv run --with threadpoolctl python rust/scripts/benchmark_prepared_density.py \
  --baseline-wheel target/density-prepared/baseline/glassure_native-0.1.0-cp313-cp313-macosx_11_0_arm64.whl
```

The baseline wheel path above is a local retained artifact, not a published package.
Use the corresponding wheel for another platform. The harness verifies its binary
hash against the earlier report and records both binary hashes and current/old source
fingerprints. It also checks full native results before starting timed samples.

[Raw paired timings and complete-result checks](density-prepared-results.json) ·
[Original density benchmark](DENSITY_REPORT.md)
