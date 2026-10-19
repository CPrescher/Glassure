"""Audit every Rust tutorial stage against explicitly selected Python settings.

Run the full_analysis Rust example first, then:
uv run --with matplotlib python rust/scripts/check_analysis.py
Matplotlib is a maintainer/documentation dependency, not a Rust runtime dependency.
"""
import argparse
from contextlib import nullcontext
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import glassure
from glassure import Pattern
from glassure.normalization import normalize_fit
from glassure.optimization import optimize_sq
from glassure.transform import calculate_fr, calculate_gr, calculate_sq
from glassure.utility import (calculate_f_squared_mean, calculate_f_mean_squared,
    calculate_incoherent_scattering, calculate_s0, convert_density_to_atoms_per_cubic_angstrom)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "target/full-analysis")
    parser.add_argument("--no-figure", action="store_true")
    args = parser.parse_args()
    output = args.output
    core = ROOT / "rust/glassure-core"
    data = core / "tests/data"
    choose = getattr(glassure, "use_backend", None)
    with choose("python") if choose else nullcontext():
        measured = Pattern.from_file(str(data / "Mg2SiO4_ambient.xy"))
        background = Pattern.from_file(str(data / "Mg2SiO4_ambient_bkg.xy"))
        scaled = background * 1.1
        sample = (measured - scaled).limit(0., 16.)
        composition, density, source = {"Mg": 2, "Si": 1, "O": 4}, 2.7, "hajdu"
        rho = convert_density_to_atoms_per_cubic_angstrom(composition, density)
        f2 = calculate_f_squared_mean(composition, sample.x, source)
        fm2 = calculate_f_mean_squared(composition, sample.x, source)
        inc = calculate_incoherent_scattering(composition, sample.x, source)
        parameters, normalized = normalize_fit(sample, f2, inc, q_cutoff=5., method="squared")
        n = float(getattr(parameters["n"], "value", parameters["n"]))
        total = sample * n
        sq = calculate_sq(normalized, f2, fm2)
        extended = sq.extend_to(0., calculate_s0(composition, source))
        r = np.arange(1e-10, 10.005, .01)
        fr = calculate_fr(extended, r=r, method="fft")
        gr = calculate_gr(fr, rho)
        optimized = optimize_sq(extended, r_cutoff=1.4, iterations=5, atomic_density=rho,
                                r_step=.01, fourier_transform_method="fft")
        fr_opt = calculate_fr(optimized, r=r, method="fft")
        gr_opt = calculate_gr(fr_opt, rho)
        fr_lorch = calculate_fr(optimized, r=r, method="fft", use_modification_fcn=True)
        gr_lorch = calculate_gr(fr_lorch, rho)
    patterns = dict(zip([
        "measured", "background-scaled", "sample", "normalized-total", "normalized-coherent",
        "sq-measured", "sq-extended", "sq-optimized", "fr-unoptimized", "gr-unoptimized",
        "fr-optimized", "gr-optimized", "fr-lorch", "gr-lorch", "f-squared-mean", "f-mean-squared", "incoherent",
    ], [measured, scaled, sample, total, normalized, sq, extended, optimized, fr, gr,
        fr_opt, gr_opt, fr_lorch, gr_lorch, Pattern(sample.x, f2), Pattern(sample.x, fm2), Pattern(sample.x, inc)]))
    rows = []
    actual = {}
    for name, expected in patterns.items():
        array = np.loadtxt(output / f"{name}.xy")
        assert np.isfinite(array).all(), name
        expected = np.column_stack([expected.x, expected.y])
        np.testing.assert_allclose(array, expected, rtol=1e-8, atol=1e-8, err_msg=name)
        actual[name] = array
        rows.append(dict(stage=name, points=len(array), max_absolute_difference=float(np.max(np.abs(array - expected)))))
    metrics = json.loads((output / "analysis.json").read_text())
    np.testing.assert_allclose(metrics["atomic_density_atoms_A3"], rho, atol=1e-14, rtol=1e-14)
    np.testing.assert_allclose(metrics["normalization"]["n"], n, atol=1e-12, rtol=1e-12)
    assert metrics["density_was_fitted"] is False
    report = dict(passed=True, reference_backend="python", rtol=1e-8, atol=1e-8, stages=rows,
                  numbers=sum(2 * row["points"] for row in rows),
                  max_absolute_difference=max(row["max_absolute_difference"] for row in rows),
                  input_sha256={p.name: sha256(p.read_bytes()).hexdigest() for p in data.glob("*.xy")},
                  example_sha256=sha256((core / "examples/full_analysis.rs").read_bytes()).hexdigest())
    (output / "python-comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k:report[k] for k in ["passed", "reference_backend", "numbers", "max_absolute_difference"]}), flush=True)
    if args.no_figure:
        return
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size":10, "svg.hashsalt":"glassure-full-analysis", "svg.fonttype":"none"})
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), layout="constrained")
    colors = ["#737b84", "#0072b2", "#d55e00"]
    def draw(ax, name, label, color=None):
        p = actual[name]
        ax.plot(p[:,0], p[:,1], label=label, lw=1.2, color=color)
    ax = axes[0,0]
    draw(ax,"measured","Measured",colors[1]); draw(ax,"background-scaled","1.1 × background",colors[0])
    ax.set(xlim=(0,16), xlabel="Q (Å⁻¹)", ylabel="Intensity (a.u.)", title="1–2  Data and background")
    ax = axes[0,1]
    draw(ax,"normalized-total","n × sample",colors[1])
    p = actual["f-squared-mean"]
    ax.plot(p[:,0],p[:,1]+actual["incoherent"][:,1],label="⟨f²⟩ + incoherent",color=colors[2],lw=1.2)
    draw(ax,"incoherent","Incoherent",colors[0]); ax.axvline(5,color="#333",ls=":",lw=.8)
    ax.set(xlim=(0,16), xlabel="Q (Å⁻¹)", ylabel="Normalized intensity", title="3–4  Scattering and normalization")
    ax = axes[0,2]
    draw(ax,"sq-extended","Before optimization",colors[0]); draw(ax,"sq-optimized","Optimized",colors[1])
    ax.set(xlim=(0,16), xlabel="Q (Å⁻¹)", ylabel="S(Q)", title="5–7  Extended structure factor")
    for ax, kind, title in [(axes[1,0],"fr","F(r) (Å⁻²)"),(axes[1,1],"gr","g(r)"),(axes[1,2],"gr","g(r)")]:
        for suffix,label,color in [("unoptimized","Before optimization",colors[0]),("optimized","Optimized",colors[1]),("lorch","Optimized + Lorch",colors[2])]:
            draw(ax,kind+"-"+suffix,label,color)
        ax.set(xlabel="r (Å)",ylabel=title,xlim=(0,8))
    axes[1,0].set_title("6–8  Fourier transform")
    axes[1,1].set(title="6–8  Pair distribution",ylim=(-1,3))
    axes[1,2].set(title="7–8  Low-r comparison",xlim=(0,1.6),ylim=(-.5,.5))
    axes[1,2].axvline(1.4,color="#333",ls=":",lw=.8)
    axes[1,2].axhline(0,color="#333",lw=.5)
    for ax in axes.flat:
        ax.legend(fontsize=8,loc="best"); ax.grid(alpha=.15)
        ax.spines[["top","right"]].set_visible(False)
    fig.suptitle("Mg₂SiO₄ analysis: fixed density 2.7 g/cm³ · Hajdu factors · FFT · five iterations",fontsize=13)
    png = output / "full-analysis.png"
    fig.savefig(png,dpi=150)
    svg = core / "docs/full_analysis.svg"
    fig.savefig(svg,metadata={"Date":None,"Creator":"Glassure full-analysis tutorial"})
    text = svg.read_text()
    text = text[text.index("<svg"):]
    text = text.replace("<svg ",'<svg role="img" aria-label="Intermediate curves from the full Mg2SiO4 analysis" ',1)
    svg.write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n")
    plt.close(fig)
    print(f"Figure: {svg}; preview: {png}")


if __name__ == "__main__":
    main()
