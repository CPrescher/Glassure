# Changelog

## 3.0.0rc1 — in preparation

- Bundle the Rust numerical engine in the Python distribution. Standard installs
  run the native engine without a separate native package.
- Require only NumPy and Pydantic as direct runtime dependencies.
- Retain the Python reference backend, pandas table inspection, lmfit parameter
  objects and SciPy transfer splines through `glassure[legacy]`.
- Preserve the usual Python calculation imports, configurations and result types;
  expose native batches, sweeps and fitting through `glassure.rust`.
- Replace Python-only release packaging with maturin wheels and a rebuildable source
  archive. Test installed packages on Python 3.10–3.13 across Linux, macOS and
  Windows before publishing.
- Correct Gaussian pair-peak weighting and concentration normalization, and
  stabilize polynomial S(Q) optimization at high order and exactly Q=0. These
  numerical corrections can change results compared with Glassure 2.
- Include the Rust core's SciPy and Xraylib notices in Python distributions.

See the [migration guide](migration-3.md) for compatibility details. This release
candidate has not yet been published. Earlier releases are recorded in the
[GitHub release history](https://github.com/CPrescher/Glassure/releases).
