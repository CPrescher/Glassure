# Local validation — 2026-10-19

Environment: Apple Silicon, macOS 26.6.2, CPython 3.13.5, release Rust/WASM
builds. These results apply to this local implementation. The configured CI
matrix and package publication statements below initially describe preparation
snapshots. The later registry release is recorded separately; the web app was
not deployed.

## Native implementation

| Check | Result |
| --- | --- |
| `uv run pytest tests -q` | 528 passed: existing Python tests and 401 optional Rust backend comparisons |
| `uv run pytest prototypes/rust-wasm/python/tests -q` | 81 passed: legacy JSON, parallel and NumPy adapter contracts |
| `cargo test --locked --all-targets` | 22 passed: core, standalone operations and CLI |
| `cargo fmt --all --check` | Passed |
| `cargo clippy --locked --workspace --all-targets -- -D warnings` | Passed |
| `cargo build --locked --release --bins --examples` | Passed without building the Python extension |

The Python comparisons cover every supported scattering state from all three
sources, standalone transforms and their inverses, normalization, extrapolation,
S(Q) optimization, corrections, peak models, transfer functions, smoothing and
rebinning. Density fitting covers 24 test cases: three objectives, two algorithms,
fixed/variable background and two datasets.
Nonconvergence is checked as an explicit error. Buffer ownership, unchanged caller
inputs, parallel ordering and sweep results are checked as well.

The compiled library example and CLI were exercised on `tests/data/SiO2.xy`
and its background (2.2 g/cm³, 1–17 Å⁻¹). Both produced identical arrays:
498 S(Q) points and 1001 points each for F(r) and g(r). Compared with the
Python calculation, maximum absolute errors were:

| Array | Maximum absolute error |
| --- | ---: |
| S(Q) | 3.33 × 10⁻¹⁵ |
| F(r) | 1.07 × 10⁻¹³ |
| g(r) | 1.77 × 10⁻¹² |

The CLI ran with an empty environment except `PATH=""` and
`PYTHONHOME="/nonexistent"`. Automated CLI tests also exercise the full PDF
pipeline and Xraylib factors under that environment. The Rust executable does
not invoke Python. This is distinct from the optional Python API, whose models
and wrappers are ordinary Python objects.

## WebAssembly

The rebuilt compatibility WASM crate uses `glassure-core` directly. Node checks
exercise the same byte ABI used by the browser:

| Check | Result |
| --- | --- |
| `node prototypes/rust-wasm/scripts/verify_wasm.mjs` | 24 PDF requests, 209 factor batches, 10 invalid requests; 291,139 numerical comparisons passed |
| `node prototypes/rust-wasm/scripts/verify_full.mjs` | 36 full PDF cases, 24 density cases passed; 290,300 pattern values compared |
| `node prototypes/rust-wasm/scripts/verify_parallel.mjs` | Ordered batches/sweeps, errors, native-thread rejection and fatal-trap handling passed |
| `node rust/scripts/verify_sources.mjs` | All three sources, 105 comparisons passed; maximum absolute error 1.93 × 10⁻¹³ |

The full-pipeline WASM fixtures had maximum absolute pattern error
2.31 × 10⁻⁷ and density/background parameter error 5.54 × 10⁻⁷. The pattern
maximum comes from polynomial extrapolation (fixture absolute tolerance 10⁻⁶).
Density tolerances are 10⁻⁵ absolute plus 10⁻⁶ relative for fitted parameters,
and 10⁻³ relative for conditional errors. One density fixture expects an
evaluation-budget error rather than accepting a nonconverged fit.

The committed `fixtures/scattering-sources.json` records current Python reference
values for SiO₂, including the low-Q Xraylib extension. The other WASM fixtures
and their generators remain in the original local prototype checkout; this
release branch retains only the compatibility crate needed to build the byte ABI.
The Node commands above record historical validation, rather than checks that can
be rerun from this release checkout. Current CI checks core and compatibility
WASM compilation; browser adapters are distributed separately.
They establish ABI and numerical agreement, not new browser response-time
measurements or a browser UI end-to-end test.

## Packaging and limits (prepublication snapshot)

The subsequent Cargo distribution check prepares `glassure-core` and
`glassure-cli` 0.1.0 with Rust 1.93 minimum metadata. Both `.crate` archives
passed Cargo's verified packaging using its companion-package staging registry.
The archives were then extracted outside the checkout: 31 core tests, four
rustdoc examples and five standalone CLI tests passed. Native and WASM rustdoc
built with warnings denied, and the extracted core compiled for WASM with all
features. Embedded Xraylib text/binary hashes matched their packaged provenance.
A fresh Rust consumer calculated 1001 g(r) points. The extracted CLI installed
in a temporary location and ran with empty PATH/nonexistent PYTHONHOME.

