"""Time density fits through the public NumPy bridge and Python process pools.

Retain the prior strict checks, with the explicitly accepted SiO2 stopping-point
difference qualified by an independent evaluation of the fitted objective.

uv run --with threadpoolctl python rust/scripts/benchmark_density.py
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import subprocess
import time

import benchmark_backend as bench
from check_density_benchmark import objective


def density_validation(name, jobs):
    strict_compare = bench.compare
    qualifications = {}
    checks = 0

    def compare(operation, actual, expected, exact=False):
        nonlocal checks
        if exact:
            return strict_compare(operation, actual, expected, exact=True)
        assert len(actual) == len(expected) == len(jobs)
        maximum = 0.
        for i, (a, e) in enumerate(zip(actual, expected, strict=True)):
            checks += 1
            try:
                error = strict_compare(operation, [a], [e])
            except AssertionError:
                # User accepted this audited density discrepancy. Do not relax
                # any other parameter/error comparison or any solver setting.
                assert name == "SiO2_density"
                assert abs(jobs[i][0].bkg_scaling - 0.9906666666666667) < 1e-14
                strict_compare(operation, [(e[0], *a[1:])], [e])
                difference = abs(a[0] - e[0])
                assert difference <= 3e-4
                py_cost, rs_cost = objective(jobs[i], e), objective(jobs[i], a)
                relative = abs(py_cost - rs_cost) / max(abs(py_cost), 1e-300)
                assert relative <= 1e-8
                qualifications[i] = dict(job=i, background_scale=jobs[i][0].bkg_scaling,
                    python=list(e), rust=list(a), absolute_density_difference=difference,
                    relative_density_difference=difference / abs(e[0]),
                    python_objective=py_cost, rust_fit_objective_evaluated_in_python=rs_cost,
                    relative_objective_difference=relative)
                error = difference
            maximum = max(maximum, error)
        return maximum

    def report():
        return dict(strict_parameter_parity=not qualifications,
                    accepted_qualifications=list(qualifications.values()), comparisons=checks)

    return compare, report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--samples", type=int, default=7)
    p.add_argument("--density-jobs", type=int, default=16)
    p.add_argument("--target-ms", type=float, default=100.)
    p.add_argument("--workers", type=int, nargs="+", default=[1, 4, min(bench.os.cpu_count() or 1, 64)])
    p.add_argument("--output", type=Path, default=bench.ROOT / "rust/benchmarks/density-results.json")
    args = p.parse_args()
    if args.samples < 3 or not bench.math.isfinite(args.target_ms) or args.target_ms <= 0:
        p.error("Require >=3 samples and finite positive target-ms")
    if not 2 <= args.density_jobs <= 1024 or any(not 1 <= n <= 64 for n in args.workers):
        p.error("Job counts must be 2..1024 and worker counts 1..64")
    counts = sorted(set([1] + args.workers))
    work = {name: item for name, item in bench.workloads(64, args.density_jobs).items() if item[0] == "density"}
    prior_path = bench.ROOT / "rust/benchmarks/backend-results.json"
    prior = json.loads(prior_path.read_text())
    # Verify and retain the exact scientific-source and release-binary identity
    # of the preceding PDF run. This driver does not rebuild or alter the solver.
    fingerprints = dict(prior["metadata"]["source_sha256"])
    for path in (Path(__file__), bench.ROOT / "rust/scripts/check_density_benchmark.py"):
        fingerprints[str(path.relative_to(bench.ROOT))] = bench.sha(path)
    for name, expected in fingerprints.items():
        assert bench.sha(bench.ROOT / name) == expected, "Source changed since the PDF benchmark: " + name
    extension = Path(prior["metadata"]["extension_path"])
    assert bench.sha(extension) == prior["metadata"]["extension_sha256"]
    metadata = dict(prior["metadata"])
    for key in ("finished_utc", "background_load_after"):
        metadata.pop(key, None)
    metadata.update(created_utc=datetime.now(timezone.utc).isoformat(), hardware=bench.hardware(),
        source_sha256=fingerprints, samples=args.samples, target_sample_ms=args.target_ms,
        workers=counts, python_pool_setup={}, density_options=bench.DENSITY_OPTIONS,
        reference_pdf_report_sha256=bench.sha(prior_path),
        density_agreement_policy=dict(strict_atol=1e-5, strict_parameter_rtol=1e-6,
            strict_error_rtol=1e-3, qualified_case="SiO2_density",
            qualified_background_scale=0.9906666666666667, maximum_qualified_density_difference=3e-4,
            maximum_qualified_relative_objective_difference=1e-8),
        background_load_before=subprocess.check_output(["ps", "-A", "-o", "pcpu,comm"], text=True))
    result = dict(metadata=metadata, rows=[])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pools = {}
    context = bench.mp.get_context("spawn")
    rng = random.Random(metadata["randomized_order_seed"])
    try:
        with bench.threadpool_limits(limits=1):
            metadata["detected_threadpools"] = bench.threadpool_info()
            for count in counts:
                if count == 1:
                    continue
                start = time.perf_counter()
                barrier = context.Barrier(count + 1)
                pool = bench.ProcessPoolExecutor(count, mp_context=context,
                    initializer=bench.initialize_worker, initargs=(work, barrier))
                pools[count] = pool
                futures = [pool.submit(bench.worker_probe, i) for i in range(count)]
                barrier.wait(timeout=120)
                for future in futures:
                    future.result(timeout=120)
                metadata["python_pool_setup"][str(count)] = dict(milliseconds=(time.perf_counter() - start) * 1000,
                    workers=[process.pid for process in pool._processes.values()])
            for count in counts:
                bench.rust._engine(count)
            for name, (operation, batch) in work.items():
                for group in ("single", "batch"):
                    jobs = batch[:1] if group == "single" else batch
                    print(f"Measuring {name} {group} ...", flush=True)
                    validate, validation_report = density_validation(name, jobs)
                    original = bench.compare
                    try:
                        bench.compare = validate
                        row = bench.benchmark_case(name, operation, jobs, counts, pools,
                                                   args.samples, args.target_ms, rng)
                    finally:
                        bench.compare = original
                    row.update(group=group, validation=validation_report(),
                        input=dict(q_points=len(jobs[0][0].data.x), background_points=len(jobs[0][0].bkg.x),
                            config=jobs[0][1].model_dump(mode="json"),
                            background_scales=[job[0].bkg_scaling for job in jobs]))
                    result["rows"].append(row)
                    args.output.with_suffix(".progress.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
                    print(name, group, {mode: round(t["median_ms"], 3) for mode, t in row["timings"].items()}, flush=True)
    finally:
        for pool in pools.values():
            pool.shutdown(wait=True, cancel_futures=True)
    for name, expected in fingerprints.items():
        assert bench.sha(bench.ROOT / name) == expected, "Source changed while measuring: " + name
    assert bench.sha(extension) == metadata["extension_sha256"]
    metadata.update(finished_utc=datetime.now(timezone.utc).isoformat(),
                    background_load_after=subprocess.check_output(["ps", "-A", "-o", "pcpu,comm"], text=True))
    result["passed_with_recorded_qualification"] = True
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    args.output.with_suffix(".progress.json").unlink(missing_ok=True)
    print("Fit checks passed with the accepted density qualification; Rust thread counts agree exactly.", flush=True)


if __name__ == "__main__":
    main()
