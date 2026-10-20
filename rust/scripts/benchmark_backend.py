"""Benchmark public Python and Rust/NumPy APIs with identical prepared inputs.

Run after installing a release Glassure wheel with its legacy extra:
uv run --with threadpoolctl python rust/scripts/benchmark_backend.py
"""
from __future__ import annotations

import os
for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
              "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import multiprocessing as mp
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from glassure import _glassure_numpy
import lmfit
import numpy as np
import scipy
from threadpoolctl import threadpool_info, threadpool_limits
from glassure import Pattern, rust
from glassure.calc import create_calculate_pdf_configs, calculate_pdf
from glassure.configuration import DACConfig, IntNormalization, OptimizeConfig
from glassure.methods import ExtrapolationMethod
from glassure.optimization import optimize_density
from glassure import set_backend

# These helpers label the legacy implementation as Python. Backend auto-selection
# must never turn that reference or its nested calls into the native engine.
set_backend("python")

DENSITY_OPTIONS = dict(method="gr", min_range=(.1, 1.), vary_bkg_scaling=False)
_WORK = None
_LIMIT = None


def workloads(pdf_jobs, density_jobs):
    cases = {}
    for stem, formula, density, qmax in (
        ("SiO2", "SiO2", 2.2, 17.), ("Mg2SiO4_ambient", "Mg2SiO4", 2.9, 20.)
    ):
        raw = Pattern.from_file(str(ROOT / "tests/data" / (stem + ".xy")))
        background = Pattern.from_file(str(ROOT / "tests/data" / (stem + "_bkg.xy")))
        data, config = create_calculate_pdf_configs(raw, formula, density, background)
        t = config.transform
        t.q_min = 1.; t.q_max = qmax; t.r_min = 1e-13
        t.normalization.q_cutoff = 5.
        t.extrapolation.method = ExtrapolationMethod.LINEAR
        for kind in ("base", "combined", "density"):
            c = config.model_copy(deep=True)
            operation = "density" if kind == "density" else "pdf"
            if kind == "combined":
                c.transform.normalization.multiple_scattering = True
                c.transform.normalization.container_scattering = {"C": 1}
                c.transform.normalization.dac = DACConfig(initial_thickness=40., sample_thickness=20.)
                c.transform.kn_correction = True; c.transform.wavelength = .29
                c.transform.extrapolation.method = ExtrapolationMethod.SPLINE
                c.transform.use_modification_fcn = True
                c.optimize = OptimizeConfig(r_cutoff=1.4, iterations=3, use_modification_fcn=True)
            elif kind == "density":
                c.transform.normalization = IntNormalization()
                c.optimize = OptimizeConfig(r_cutoff=1.4, iterations=3)
            jobs = []
            for i in range(density_jobs if kind == "density" else pdf_jobs):
                # Independent settings and outputs, with no repeated-result cache.
                d = data.model_copy(); d.bkg_scaling = .98 + .04 * i / max(1, (density_jobs if kind == "density" else pdf_jobs) - 1)
                jobs.append((d, c.model_copy(deep=True)))
            cases[formula + "_" + kind] = (operation, jobs)
    return cases


def python_one(operation, job):
    if operation == "pdf":
        return calculate_pdf(*job)
    # The reference mutates the background scale. A shallow wrapper isolates that
    # mutation without copying the numerical arrays or changing subsequent starts.
    return optimize_density(job[0].model_copy(), job[1], **DENSITY_OPTIONS)


def initialize_worker(work, barrier):
    global _WORK, _LIMIT
    _WORK = work
    _LIMIT = threadpool_limits(limits=1)
    barrier.wait(timeout=120)


def worker_probe(_):
    return os.getpid()


def worker_job(key):
    name, index = key
    operation, jobs = _WORK[name]
    return python_one(operation, jobs[index])


def compare(operation, actual, expected, exact=False):
    assert len(actual) == len(expected)
    maximum = 0.
    for a, e in zip(actual, expected, strict=True):
        if operation == "pdf":
            pairs = [(getattr(getattr(a, name), axis), getattr(getattr(e, name), axis))
                     for name in ("sq", "fr", "gr") for axis in ("x", "y")]
            for x, y in pairs:
                if exact:
                    np.testing.assert_array_equal(x, y)
                else:
                    np.testing.assert_allclose(x, y, atol=1e-8, rtol=1e-8)
                maximum = max(maximum, float(np.max(np.abs(x - y))))
        else:
            for index, (x, y) in enumerate(zip(a, e, strict=True)):
                if y is None:
                    assert x is None
                    continue
                if exact:
                    assert x == y
                else:
                    np.testing.assert_allclose(x, y, atol=1e-5,
                                               rtol=1e-3 if index in (1, 3) else 1e-6)
                maximum = max(maximum, abs(x - y))
    return maximum


