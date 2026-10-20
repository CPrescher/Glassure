# Profile-guided FFT optimization for density fitting

Paired API benchmark: 2026-10-19T15:03:05.514905+00:00 to 2026-10-19T15:04:57.373488+00:00.

The profile identifies FFT execution as the main cost: **96.7–96.8% of native
fit time** before this change. Preparation is below 0.5%, normalization below
0.3%, and output interpolation below 0.4%. Optimizing those smaller stages
would have little effect on the total for these workloads.

The fitter now uses an immutable-input FFT path when the planner’s memory
requirements permit it. This removes the ARM in-place wrapper’s full-result
copy back and avoids repeatedly clearing unchanged real-input padding.
The FFT length, precision, mathematical algorithm, solver settings and result
values stay the same. Measured savings are **5–7% for single fits** and about
**7% for 16-fit batches with 14 workers** on this M4 Pro.

## Profile breakdown

Each mode runs 64 warmed native fits in the same instrumented release executable.
Stages are inclusive/nested, so their percentages must not be added together.
The `inplace` diagnostic reproduces the previous FFT execution path; `auto` uses
the new selection. Profiling excludes the Python bridge. JSON fixture loading
happens once before the warmup and fit loop.

| Dataset | Mode | Native ms/fit | FFT kernel | Input filling/clearing | Preparation | Normalization |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| SiO2 | inplace | 31.670 | 96.73% | 1.87% | 0.17% | 0.15% |
| SiO2 | auto | 29.536 | 98.43% | 0.09% | 0.18% | 0.16% |
| Mg2SiO4 | inplace | 64.090 | 96.78% | 1.61% | 0.45% | 0.24% |
| Mg2SiO4 | auto | 58.821 | 98.19% | 0.13% | 0.48% | 0.26% |

These particular single-fit inputs perform 308 FFTs per SiO₂ fit and 133
larger FFTs per Mg₂SiO₄ fit, including iterative S(Q) optimization, numerical
Jacobian evaluations and final output generation. After the change the FFT
kernel still accounts for roughly 98% of native time. The remaining computation
is therefore substantial; this is an incremental improvement, not a new
order-of-magnitude speedup.

## Single fits through the NumPy bridge

Median milliseconds, seven shuffled warm samples. These normal release wheels
have profiling disabled. Input snapshots, preparation and result handling are timed.

| Dataset | Python | Previous prepared Rust | Optimized Rust | Reduction in Rust time |
| --- | ---: | ---: | ---: | ---: |
| SiO₂ | 116.169 | 31.662 | 29.577 | 6.6% |
| Mg₂SiO₄ | 176.251 | 63.038 | 59.663 | 5.4% |

## Batches of 16 fits

Median milliseconds for the whole batch, returning all fit tuples.

| Dataset | Workers | Python | Previous prepared Rust | Optimized Rust | Reduction in Rust time |
| --- | ---: | ---: | ---: | ---: | ---: |
| SiO₂ | 1 | 1766.008 | 466.435 | 435.039 | 6.7% |
| SiO₂ | 4 | 443.387 | 130.249 | 124.232 | 4.6% |
| SiO₂ | 14 | 221.789 | 70.704 | 66.058 | 6.6% |
| Mg₂SiO₄ | 1 | 3168.302 | 1050.440 | 985.168 | 6.2% |
| Mg₂SiO₄ | 4 | 912.300 | 293.656 | 277.640 | 5.5% |
| Mg₂SiO₄ | 14 | 507.949 | 190.876 | 177.147 | 7.2% |

Python uses spawned processes for multicore batches; Rust uses Rayon threads.
Both pools are persistent and warmed. Worker startup, file loading and initial
model creation are excluded. Prepared inputs reside in each Python worker;
timed calls send job indices and return fit tuples. There is no numerical JSON
conversion in either Rust API path. Native warmups also pass with Python’s JSON
encoding and decoding disabled.

The before/after native extensions load side by side. The previous prepared
wheel is verified against its recorded extension hash. Paths run sequentially
in shuffled order; the record retains all samples, ranges, quartiles, measurement
order, source/binary hashes and pre/post process snapshots. Other work and system
services were active. Occasional batch outliers are retained, not discarded.

## Implementation and numerical checks

- RustFFT 6.4.1’s ARM in-place wrapper computes into scratch and copies the full
  result back. Its immutable path can use that same storage as the final output.
  This is an entry-point/storage optimization, not a smaller FFT or lower precision.
- The immutable path is selected only when input + output + required scratch
  uses no more complex-number storage than the previous input + scratch.
  Other planners retain the existing in-place fallback.
- Immutable real input stays real and padded with zeros. A changing prefix is
  overwritten; a formerly active tail is cleared if the input shrinks. Mutable
  fallback execution retains its full reset. Each fit owns its buffers.
- New tests compare complete complex output bits with the prior FFT path for
  scalar and native planners, eight sizes from 4 to 65,536, shrinking/growing
  prefixes and zero input. Buffer addresses and the storage bound are checked.
- **32 complete fits match the previous prepared release bit for bit**: fitted
  values, errors, objectives, evaluation counts, stopping decisions and all
  **192 output arrays / 258,048 array values**. Repeated timing outputs agree
  exactly across one, four and fourteen workers.
- **609 Python tests and 25 Rust tests pass**. Formatting and Clippy with all
  features and warnings denied pass. WASM passes 36 PDF/24 density fixtures
  and ordered/error batch checks. The existing 432-evaluation differential
  matrix continues to match the reference calculation or its error result.
- The previously accepted 0.000298381 g/cm³ Python/Rust stopping-point difference
  is unchanged. No new discrepancy was admitted and no tolerance was loosened.

All reported native timings are local macOS ARM64 results. Other platforms
retain the planner-dependent selection and require their own performance measurements.

## Reproduce

Build and install the current release native wheel, preserving the previous
prepared release wheel from the preceding report:

```sh
uv run --with threadpoolctl python rust/scripts/benchmark_prepared_density.py \
  --baseline-wheel target/density-profile/baseline/glassure_native-0.1.0-cp313-cp313-macosx_11_0_arm64.whl \
  --baseline-report rust/benchmarks/density-prepared-results.json \
  --output rust/benchmarks/density-profile-results.json
```

The baseline wheel is a retained local artifact. The report contains its hash;
use the corresponding wheel on another platform. For native stage profiling:

```sh
cargo build --release --locked -p glassure-core --features profiling --example profile_density
target/release/examples/profile_density target/density-profile/SiO2_density.json 64 inplace
target/release/examples/profile_density target/density-profile/SiO2_density.json 64 auto
```

Repeat with `Mg2SiO4_density.json`. The fixtures are ordinary DensityRequest JSON
created from the same benchmark jobs using `benchmark_backend.workloads(64, 16)`
and `glassure.rust._density_request`, converting NumPy arrays only when writing
the untimed fixture. Profiling is opt-in through the `profiling` Cargo feature;
its timers and diagnostic FFT override are compiled out of standard builds.

The fitting configuration remains fixed-background least squares on low-r g(r),
integral normalization, Brown–Hubbell factors, linear extrapolation, FFT and three
S(Q) optimization iterations. Background scales vary 0.98–1.02 across batches;
the profiled/single job uses 0.98. This does not benchmark joint background fitting.

[Stage timings](density-profile-stages.json) · [Paired API timings and checks](density-profile-results.json) ·
[Previous preparation/buffer report](PREPARED_DENSITY_REPORT.md)
