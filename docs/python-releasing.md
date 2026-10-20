# Releasing the Python package

Glassure 3 is a mixed Python/Rust distribution built from the repository root.
Its version is set explicitly in the root `pyproject.toml`, independently of the
Rust library/CLI versions. The current stable Python version is `3.0.0`.

## Local verification

```sh
uv sync --extra dev
uv run pytest tests --glassure-backend=rust
uv run pytest tests --glassure-backend=python
cargo fmt --all --check
cargo clippy --locked --workspace --all-targets --all-features -- -D warnings
cargo test --locked --workspace --all-features
uv build
python scripts/check_python_dist.py dist --expected-tag 3.0.0
uvx twine check dist/*
```

Use an empty output directory for each version. `uv build` builds the wheel from
its source archive, checking that sources, workspace members and embedded data
are sufficient outside the checkout. The archive audit checks direct requirements,
version, native module, notices and source contents. Avoid shipping prototype,
manuscript, temporary or generated build directories.

Install the exact wheel in a fresh environment containing only its default
requirements and pytest; run `tests/test_minimal_install.py` from outside the
checkout with `--import-mode=importlib`. Then install that same wheel with its
`[dev]` extra and run the full suite once per backend. CI performs these checks
for every supported Python/platform wheel and tests the minimum direct dependency
versions separately. Rust package, CLI, documentation and WASM checks also gate
publication. Local macOS success does not establish Windows/Linux success.

## Release candidate and publication

1. Review and commit the release sources, including previously untracked Rust
   files, packaging tests, notices and workflows. Check for unrelated local work.
2. Run Python CI and Rust CI for that commit and inspect every platform result.
3. Ensure the proposed GitHub release tag (for example, `3.0.0` or `v3.0.0`) matches
   `project.version`. Cargo prerelease spelling is not used for the Python tag.
4. When publication is authorized, publish the GitHub release. The existing PyPI
   trusted publisher must permit `.github/workflows/CD.yml` and environment `pypi`.
5. CD rebuilds and tests the wheel matrix and source archive, runs Rust validation,
   audits artifact versions against the release tag, then publishes using OIDC.
   A failed build or test prevents publishing; a GitHub release alone is not proof
   that PyPI upload succeeded.
6. Verify a fresh `pip install glassure==3.0.0`, its reported version,
   native backend, sample calculation and optional legacy installation from PyPI.

For each release, update `project.version`, regenerate `uv.lock`, update the
migration/changelog status, and repeat verification. Mark release candidates as
prereleases on GitHub; mark stable releases as the latest release. Do not reuse a
published version.
