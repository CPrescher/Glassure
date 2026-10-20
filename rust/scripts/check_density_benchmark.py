"""Audit the supplemental density-batch inputs before interpreting fit timings.

uv run --with threadpoolctl python rust/scripts/check_density_benchmark.py
"""
from datetime import datetime, timezone
import json
from pathlib import Path

from benchmark_backend import (
    ROOT, DENSITY_OPTIONS, compare, np, python_one, rust, sha,
    threadpool_limits, workloads, calculate_pdf,
)


def objective(job, fit):
    data, config = job[0].model_copy(), job[1].model_copy(deep=True)
    data.bkg_scaling = fit[2]
    config.sample.density = fit[0]
    pattern = calculate_pdf(data, config, backend="python").gr.limit(*DENSITY_OPTIONS["min_range"])
    residual = pattern.y * (pattern.x[1] - pattern.x[0])
    return float(residual @ residual)


def main():
    result = {"created_utc": datetime.now(timezone.utc).isoformat(),
              "script_sha256": sha(Path(__file__)),
              "workload_script_sha256": sha(ROOT / "rust/scripts/benchmark_backend.py"),
              "parameter_tolerances": {"absolute": 1e-5, "relative_fitted": 1e-6, "relative_errors": 1e-3},
              "options": DENSITY_OPTIONS, "rows": []}
    with threadpool_limits(limits=1):
        for name, (operation, jobs) in workloads(64, 16).items():
            if operation != "density":
                continue
            for index, job in enumerate(jobs):
                expected = python_one(operation, job)
                native = rust._engine(1).density(rust._density_request(*job, **DENSITY_OPTIONS))
                actual = rust._fit_tuple(native)
                try:
                    compare(operation, [actual], [expected])
                    passed = True
                except AssertionError:
                    passed = False
                py_cost, rs_cost = objective(job, expected), objective(job, actual)
                row = dict(case=name, job=index, background_scale=job[0].bkg_scaling,
                    strict_parameter_parity=passed, python=list(expected), rust=list(actual),
                    absolute_density_difference=abs(actual[0] - expected[0]),
                    python_objective=py_cost, rust_fit_objective_evaluated_in_python=rs_cost,
                    relative_objective_difference=abs(py_cost - rs_cost) / max(abs(py_cost), 1e-300),
                    rust_evaluations=native["evaluations"], rust_termination=native["termination"])
                result["rows"].append(row)
                if not passed:
                    print(name, index, "parameter tolerance exceeded:", row, flush=True)
    result["strict_passed"] = all(row["strict_parameter_parity"] for row in result["rows"])
    result["mismatched_cases"] = sum(not row["strict_parameter_parity"] for row in result["rows"])
    path = ROOT / "rust/benchmarks/density-parity.json"
    path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"{len(result['rows'])} fits audited; {result['mismatched_cases']} exceed the strict parameter tolerances.")


if __name__ == "__main__":
    main()
