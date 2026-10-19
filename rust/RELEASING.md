# Rust package preparation and release

The distributable Cargo packages are `glassure-core` (library, imported as
`glassure_core`) and `glassure-cli` (installs the `glassure` executable).
Both begin at 0.1.0 and require Rust 1.93 or newer. The Python package's version
continues to follow its existing git-tag scheme; the native wheel remains the
separate `glassure-native` distribution. Creating Rust archives does not release
or replace either Python package.

## Prepare reviewable source archives

From the repository root:

```sh
cargo fmt --all -- --check
cargo clippy --locked --workspace --all-targets --all-features -- -D warnings
cargo test --locked --workspace --all-features
python3 rust/scripts/check_packages.py --wasm
```

Install the `wasm32-unknown-unknown` target before using `--wasm`. The verification
script uses Python's standard library as a **maintainer tool**; the distributed
Rust packages have no Python runtime or build dependency. Cached dependencies can
be checked with `--offline`. For a local review of uncommitted implementation,
explicitly add `--allow-dirty`; the archive records its dirty VCS provenance.
Release verification must use committed sources without that option.

The script:

1. Runs Cargo's verified packaging for both crates together. Cargo stages the
   companion core archive to verify the CLI's normal versioned dependency before
   its first registry publication.
2. Extracts both archives outside the checkout, audits manifests, licenses and
   pinned Xraylib table hashes, and runs the core's tests and rustdoc examples.
3. Builds documentation with warnings treated as errors and optionally checks WASM.
4. Runs the extracted CLI's tests, including file/project input with Python
   unavailable, and installs its executable into a disposable location.
5. Builds and runs a fresh application consuming the extracted Rust library.

For the isolated CLI tests/install before first publication, only the disposable
test manifest patches the core dependency to the extracted companion archive.
The delivered CLI manifest retains `glassure-core = "0.1.0"`, with no path or
checkout dependency. This verifies source distribution; it does not establish
that crates.io installation works before the packages are published.

Artifacts are under `target/package/`:

```text
glassure-core-0.1.0.crate
glassure-cli-0.1.0.crate
```

`target/package-validation/report.json` records versions, sizes, SHA-256 hashes,
VCS provenance and the checks performed. CI runs the same verification from a
clean checkout and uploads the archives and report. Remote success must be
checked separately; configuring the workflow does not establish a passing run.

Core archives explicitly include sources, examples, tests, README, MIT license,
SciPy/Xraylib notices and original/binary scattering tables with provenance.
CLI archives include sources, usage documentation, notices and standalone XY/CHI
test fixtures. Package allowlists exclude benchmarks, Python bindings, generated
build output and manuscript files.

## Publish only the reviewed release

Before publishing, verify the desired package names are available or owned by
the releasing account, review changes and artifacts, commit the approved source,
and check required platform CI. A local `.crate` is not a published version.
The initial names have not been reserved by creating these archives.

Check registry access and validation without uploading:

```sh
cargo publish --dry-run --locked -p glassure-core -p glassure-cli
```

This requires registry connectivity even when dependencies are cached. A failed
registry request is not a successful dry run. It does not prevent local
`cargo package` verification using cached dependencies.

When publication is explicitly authorized, publish the library first and wait
for its version to become available in the registry, then publish the CLI:

```sh
cargo publish --locked -p glassure-core
cargo publish --locked -p glassure-cli
```

Never use `--allow-dirty` for a release. Do not publish the Python bindings crate
through Cargo: `glassure-python` intentionally retains `publish = false` and
uses the wheel build/release process. Crates.io publication is immutable for a
given name/version; version bumps must update the dependent CLI/native manifest
requirements and regenerate/review lockfiles.

After registry publication, independently verify:

- A fresh application using `glassure-core = "0.1.0"` builds and calculates a PDF.
- `cargo install --locked glassure-cli --version 0.1.0` installs `glassure` and
  can load XY/CHI and a saved web project without Python.
- docs.rs builds the native and WASM API reference; check its public pages.
- Package archives/checksums correspond to the reviewed release artifacts.

Only then change documentation from “publication pending” to “published”. Rust
package publication does not deploy the web application or publish Python wheels.

Cargo's [package command](https://doc.rust-lang.org/cargo/commands/cargo-package.html)
and [publishing guide](https://doc.rust-lang.org/cargo/reference/publishing.html)
describe archive verification, registry dependencies and release semantics.
