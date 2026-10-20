"""Audit release archives without importing Glassure or third-party libraries."""

import argparse
from email.parser import Parser
from pathlib import Path
import tarfile
import zipfile


def check_metadata(text, expected_tag):
    metadata = Parser().parsestr(text)
    assert metadata["Name"] == "glassure"
    if expected_tag:
        assert metadata["Version"] == expected_tag.removeprefix("v"), metadata["Version"]
    dependencies = metadata.get_all("Requires-Dist", [])
    required = {line.split(">=")[0] for line in dependencies if ";" not in line}
    assert required == {"numpy", "pydantic"}, required
    assert "legacy" in metadata.get_all("Provides-Extra", [])
    assert metadata["License-Expression"] == "MIT AND BSD-3-Clause"
    return metadata["Version"]


def check_archive(path, expected_tag=None):
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            metadata = next(name for name in names if name.endswith(".dist-info/METADATA"))
            version = check_metadata(archive.read(metadata).decode(), expected_tag)
            assert any(name.startswith("glassure/_glassure_numpy") and name.endswith((".so", ".pyd")) for name in names)
            assert "glassure/calc.py" in names and "glassure/data/atomic_weights.csv" in names
            assert any("licenses/THIRD_PARTY_NOTICES.md" in name for name in names)
            assert not any(name.endswith("_version.py") for name in names)
    else:
        with tarfile.open(path) as archive:
            names = archive.getnames()
            metadata = next(name for name in names if name.count("/") == 1 and name.endswith("/PKG-INFO"))
            version = check_metadata(archive.extractfile(metadata).read().decode(), expected_tag)
            assert any(name.endswith("rust/glassure-python/src/lib.rs") for name in names)
            assert any(name.endswith("rust/glassure-core/src/lib.rs") for name in names)
            assert any(name.endswith("/Cargo.lock") for name in names)
            assert any(name.endswith("/tests/test_minimal_install.py") for name in names)
            assert not any(part in name.split("/") for name in names for part in (".venv", "target", "paper", "tmp", "prototypes"))
    assert not any("__pycache__" in name or name.endswith(".pyc") for name in names)
    print(f"Verified {path.name}: {version}, bundled Rust, NumPy/Pydantic requirements")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-tag")
    args = parser.parse_args()
    paths = sorted([*args.directory.glob("*.whl"), *args.directory.glob("*.tar.gz")])
    if not paths:
        parser.error("No distribution archives found")
    for path in paths:
        check_archive(path, args.expected_tag)
