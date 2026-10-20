"""Plot the measured density objectives and the three optimizers' stopping points.

Run after benchmark_brent_density.py. All sampling happens outside fit timings.
The JSON alongside the figure retains the numerical source data.
"""
import json
from pathlib import Path

import benchmark_backend as b
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    directory = b.ROOT / "rust/benchmarks"
    result = json.loads((directory / "density-brent-results.json").read_text())
    work = {name: jobs for name, (operation, jobs) in b.workloads(64, 16).items() if operation == "density"}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    rows = []
    labels = {"SiO2_density": "SiO₂", "Mg2SiO4_density": "Mg₂SiO₄"}
    styles = {"lsq": ("TRF", "#0072B2", "o", 6),
              "brent_local": ("Brent, local bracket", "#009E73", "s", 9),
              "brent": ("Brent, full interval", "#D55E00", "x", 8)}
    with b.threadpool_limits(limits=1):
        for ax, (name, jobs) in zip(axes, work.items()):
            data, config = jobs[0]
            fit = next(row for row in result["complete_result_checks"] if row["case"] == name and row["job"] == 0)
            density = sorted(set(b.np.linspace(.25, 80., 400).tolist() + [m["fit"][0] for m in fit["methods"].values()]))
            values = []
            for rho in density:
                config.sample.density = rho
                gr = b.rust.calculate_pdf(data, config).gr.limit(*b.DENSITY_OPTIONS["min_range"])
                residual = gr.y * (gr.x[1] - gr.x[0])
                values.append(float(residual @ residual))
            rows.append(dict(case=name, background_scale=data.bkg_scaling, density=density, objective=values,
                             optimizer_results=fit["methods"]))
            ax.plot(density, values, color="#555555", linewidth=1.3)
            for algorithm, (label, color, marker, size) in styles.items():
                entry = fit["methods"][algorithm]
                ax.plot(entry["fit"][0], entry["objective"], marker=marker, markersize=size, color=color,
                        markerfacecolor="none" if algorithm == "brent_local" else color, linestyle="none", label=label)
            ax.set(title=labels[name], xlabel="Density (g/cm³)", ylabel="Sum of squared residuals", xlim=(0, 80), yscale="log")
            minimum = min(values)
            ax.set_ylim(minimum / 1.6, minimum * 300)
            ax.grid(alpha=.18)
            ax.legend(fontsize=8, loc="upper right")
    fig.suptitle("Density objectives have multiple minima", fontsize=13)
    fig.tight_layout()
    fig.savefig(directory / "density-brent-objectives.png", dpi=200)
    (directory / "density-brent-objectives.json").write_text(json.dumps(dict(
        note="First benchmark jobs; sampled after timing with the ordinary native PDF pipeline.",
        benchmark_sha256=b.sha(directory / "density-brent-results.json"), script_sha256=b.sha(Path(__file__)),
        source_density_units="g/cm^3", rows=rows), indent=2) + "\n")


if __name__ == "__main__":
    main()
