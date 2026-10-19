"""Compare the Rust density tutorial with Python and render its scientific plots.

Run the density_fitting example, then:
uv run --with matplotlib python rust/scripts/check_density_tutorial.py
This is a maintainer audit, not a Rust build/runtime dependency.
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
from glassure.calc import calculate_pdf, create_calculate_pdf_configs
from glassure.configuration import OptimizeConfig
from glassure.optimization import optimize_density
from glassure.utility import calculate_kn_correction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "target/density-tutorial")
    parser.add_argument("--no-figure", action="store_true")
    args = parser.parse_args()
    output = args.output
    core = ROOT / "rust/glassure-core"
    fixtures = core / "tests/data"
    report = json.loads((output / "analysis.json").read_text())
    choose = getattr(glassure, "use_backend", None)
    comparisons = []
    arrays = {}

    def compare(label, actual, expected, rtol=1e-5, atol=1e-6):
        actual, expected = np.asarray(actual), np.asarray(expected)
        np.testing.assert_allclose(actual, expected, rtol=rtol, atol=atol, err_msg=label)
        comparisons.append(dict(name=label, numbers=int(actual.size), rtol=rtol,
                                atol=atol, max_absolute_difference=float(np.max(np.abs(actual - expected)))))

    def curves(label, actual, expected):
        for name in ["sq", "fr", "gr"]:
            python = getattr(expected, name)
            compare(label + "-" + name + "-x", actual[name]["x"], python.x, rtol=0, atol=1e-13)
            compare(label + "-" + name + "-y", actual[name]["y"], python.y)

    with choose("python") if choose else nullcontext():
        data, config = create_calculate_pdf_configs(
            Pattern.from_file(str(fixtures / "Mg2SiO4_ambient.xy")), "Mg2SiO4", 2.7,
            Pattern.from_file(str(fixtures / "Mg2SiO4_ambient_bkg.xy")),
        )
        data.bkg_scaling = 1.1
        t = config.transform
        t.q_min, t.q_max = 1., 20.
        t.r_min, t.r_max, t.r_step = 1e-10, 10., .01
        t.scattering_factor_source = "brown_hubbell"
        t.normalization.q_cutoff = 5.
        t.normalization.method = "squared"
        t.normalization.multiple_scattering = False
        t.normalization.incoherent_scattering = True
        t.extrapolation.method = "linear"
        t.fourier_transform_method = "fft"
        t.kn_correction, t.wavelength = True, .1908
        t.use_modification_fcn = False
        config.optimize = OptimizeConfig(r_cutoff=1.4, iterations=3, use_modification_fcn=False)
        kn = np.loadtxt(output / "klein-nishina.xy")
        compare("klein-nishina", kn[:,1], calculate_kn_correction(kn[:,0], .1908), rtol=1e-13, atol=1e-14)
        initial = calculate_pdf(data.model_copy(), config.model_copy(deep=True))
        for name in ["sq", "fr", "gr"]:
            actual = np.loadtxt(output / f"initial-{name}.xy")
            arrays[f"initial-{name}"] = actual
            compare(f"initial-{name}", actual, np.column_stack([getattr(initial, name).x, getattr(initial, name).y]))

        def audit_fit(label, actual, start, vary):
            c = config.model_copy(deep=True)
            c.sample.density = start
            fit = optimize_density(data.model_copy(), c, method="gr", min_range=(.1, 1.3),
                                   vary_bkg_scaling=vary, bkg_limits=(.9, 1.1), optimization_method="lsq")
            compare(label + "-parameters", [actual["density"], actual["background_scale"]], [fit[0], fit[2]])
            if fit[1] is not None and fit[3] is not None:
                compare(label + "-conditional-errors", [actual["density_error"], actual["background_error"]],
                        [fit[1], fit[3]], rtol=2e-3, atol=1e-5)
            c.sample.density = fit[0]
            d = data.model_copy()
            d.bkg_scaling = fit[2]
            expected = calculate_pdf(d, c)
            curves(label, actual["result"], expected)
            low = expected.gr.limit(.1, 1.3)
            sse = float(np.sum((low.y * (low.x[1] - low.x[0])) ** 2))
            compare(label + "-sse", actual["sum_squared_residuals"], sse, rtol=1e-5, atol=1e-12)
            return expected

        for label, vary in [("fixed", False), ("joint", True)]:
            expected = audit_fit(label, report[label], 2.7, vary)
            for name in ["sq", "fr", "gr"]:
                actual = np.loadtxt(output / f"{label}-{name}.xy")
                arrays[f"{label}-{name}"] = actual
                compare(label + "-export-" + name, actual,
                        np.column_stack([getattr(expected, name).x, getattr(expected, name).y]))
        for index, start in enumerate(report["starts"]):
            serial = report["serial"]["items"][index]
            parallel = report["multicore"]["items"][index]
            assert serial == parallel and serial["status"] == "success"
            audit_fit(f"batch-{index}", parallel["output"]["result"], start, True)

    assert report["at_background_bound"] is True
    assert abs(report["joint"]["background_scale"] - report["background_bounds"][1]) < 1e-6
    assert report["dac_applied_to_ambient_data"] is False
    result = dict(passed=True, reference_backend="python", comparisons=comparisons,
                  numbers=sum(row["numbers"] for row in comparisons), serial_multicore_identical=True,
                  max_absolute_difference=max(row["max_absolute_difference"] for row in comparisons),
                  input_sha256={p.name: sha256(p.read_bytes()).hexdigest() for p in fixtures.glob("*.xy")},
                  example_sha256=sha256((core / "examples/density_fitting.rs").read_bytes()).hexdigest())
    (output / "python-comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k:result[k] for k in ["passed", "numbers", "max_absolute_difference", "serial_multicore_identical"]}), flush=True)
    if args.no_figure:
        return

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size":10, "svg.hashsalt":"glassure-density-tutorial", "svg.fonttype":"none"})
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), layout="constrained")
    colors = ["#737b84", "#0072b2", "#d55e00"]
    labels = ["Initial", "Density fit; fixed background", "Joint fit; background at bound"]
    for ax, kind, title, ylabel, xlim in [
        (axes[0,1],"gr","Low-r objective","g(r)",(0,1.6)),
        (axes[0,2],"gr","Full pair distribution","g(r)",(0,8)),
        (axes[1,0],"sq","Structure factor","S(Q)",(0,20)),
    ]:
        for prefix,label,color in zip(["initial","fixed","joint"],labels,colors):
            p=arrays[f"{prefix}-{kind}"]
            ax.plot(p[:,0],p[:,1],label=label,color=color,lw=1.2)
        ax.set(title=title,xlabel="Q (Å⁻¹)" if kind=="sq" else "r (Å)",ylabel=ylabel,xlim=xlim)
        ax.legend(fontsize=7)
    axes[0,1].axvspan(.1,1.3,color="#0072b2",alpha=.07)
    axes[0,1].axhline(0,color="#333",lw=.5)
    axes[0,2].set_ylim(-1,3)
    kn=np.loadtxt(output/"klein-nishina.xy")
    axes[0,0].plot(kn[:,0],kn[:,1],color=colors[1])
    axes[0,0].set(title="Klein–Nishina; wavelength 0.1908 Å",xlabel="Q (Å⁻¹)",ylabel="Incoherent multiplier")
    fits=[item["output"]["result"] for item in report["multicore"]["items"]]
    axes[1,1].plot(report["starts"],[(f["density"]-report["joint"]["density"])*1e6 for f in fits],"o-",color=colors[1])
    axes[1,1].axhline(0,ls=":",color=colors[2])
    axes[1,1].set(title="Starting guesses: numerical spread",xlabel="Starting density (g/cm³)",ylabel="Fit − joint fit (10⁻⁶ g/cm³)")
    ax=axes[1,2]
    ax.plot(["Starting","Fixed fit","Joint fit"],[1.1,report["fixed"]["background_scale"],report["joint"]["background_scale"]],"o-",color=colors[1])
    for bound in report["background_bounds"]:
        ax.axhline(bound,ls=":",color=colors[2])
    ax.set(title="Background scale:\njoint fit reaches upper bound",ylabel="Background multiplier",ylim=(.97,1.24))
    for ax in axes.flat:
        ax.grid(alpha=.15)
        ax.spines[["top","right"]].set_visible(False)
    fig.suptitle("Density/background fitting: numerical example · fitted density is not physically validated",fontsize=13)
    fig.savefig(output/"density-fitting.png",dpi=150)
    svg=core/"docs/density_fitting.svg"
    fig.savefig(svg,metadata={"Date":None,"Creator":"Glassure density-fitting tutorial"})
    text=svg.read_text()
    text=text[text.index("<svg"):].replace("<svg ",'<svg style="max-width:100%;height:auto" role="img" aria-label="Density fitting, corrections and multicore results" ',1)
    svg.write_text("\n".join(line.rstrip() for line in text.splitlines())+"\n")
    plt.close(fig)
    print(f"Figure: {svg}")


if __name__ == "__main__":
    main()
