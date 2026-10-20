"""Compare standalone project-file calculations with the independent Python API.

Build with cargo build --locked --release, then run:
    uv run python rust/scripts/check_standalone.py
Python orchestrates this audit; the tested executable has an empty environment
and PATH, with PYTHONHOME pointing to a nonexistent interpreter installation.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from glassure import Pattern, use_backend
from glassure.calc import calculate_pdf
from glassure.configuration import CalculationConfig, DataConfig


def python_inputs(project, file, config):
    """Translate saved UI settings independently through Python's model schema."""
    sample, transform = config.get("sample", {}), config.get("transform", {})
    normalization, optimization = config.get("normalization", {}), config.get("optimization", {})
    value = lambda section, key, default: default if section.get(key) is None else section[key]
    n = dict(TYPE=normalization.get("normalizationMethod", "fit"),
             incoherent_scattering=normalization.get("incoherentScattering", True))
    if n["TYPE"] == "fit":
        n.update(q_cutoff=value(normalization, "qCutoff", 5), method="squared",
                 multiple_scattering=normalization.get("multipleScattering", False),
                 container_scattering=normalization.get("containerComposition")
                 if normalization.get("containerScattering") else None)
        dac = normalization.get("dac", {})
        if n["container_scattering"] and dac.get("enabled"):
            n["dac"] = dict(initial_thickness=dac["initialThickness"], sample_thickness=dac["sampleThickness"])
    else:
        n["attenuation_factor"] = 0.001
    r_min = value(transform, "rMin", 0)
    c = CalculationConfig.model_validate(dict(
        sample=dict(composition=sample.get("composition", "SiO2"), density=value(sample, "densityGcm3", 2.2)),
        transform=dict(q_min=value(transform, "qMin", 0), q_max=value(transform, "qMax", 12),
                       r_min=1e-13 if r_min == 0 else r_min, r_max=value(transform, "rMax", 10),
                       r_step=0.01, normalization=n,
                       extrapolation=dict(method=transform.get("extrapolationMethod", "linear")),
                       use_modification_fcn=transform.get("lorchModification", False),
                       kn_correction=transform.get("kleinNishimaCorrection", False),
                       wavelength=value(transform, "wavelength", 0.31)),
        optimize=dict(method=optimization.get("method", "iterative"),
                      r_cutoff=value(optimization, "rCutoff", 1.4),
                      iterations=value(optimization, "iterations", 5),
                      use_modification_fcn=optimization.get("lorchModification", False))
        if optimization.get("isEnabled") else None))
    background_id = config.get("backgroundFileId")
    background = next((b["pattern"] for b in project["backgroundFiles"] if b["id"] == background_id), None)
    return DataConfig(data=Pattern.from_dict(file["pattern"]),
                      bkg=None if background is None else Pattern.from_dict(background),
                      bkg_scaling=config.get("backgroundScale", 1)), c


def sample_project():
    data = Pattern.from_file(str(ROOT / "tests/data/SiO2.xy"))
    bkg = Pattern.from_file(str(ROOT / "tests/data/SiO2_bkg.xy"))
    base = dict(sample=dict(composition="SiO2", densityGcm3=2.2), backgroundFileId="b",
                backgroundScale=1., transform=dict(qMin=1., qMax=17., extrapolationMethod="linear"))
    configs = {"defaults": deepcopy(base)}
    for method in ("fit", "integral"):
        for extrapolation in ("step", "linear", "poly", "spline"):
            c = deepcopy(base)
            c["normalization"] = dict(normalizationMethod=method, qCutoff=3.)
            c["transform"].update(extrapolationMethod=extrapolation, lorchModification=True)
            configs[f"{method}-{extrapolation}"] = c
    for method in ("iterative", "fit"):
        c = deepcopy(base)
        c["optimization"] = dict(isEnabled=True, method=method, rCutoff=1.1, iterations=5)
        configs[f"optimization-{method}"] = c
    c = deepcopy(base)
    c["normalization"] = dict(normalizationMethod="fit", qCutoff=3., multipleScattering=True,
                              containerScattering=True, containerComposition="C",
                              dac=dict(enabled=True, initialThickness=40., sampleThickness=30.))
    c["transform"].update(kleinNishimaCorrection=True, wavelength=.31)
    configs["combined-corrections"] = c
    return dict(dataFiles=[dict(id="s", pattern=data.to_dict(), configurations=configs,
                               selectedConfigurationId="defaults")],
                backgroundFiles=[dict(id="b", pattern=bkg.to_dict())], selectedDataFileId="s")


def main():
    binary = ROOT / "target/release" / ("glassure.exe" if os.name == "nt" else "glassure")
    projects = {"silica": sample_project()}
    # A real saved browser project is available in the author's working tree;
    # keep it optional because manuscript files are not part of the Rust package.
    cerium = ROOT / "paper/results/cerium_sylvia_2026-10-15/Cerium_input_original.json"
    if cerium.exists():
        projects["cerium-saved-project"] = json.loads(cerium.read_text())
    rows = []
    with tempfile.TemporaryDirectory(prefix="glassure-project-audit-") as temporary, use_backend("python"):
        directory = Path(temporary)
        for name, project in projects.items():
            source, output = directory / f"{name}.json", directory / f"{name}-result.json"
            source.write_text(json.dumps(project))
            subprocess.run([str(binary), "project", str(source), str(output)], check=True,
                           cwd=directory, env={"PATH": "", "PYTHONHOME": "/nonexistent"})
            result = json.loads(output.read_text())
            for file in project["dataFiles"]:
                native_file = next(f for f in result["dataFiles"] if f["id"] == file["id"])
                for key, config in file["configurations"].items():
                    expected = calculate_pdf(*python_inputs(project, file, config), backend="python")
                    actual = native_file["configurations"][key]
                    differences = {}
                    for curve in ("sq", "fr", "gr"):
                        for axis in ("x", "y"):
                            py = getattr(getattr(expected, curve), axis)
                            rs = np.array(actual[curve][axis])
                            np.testing.assert_allclose(rs, py, atol=1e-7, rtol=1e-7,
                                                       err_msg=f"{name}/{key}/{curve}/{axis}")
                            differences[f"{curve}_{axis}"] = float(np.max(np.abs(rs - py)))
                    rows.append(dict(project=name, configuration=key, max_absolute_difference=differences))
    report = dict(passed=True, configurations=len(rows), input_precision="saved f64 arrays; no Float32 transport",
                  executable_environment={"PATH": "", "PYTHONHOME": "/nonexistent"}, rows=rows)
    destination = ROOT / "target/backend-selection/standalone-project-parity.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(passed=True, configurations=len(rows), report=str(destination),
                         max_absolute_difference=max(max(r["max_absolute_difference"].values()) for r in rows))))


if __name__ == "__main__":
    main()
