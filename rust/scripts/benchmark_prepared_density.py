"""Interleave original Rust, prepared Rust and Python density-fit measurements.

Requires the original release wheel saved before changing the core. Both native
extensions load side by side, using identical public NumPy adapter code.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import random
import sys
import time
import zipfile
from unittest.mock import patch

import glassure

import benchmark_backend as b
from benchmark_density import density_validation


def original_adapter(wheel, expected_sha):
    destination = b.ROOT / "target/density-prepared/loaded-baseline"
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel) as archive:
        name = next(n for n in archive.namelist() if n.endswith((".so", ".pyd")))
        binary = destination / Path(name).name
        binary.write_bytes(archive.read(name))
    assert b.sha(binary) == expected_sha, "Baseline wheel differs from the recorded original engine"
    spec = importlib.util.spec_from_file_location("_glassure_before._glassure_numpy", binary)
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    adapter_spec = importlib.util.spec_from_file_location("_glassure_before_adapter", b.ROOT / "glassure/rust.py")
    adapter = importlib.util.module_from_spec(adapter_spec)
    # The adapter now imports its native extension relative to glassure.
    adapter.__package__ = "glassure"
    with patch.dict(sys.modules, {"glassure._glassure_numpy": native}), patch.object(
        glassure, "_glassure_numpy", native
    ):
        adapter_spec.loader.exec_module(adapter)
    return adapter, binary


def exact_result(actual, expected, stats):
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys()
        for key in expected:
            exact_result(actual[key], expected[key], stats)
    elif isinstance(expected, b.np.ndarray):
        b.np.testing.assert_array_equal(actual.view(b.np.uint64), expected.view(b.np.uint64))
        stats["arrays"] += 1
        stats["array_values"] += int(expected.size)
    elif isinstance(expected, float):
        assert actual.hex() == expected.hex()
    else:
        assert actual == expected


def case(name, jobs, counts, pools, before, args, rng):
    modes = {"python_serial": lambda: [b.python_one("density", job) for job in jobs]}
    for label, adapter in (("before", before), ("after", b.rust)):
        for count in ([1] if len(jobs) == 1 else counts):
            if len(jobs) == 1:
                modes[f"rust_{label}_{count}"] = lambda adapter=adapter: [adapter.optimize_density(*jobs[0], **b.DENSITY_OPTIONS)]
            else:
                modes[f"rust_{label}_{count}"] = lambda adapter=adapter, count=count: adapter.optimize_density_batch(jobs, threads=count, **b.DENSITY_OPTIONS)
    if len(jobs) > 1:
        for count, pool in pools.items():
            modes[f"python_processes_{count}"] = lambda pool=pool: list(pool.map(b.worker_job, ((name, i) for i in range(len(jobs))), chunksize=1))
    validate, validation_report = density_validation(name, jobs)
    expected = original = None
    timings = {}
    for mode, function in modes.items():
        if mode.startswith("rust_"):
            with b.patch("json.dumps", b.blocked_json), b.patch("json.loads", b.blocked_json):
                duration, value = b.timed(function, 1)
        else:
            duration, value = b.timed(function, 1)
        if expected is None:
            expected = value
        error = validate("density", value, expected)
        if mode.startswith("rust_"):
            if original is None:
                original = value
            b.compare("density", value, original, exact=True)
        timings[mode] = dict(warmup_ms=duration, samples_ms=[], max_abs_vs_python=error,
            repetitions_per_sample=min(500, max(1, b.math.ceil(args.target_ms / max(duration, .001)))))
    orders = []
    for _ in range(args.samples):
        order = list(modes)
        rng.shuffle(order)
        orders.append(order)
        for mode in order:
            timing = timings[mode]
            duration, value = b.timed(modes[mode], timing["repetitions_per_sample"])
            timing["samples_ms"].append(duration)
            timing["max_abs_vs_python"] = max(timing["max_abs_vs_python"], validate("density", value, expected))
            if mode.startswith("rust_"):
                b.compare("density", value, original, exact=True)
    for timing in timings.values():
        values = timing["samples_ms"]
        timing.update(median_ms=b.statistics.median(values), min_ms=min(values), max_ms=max(values),
            q25_ms=float(b.np.quantile(values, .25)), q75_ms=float(b.np.quantile(values, .75)))
    return dict(case=name, jobs=len(jobs), timings=timings, validation=validation_report(),
        measurement_order=orders, exact_before_after=True,
        input=dict(config=jobs[0][1].model_dump(mode="json"), background_scales=[j[0].bkg_scaling for j in jobs]))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline-wheel", type=Path, required=True)
    p.add_argument("--baseline-report", type=Path, default=b.ROOT / "rust/benchmarks/density-results.json",
                   help="Report identifying the baseline wheel's extension and scientific inputs")
    p.add_argument("--samples", type=int, default=7)
    p.add_argument("--density-jobs", type=int, default=16)
    p.add_argument("--target-ms", type=float, default=100.)
    p.add_argument("--workers", type=int, nargs="+", default=[1, 4, min(b.os.cpu_count() or 1, 64)])
    p.add_argument("--output", type=Path, default=b.ROOT / "rust/benchmarks/density-prepared-results.json")
    args = p.parse_args()
    if args.samples < 3 or not b.math.isfinite(args.target_ms) or args.target_ms <= 0:
        p.error("Require >=3 samples and finite positive target duration")
    if not 2 <= args.density_jobs <= 1024 or any(not 1 <= n <= 64 for n in args.workers):
        p.error("Invalid job/worker counts")
    reference_path = args.baseline_report
    reference = json.loads(reference_path.read_text())
    before, before_binary = original_adapter(args.baseline_wheel, reference["metadata"]["extension_sha256"])
    for name, expected in reference["metadata"]["source_sha256"].items():
        if name.startswith(("glassure/", "tests/data/")):
            assert b.sha(b.ROOT / name) == expected, "Python reference/input changed: " + name
    metadata = dict(reference["metadata"])
    files = set((b.ROOT / "rust").rglob("*.rs")) | set((b.ROOT / "glassure").rglob("*.py")) | set((b.ROOT / "glassure/data").rglob("*.csv"))
    files |= set((b.ROOT / "rust").rglob("Cargo.toml")) | set((b.ROOT / "rust/glassure-core/data").rglob("*.bin"))
    files |= {Path(__file__), b.ROOT / "rust/scripts/benchmark_backend.py", b.ROOT / "rust/scripts/benchmark_density.py",
              b.ROOT / "rust/scripts/check_density_benchmark.py", b.ROOT / "Cargo.toml", b.ROOT / "Cargo.lock"}
    files |= {b.ROOT / name for name in reference["metadata"]["source_sha256"] if name.startswith("tests/data/")}
    fingerprints = {str(path.relative_to(b.ROOT)): b.sha(path) for path in sorted(files)}
    extension = Path(metadata["extension_path"])
    metadata.pop("finished_utc", None)
    metadata.pop("background_load_after", None)
    metadata.update(created_utc=datetime.now(timezone.utc).isoformat(), hardware=b.hardware(), source_sha256=fingerprints,
        baseline_report_sha256=b.sha(reference_path), baseline_wheel=str(args.baseline_wheel.resolve()), baseline_wheel_sha256=b.sha(args.baseline_wheel),
        baseline_extension_sha256=b.sha(before_binary), extension_sha256=b.sha(extension),
        baseline_source_sha256=reference["metadata"]["source_sha256"],
        samples=args.samples, workers=sorted(set([1] + args.workers)), target_sample_ms=args.target_ms, python_pool_setup={},
        background_load_before=b.subprocess.check_output(["ps", "-A", "-o", "pcpu,comm"], text=True))
    result = dict(metadata=metadata, rows=[])
    work = {name: item for name, item in b.workloads(64, args.density_jobs).items() if item[0] == "density"}
    checks = []
    with b.threadpool_limits(limits=1):
        for name, (_, jobs) in work.items():
            for i, job in enumerate(jobs):
                old = before._engine(1).density(before._density_request(*job, **b.DENSITY_OPTIONS))
                new = b.rust._engine(1).density(b.rust._density_request(*job, **b.DENSITY_OPTIONS))
                stats = dict(arrays=0, array_values=0)
                exact_result(new, old, stats)
                checks.append(dict(case=name, job=i, density=new["density"], density_error=new["density_error"],
                    evaluations=new["evaluations"], termination=new["termination"], sum_squared_residuals=new["sum_squared_residuals"],
                    exact=True, **stats))
    result["complete_result_checks"] = checks
    print(f"{len(checks)} complete native fit results, evaluation counts and termination reasons match exactly.", flush=True)
    pools = {}
    context = b.mp.get_context("spawn")
    rng = random.Random(metadata["randomized_order_seed"])
    counts = metadata["workers"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with b.threadpool_limits(limits=1):
            metadata["detected_threadpools"] = b.threadpool_info()
            for count in counts:
                if count == 1:
                    continue
                start = time.perf_counter()
                barrier = context.Barrier(count + 1)
                pool = b.ProcessPoolExecutor(count, mp_context=context, initializer=b.initialize_worker, initargs=(work, barrier))
                pools[count] = pool
                futures = [pool.submit(b.worker_probe, i) for i in range(count)]
                barrier.wait(timeout=120)
                for future in futures:
                    future.result(timeout=120)
                metadata["python_pool_setup"][str(count)] = dict(milliseconds=(time.perf_counter() - start)*1000,
                    workers=[process.pid for process in pool._processes.values()])
            for adapter in (before, b.rust):
                for count in counts:
                    adapter._engine(count)
            for name, (_, jobs) in work.items():
                for group in ("single", "batch"):
                    print(f"Measuring {name} {group} ...", flush=True)
                    row = case(name, jobs[:1] if group == "single" else jobs, counts, pools, before, args, rng)
                    row["group"] = group
                    result["rows"].append(row)
                    args.output.with_suffix(".progress.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
                    print(name, group, {key: round(v["median_ms"], 3) for key, v in row["timings"].items()}, flush=True)
    finally:
        for pool in pools.values():
            pool.shutdown(wait=True, cancel_futures=True)
    for name, expected in fingerprints.items():
        assert b.sha(b.ROOT / name) == expected, "Source changed while measuring: " + name
    assert b.sha(extension) == metadata["extension_sha256"]
    assert b.sha(before_binary) == metadata["baseline_extension_sha256"]
    metadata.update(finished_utc=datetime.now(timezone.utc).isoformat(),
        background_load_after=b.subprocess.check_output(["ps", "-A", "-o", "pcpu,comm"], text=True))
    result["passed_with_recorded_qualification"] = True
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    args.output.with_suffix(".progress.json").unlink(missing_ok=True)
    print("Original/prepared results and thread counts match exactly; Python qualification retained.", flush=True)


if __name__ == "__main__":
    main()
