"""Build and verify distributable Rust archives independently of the checkout.

Maintainer tool (Python standard library only); distributed Rust builds do not
require Python. Before first publication the isolated CLI check patches its
registry dependency to the core extracted from the companion archive. Cargo's
own package verification additionally tests the unmodified registry manifests
using its staging registry. This script never publishes or accesses credentials.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def run(arguments, *, cwd=ROOT, environment=None):
    print("+", " ".join(map(str, arguments)), flush=True)
    subprocess.run(list(map(str, arguments)), cwd=cwd, env=environment, check=True)


def extract(archive, destination):
    """Extract only regular files/directories under the expected package root."""
    expected = archive.name.removesuffix(".crate")
    with tarfile.open(archive, "r:gz") as package:
        names = set()
        for member in package.getmembers():
            relative = Path(member.name)
            if relative.is_absolute() or ".." in relative.parts or relative.parts[0] != expected:
                raise ValueError(f"Unexpected archive path: {member.name}")
            target = destination / relative
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                if member.name in names:
                    raise ValueError(f"Duplicate archive entry: {member.name}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with package.extractfile(member) as source:
                    target.write_bytes(source.read())
            else:
                raise ValueError(f"Unsupported archive entry: {member.name}")
            names.add(member.name)
    return destination / expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-dirty", action="store_true", help="Local review builds only; retains Cargo's dirty provenance flag")
    parser.add_argument("--offline", action="store_true", help="Use already cached Cargo dependencies")
    parser.add_argument("--wasm", action="store_true", help="Also check the extracted core for wasm32-unknown-unknown")
    args = parser.parse_args()
    cargo_options = ["--offline"] if args.offline else []
    package_options = ["--allow-dirty"] if args.allow_dirty else []
    run(["cargo", "package", "--locked", "--all-features", *cargo_options, *package_options,
         "-p", "glassure-core", "-p", "glassure-cli"])
    metadata = json.loads(subprocess.check_output(
        ["cargo", "metadata", "--locked", "--no-deps", "--format-version", "1"], cwd=ROOT))
    packages = {p["name"]: p for p in metadata["packages"]}
    target = Path(metadata["target_directory"])
    artifacts = {name: target / "package" / f"{name}-{packages[name]['version']}.crate"
                 for name in ("glassure-core", "glassure-cli")}
    report = {"passed": False, "packages": [], "cli_dependency": "companion archive via temporary path patch; registry installation not claimed",
              "wasm_checked": args.wasm}
    with tempfile.TemporaryDirectory(prefix="glassure-packages-") as temporary:
        directory = Path(temporary)
        unpacked = {name: extract(archive, directory) for name, archive in artifacts.items()}
        for name, source in unpacked.items():
            for required in ("Cargo.toml", "Cargo.lock", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md"):
                assert (source / required).is_file(), (name, required)
            manifest = (source / "Cargo.toml").read_text()
            assert "[workspace" not in manifest and 'path = "../' not in manifest
            vcs = json.loads((source / ".cargo_vcs_info.json").read_text())
            report["packages"].append(dict(name=name, version=packages[name]["version"],
                archive=str(artifacts[name]), bytes=artifacts[name].stat().st_size,
                sha256=sha256(artifacts[name].read_bytes()).hexdigest(), vcs=vcs))

        core = unpacked["glassure-core"]
        data = core / "data/xraylib"
        provenance = json.loads((data / "provenance.json").read_text())
        for table, hashes in provenance["tables"].items():
            assert sha256((data / f"{table}.bin").read_bytes()).hexdigest() == hashes["binary_sha256"]
            assert sha256((data / f"{table}.dat").read_bytes()).hexdigest() == hashes["text_sha256"]
        assert (data / "LICENSE.txt").is_file()
        environment = dict(os.environ, CARGO_TARGET_DIR=str(target / "package-validation"))
        run(["cargo", "test", "--locked", "--all-features", *cargo_options], cwd=core, environment=environment)
        run(["cargo", "doc", "--locked", "--no-deps", "--all-features", *cargo_options], cwd=core,
            environment=dict(environment, RUSTDOCFLAGS="-D warnings"))
        if (core / "examples/full_analysis.rs").exists():
            run(["cargo", "run", "--locked", "--release", "--example", "full_analysis", *cargo_options, "--",
                 core / "tests/data/Mg2SiO4_ambient.xy", core / "tests/data/Mg2SiO4_ambient_bkg.xy", directory / "tutorial-output"],
                cwd=core, environment=environment)
        if args.wasm:
            run(["cargo", "check", "--locked", "--all-features", "--target", "wasm32-unknown-unknown", *cargo_options],
                cwd=core, environment=environment)
            run(["cargo", "doc", "--locked", "--no-deps", "--all-features", "--target", "wasm32-unknown-unknown", *cargo_options],
                cwd=core, environment=dict(environment, RUSTDOCFLAGS="-D warnings"))

        if (core / "examples/density_fitting.rs").exists():
            run(["cargo", "run", "--locked", "--release", "--example", "density_fitting", *cargo_options, "--",
                 core / "tests/data/Mg2SiO4_ambient.xy", core / "tests/data/Mg2SiO4_ambient_bkg.xy", directory / "density-output"],
                cwd=core, environment=environment)

        cli = unpacked["glassure-cli"]
        # Patch only this unpublished dependency in the disposable check copy.
        # The deliverable archive retains its normal versioned registry dependency.
        with (cli / "Cargo.toml").open("a") as manifest:
            manifest.write(f'\n[patch.crates-io]\nglassure-core = {{ path = {json.dumps(core.as_posix())} }}\n')
        # Let Cargo replace this dependency's lock entry, preserving other pins.
        run(["cargo", "check", *cargo_options], cwd=cli, environment=environment)
        run(["cargo", "test", "--locked", *cargo_options], cwd=cli, environment=environment)
        install = directory / "installation"
        run(["cargo", "install", "--locked", "--path", cli, "--root", install, *cargo_options],
            cwd=directory, environment=environment)
        executable = install / "bin" / ("glassure.exe" if os.name == "nt" else "glassure")
        run([executable, "--version"], cwd=directory,
            environment=dict(os.environ, PATH="", PYTHONHOME="/nonexistent"))
        consumer = directory / "consumer"
        (consumer / "src").mkdir(parents=True)
        (consumer / "Cargo.toml").write_text(
            '[package]\nname = "glassure-package-consumer"\nversion = "0.0.0"\nedition = "2021"\n'
            f'[dependencies]\nglassure-core = {{ path = {json.dumps(core.as_posix())} }}\n')
        (consumer / "src/main.rs").write_text('''use glassure_core::{pattern::Pattern, request::{calculate, Request}, scattering::Composition};
fn main() -> Result<(), String> {
    let q = (1..=200).map(|i| i as f64 * 0.1).collect();
    let request = Request::new(Pattern::new(q, vec![100.; 200])?, Composition::Formula("SiO2".into()), 2.2)?;
    let result = calculate(request)?;
    assert_eq!(result.gr.x.len(), 1001);
    assert!(result.gr.y.iter().all(|x| x.is_finite()));
    println!("Independent Rust consumer calculated {} g(r) points", result.gr.x.len());
    Ok(())
}
''')
        run(["cargo", "run", *cargo_options], cwd=consumer, environment=environment)
    report["passed"] = True
    report["created_utc"] = datetime.now(timezone.utc).isoformat()
    report["checks"] = ["cargo package verification using staged registry", "archive manifests and required files",
        "pinned Xraylib table hashes", "extracted core all-feature tests and doctests", "native rustdoc with warnings denied",
        "extracted CLI tests", "isolated CLI installation with companion-core patch", "installed executable without Python discovery",
        "fresh independent Rust application"]
    if args.wasm:
        report["checks"].extend(["extracted core WASM compilation", "WASM rustdoc with warnings denied"])
    if (ROOT / "rust/glassure-core/examples/full_analysis.rs").exists():
        report["checks"].append("extracted stage-by-stage analysis example")
    if (ROOT / "rust/glassure-core/examples/density_fitting.rs").exists():
        report["checks"].append("extracted density/background fitting and multicore example")
    destination = target / "package-validation/report.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Package verification passed: {destination}", flush=True)


if __name__ == "__main__":
    main()