The isolated CLI test/install temporarily patched its unpublished core dependency
to the extracted companion archive; the delivered manifest retains its normal
versioned registry dependency. This is not a registry-installation claim.
The local check used `--allow-dirty` and records that provenance in the archives.
`target/package-validation/report.json` records final archive sizes, SHA-256
hashes and checks. Registry publication and the registry-connected publish dry
run remain unverified: the attempted offline dry run required an HTTP request.
CI package checks are configured but have not run remotely. See
[RELEASING.md](RELEASING.md) for reproduction and release gates.

- The core's Cargo source package was built and verified locally.
- The native wheel built for CPython 3.13 on macOS ARM64 and was installed in
  the development environment. A native source distribution also built into a
  wheel through its PEP 517 build configuration.
- Native wheel metadata contains the MIT license and SciPy/Xraylib notices.
- Other operating systems and interpreter versions await their CI jobs.

This is implementation agreement with the existing reference, not independent
validation of the scientific model. The API differences and numerical limits
are listed in [README.md](README.md). Historical benchmark snapshots are retained.
Subsequent timings and an additional density-fit qualification are recorded in the
[backend benchmark report](benchmarks/BACKEND_REPORT.md).
Density-fit timings with the accepted qualification are recorded in the
[density benchmark report](benchmarks/DENSITY_REPORT.md).

## Prepared density fitting

After adding per-fit preparation and reusable numerical/FFT buffers, 609 Python
tests and 24 Rust tests pass. A 432-evaluation differential matrix checks exact
agreement with the ordinary calculation and matching nonconvergence errors.
All 32 benchmark fits match the original release binary bit for bit, including
192 output arrays (258,048 values), objective values, evaluation counts and
termination reasons. Rebuilt WASM passes the 36-PDF/24-density fixture suite.
The solver settings and previously qualified Python/Rust difference are unchanged.

Fresh interleaved old/new/Python timings are in the
[prepared density report](benchmarks/PREPARED_DENSITY_REPORT.md), including the
14-worker Mg₂SiO₄ case where no improvement was measured.

## Profile-guided FFT execution

After selecting immutable-input FFT execution where it fits the existing memory
budget, all 32 full native fits again match the previous prepared release bit
for bit, including objectives, evaluations, termination and 258,048 array values.
609 Python tests and 25 Rust tests pass. The new FFT test covers native/scalar
planners and changing input lengths; WASM retains the same 36-PDF/24-density
fixture results. All-feature Clippy and formatting pass. Profiling is disabled
in the timed normal wheels. See the [profile and benchmark report](benchmarks/PROFILE_DENSITY_REPORT.md).

## crates.io release 0.1.0

`glassure-core` and `glassure-cli` 0.1.0 were published from clean source commit
`a81c749558144d41e5e030500003abdf4e1cbb5f` on branch
`codex/rust-release-0.1.0`. The source snapshot is committed and pushed; it has
not been merged into develop. The existing uncommitted Python/manuscript work
was preserved. No Python wheel/PyPI or web application release was made.

Release CI [39331077178](https://github.com/CPrescher/Glassure/actions/runs/39331077178)
passed Linux, macOS and Windows native tests/builds plus isolated package/WASM
checks. Existing Python 3.10–3.13 CI
[39331077058](https://github.com/CPrescher/Glassure/actions/runs/39331077058) also passed.
The registry-connected dry run and both actual publications completed.

A fresh consumer resolved the core from crates.io without path patches. The CLI
was installed with `cargo install --registry crates-io glassure-cli --version
0.1.0 --locked` into a verification directory. With PATH empty and PYTHONHOME
nonexistent, it passed XY and CHI loading, full PDF calculation, saved project
loading/recalculation, density fitting, a mixed multicore batch and a Q_max sweep.
The consumer's debug-build g(r) and the installed release CLI g(r) differed by at
most 1.1102230246251565e-16 (comparison tolerance 1e-12 absolute/relative).

The published archive SHA-256 values match local clean-release archives:

- core: `a7cb07351b6efb5d365d62b21505ac1353e143cb0d6320e7e11cf2e41fdc2e53`
- CLI: `4963de3e9f238dbb7cc190c68c5df0b1f8e421f118bcb2ec5358082ee6fbf3e4`

The [native API](https://docs.rs/glassure-core/0.1.0/glassure_core/) and
[WASM API](https://docs.rs/glassure-core/0.1.0/wasm32-unknown-unknown/glassure_core/)
were verified live on docs.rs. Local artifacts, upload logs and the detailed
registry verification report are under `target/published-rust/0.1.0/`.