def timed(function, repeats):
    elapsed, last = 0, None
    for _ in range(repeats):
        start = time.perf_counter_ns()
        value = function()
        elapsed += time.perf_counter_ns() - start
        last = value  # Dispose of the previous result outside the timed interval.
    return elapsed / repeats / 1e6, last


def blocked_json(*args, **kwargs):
    raise AssertionError("JSON conversion entered the NumPy calculation path")


def benchmark_case(name, operation, jobs, counts, pools, samples, target_ms, rng):
    is_single = len(jobs) == 1
    modes = {"python_serial": lambda: [python_one(operation, job) for job in jobs]}
    for count in ([1] if is_single else counts):
        if operation == "pdf":
            modes[f"rust_{count}"] = (lambda: [rust.calculate_pdf(*jobs[0])]) if is_single else (
                lambda count=count: rust.calculate_batch(jobs, threads=count))
        else:
            modes[f"rust_{count}"] = (lambda: [rust.optimize_density(*jobs[0], **DENSITY_OPTIONS)]) if is_single else (
                lambda count=count: rust.optimize_density_batch(jobs, threads=count, **DENSITY_OPTIONS))
    if not is_single:
        for count, pool in pools.items():
            modes[f"python_processes_{count}"] = lambda pool=pool: list(
                pool.map(worker_job, ((name, i) for i in range(len(jobs))), chunksize=1))
    expected = None
    rust_serial = None
    timings = {}
    for mode, function in modes.items():
        if mode.startswith("rust_"):
            with patch("json.dumps", blocked_json), patch("json.loads", blocked_json):
                duration, warm = timed(function, 1)
        else:
            duration, warm = timed(function, 1)
        if expected is None:
            expected = warm
        error = compare(operation, warm, expected)
        if mode.startswith("rust_"):
            if rust_serial is None:
                rust_serial = warm
            else:
                compare(operation, warm, rust_serial, exact=True)
        timings[mode] = dict(warmup_ms=duration, repetitions_per_sample=min(500, max(1, math.ceil(target_ms / max(duration, .001)))),
                             samples_ms=[], max_abs_vs_python=error)
    orders = []
    for _ in range(samples):
        order = list(modes); rng.shuffle(order); orders.append(order)
        for mode in order:
            timing = timings[mode]
            elapsed, last = timed(modes[mode], timing["repetitions_per_sample"])
            timing["samples_ms"].append(elapsed)
            timing["max_abs_vs_python"] = max(timing["max_abs_vs_python"], compare(operation, last, expected))
            if mode.startswith("rust_"):
                compare(operation, last, rust_serial, exact=True)
    for timing in timings.values():
        values = timing["samples_ms"]
        timing.update(median_ms=statistics.median(values), min_ms=min(values), max_ms=max(values),
                      q25_ms=float(np.quantile(values, .25)), q75_ms=float(np.quantile(values, .75)))
    return {"case": name, "operation": operation, "jobs": len(jobs), "timings": timings, "measurement_order": orders}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hardware():
    result = dict(platform=platform.platform(), logical_cpus=os.cpu_count())
    if sys.platform == "darwin":
        for key in ("machdep.cpu.brand_string", "hw.physicalcpu", "hw.memsize", "hw.perflevel0.physicalcpu", "hw.perflevel1.physicalcpu"):
            value = subprocess.run(["sysctl", "-n", key], capture_output=True, text=True)
            if value.returncode == 0:
                result[key] = value.stdout.strip()
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--samples", type=int, default=7)
    p.add_argument("--target-ms", type=float, default=100.)
    p.add_argument("--pdf-jobs", type=int, default=64)
    p.add_argument("--density-jobs", type=int, default=16)
    p.add_argument("--workers", type=int, nargs="+", default=[1, 4, min(os.cpu_count() or 1, 64)])
    p.add_argument("--cases", nargs="+")
    p.add_argument("--include-density", action="store_true", help="Also time density fits; strict parameter parity is required")
    p.add_argument("--output", type=Path, default=ROOT / "rust/benchmarks/backend-results.json")
    args = p.parse_args()
    if args.samples < 3 or not math.isfinite(args.target_ms) or args.target_ms <= 0:
        p.error("Require >=3 samples and finite positive target-ms")
    if not 2 <= args.pdf_jobs <= 1024 or not 2 <= args.density_jobs <= 1024 or any(not 1 <= n <= 64 for n in args.workers):
        p.error("Job counts must be 2..1024 and worker counts 1..64")
    work = workloads(args.pdf_jobs, args.density_jobs)
    if args.cases:
        if set(args.cases) - work.keys():
            p.error("Unknown case")
        work = {name: work[name] for name in args.cases}
    elif not args.include_density:
        work = {name: item for name, item in work.items() if item[0] == "pdf"}
    counts = sorted(set([1] + args.workers))
    binaries = sorted(Path(_glassure_numpy.__file__).parent.glob("*.so")) + sorted(Path(_glassure_numpy.__file__).parent.glob("*.pyd"))
    if len(binaries) != 1:
        raise RuntimeError("Cannot identify installed native extension")
    files = sorted(set((ROOT / "rust").rglob("*.rs")) | set((ROOT / "glassure").rglob("*.py")) |
                   set((ROOT / "glassure/data").rglob("*.csv")) | set((ROOT / "rust").rglob("Cargo.toml")) |
                   set((ROOT / "rust/glassure-core/data").rglob("*.bin")) | {ROOT / "Cargo.toml", ROOT / "Cargo.lock", Path(__file__)})
    for stem in ("SiO2", "Mg2SiO4_ambient"):
        files += [ROOT / "tests/data" / (stem + suffix + ".xy") for suffix in ("", "_bkg")]
    fingerprints = {str(path.relative_to(ROOT)): sha(path) for path in files}
    result = dict(metadata=dict(created_utc=datetime.now(timezone.utc).isoformat(), hardware=hardware(),
        python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__, lmfit=lmfit.__version__,
        native_distribution=importlib.metadata.version("glassure"), extension_path=str(binaries[0]), extension_sha256=sha(binaries[0]),
        rustc=subprocess.check_output(["rustc", "--version"], text=True).strip(), source_sha256=fingerprints,
        git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        source_tree_dirty=bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
        samples=args.samples, target_sample_ms=args.target_ms, workers=counts, randomized_order_seed=20261019,
        requested_blas_threads=1, scattering_source="brown_hubbell", python_pool_setup={},
        background_load_before=subprocess.check_output(["ps", "-A", "-o", "pcpu,comm"], text=True)), rows=[])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pools = {}
    context = mp.get_context("spawn")
    rng = random.Random(20261019)
    try:
        with threadpool_limits(limits=1):
            result["metadata"]["detected_threadpools"] = threadpool_info()
            for count in counts:
                if count == 1:
                    continue
                start = time.perf_counter()
                barrier = context.Barrier(count + 1)
                pool = ProcessPoolExecutor(count, mp_context=context, initializer=initialize_worker, initargs=(work, barrier))
                pools[count] = pool
                futures = [pool.submit(worker_probe, i) for i in range(count)]
                barrier.wait(timeout=120)
                for future in futures:
                    future.result(timeout=120)
                result["metadata"]["python_pool_setup"][str(count)] = dict(milliseconds=(time.perf_counter() - start) * 1000,
                    workers=[process.pid for process in pool._processes.values()])
            # Create and retain every Rust executor before warm calculation timing.
            for count in counts:
                rust._engine(count)
            for name, (operation, jobs) in work.items():
                for group in ("single", "batch"):
                    print(f"Measuring {name} {group} ...", flush=True)
                    row = benchmark_case(name, operation, jobs[:1] if group == "single" else jobs,
                                         counts, pools, args.samples, args.target_ms, rng)
                    row["group"] = group
                    row["input"] = dict(q_points=len(jobs[0][0].data.x), background_points=len(jobs[0][0].bkg.x),
                        config=jobs[0][1].model_dump(mode="json"), background_scales=[job[0].bkg_scaling for job in (jobs[:1] if group == "single" else jobs)])
                    result["rows"].append(row)
                    args.output.with_suffix(".progress.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
                    print(name, group, {mode: round(t["median_ms"], 3) for mode, t in row["timings"].items()}, flush=True)
    finally:
        for pool in pools.values():
            pool.shutdown(wait=True, cancel_futures=True)
    for name, expected in fingerprints.items():
        assert sha(ROOT / name) == expected, "Source changed while measuring: " + name
    assert sha(binaries[0]) == result["metadata"]["extension_sha256"]
    result["metadata"]["finished_utc"] = datetime.now(timezone.utc).isoformat()
    result["metadata"]["background_load_after"] = subprocess.check_output(["ps", "-A", "-o", "pcpu,comm"], text=True)
    result["passed"] = True
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("Numerical agreement, deterministic Rust results and source fingerprints passed.", flush=True)


if __name__ == "__main__":
    main()
