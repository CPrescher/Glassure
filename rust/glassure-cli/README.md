# Glassure CLI

Standalone X-ray total-scattering analysis using the `glassure-core` Rust library.
The `glassure` executable loads XY/CHI data or saved web projects, calculates
S(Q), F(r) and g(r), fits density, and runs multicore batches/parameter sweeps.
No Python interpreter, installed xraylib library or runtime network is required.

Version 0.1.0 is the first standalone Cargo release.
Rust 1.93 or newer is required to build the package.

## Install

From this source checkout:

```sh
cargo install --locked --path rust/glassure-cli
```

Install the registry release:

```sh
cargo install --locked glassure-cli --version 0.1.0
```

The package name is `glassure-cli`; the installed executable is `glassure`.

## Calculate a PDF

```sh
glassure init sample.xy SiO2 2.2 background.xy > request.json
glassure pdf request.json result.json
```

Edit the generated request to select Q/r ranges, normalization, corrections and
optimization. Composition is a formula or relative atomic amounts. Request
density is **mass density in g/cm³**; Q is Å⁻¹, r and wavelength are Å. Cropping
is strict: q_min < Q < q_max. The defaults use fit normalization, Brown–Hubbell
scattering factors, step extrapolation and FFT. Check the suitability of ranges
and physical assumptions for your measurement.

Patterns may embed numeric x/y arrays or use a file reference:

```json
{"file": "sample.xy", "skip_rows": 0}
```

Relative paths resolve from the request file's directory, or the working
directory for stdin. XY files contain whitespace-separated x/y columns; comments
starting with `#`, blank lines and additional columns are accepted. `.chi` files
skip four header rows. File references accept only `file` and `skip_rows`.

## Saved web projects

```sh
glassure project experiment.json recalculated.json
```

The `dataFiles` / `backgroundFiles` JSON project format is imported directly.
Every configuration's sq/fr/gr curves are recalculated; data, settings, IDs,
selections, stored fitted densities and UI metadata are retained. The saved output
can be reopened in the web app. This command does not rerun stored density fits.
Legacy desktop projects and Python's base64 NumPy API payloads are not imported.

## Other commands

```sh
glassure density density-request.json fit.json
glassure batch batch-request.json batch-results.json
glassure sweep sweep-request.json sweep-results.json
glassure factors factors-request.json factors.json
glassure --help
```

Density requests contain a `calculation` object, objective `method` (`gr`, `fr`
or `sq`), and optional fitting settings. Bounded TRF (`algorithm: "lsq"`) is the
default; specify a suitable `min_range` or enable S(Q) optimization for the
default low-r interval. Reported errors are conditional fit estimates, not full
experimental uncertainties.

Batch jobs use `{"operation": "calculate", "request": {...}}` or `density`.
Sweeps contain a `base` job and explicit `points` overriding density, background
scale, q_max and/or r_cutoff. Native `threads: 0` selects available CPUs (up to 64),
`1` is serial. At most 1024 independent jobs are accepted; each fit is sequential.
Inspect every per-job result, including when the command exits successfully.

Input can be a filename or `-`/stdin; omitting the output filename writes JSON
to stdout. Errors go to stderr and return a nonzero exit code, except per-job
batch/sweep failures, which remain explicit entries in the output report.

## Documentation and licenses

The [Rust guide](https://github.com/CPrescher/Glassure/blob/codex/rust-release-0.1.0/docs/rust.md)
includes a complete executable workflow and generates request templates for
PDFs, fits, batches and sweeps. The core package provides the Rust API reference;
build it locally with `cargo doc --no-deps -p glassure-core` in the source checkout.

Embedded scattering data and adapted numerical solvers retain their provenance
and notices. See `LICENSE`, `THIRD_PARTY_NOTICES.md` and the core's Xraylib data
license. Validation establishes implementation agreement with Glassure Python,
not independent physical validation of a sample or model.
