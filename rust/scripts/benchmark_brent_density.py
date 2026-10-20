"""Compare analytic TRF, bounded Brent and locally bracketed Brent through NumPy.

Keep full-interval failures of TRF parity visible: these objectives are multimodal.
Independent Python/SciPy calculations verify each Brent result, including the
different, worse minimum selected by the full-interval search.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import random
import time

import benchmark_backend as b
from check_density_benchmark import objective
from scipy.optimize import minimize_scalar

ALGORITHMS = ("lsq", "brent_local", "brent")


def scalar_reference(job, algorithm):
    f = lambda rho: objective(job, (rho, 0., job[0].bkg_scaling, 0.))
    if algorithm == "brent":
        result = minimize_scalar(f, method="bounded", bounds=(1e-12, 100.), options={"xatol": 1e-8, "maxiter": 500})
    else:
        rho = job[1].sample.density
        # SciPy independently brackets from the same start; no fitted answer or
        # interval from either native method is passed to this reference.
        result = minimize_scalar(f, method="brent", bracket=(rho, 1.1*rho), options={"xtol": 1e-8, "maxiter": 500})
    assert result.success
    return dict(density=float(result.x), objective=float(result.fun), evaluations=int(result.nfev))


def audit(work, previous):
    checks, fixtures = [], []
    prior = {(c["case"], c["job"]): c for c in previous["complete_result_checks"]}
    for name, (_, jobs) in work.items():
        for i, job in enumerate(jobs):
            expected = b.python_one("density", job)
            outputs = {a: b.rust._engine(1).density(b.rust._density_request(*job, **b.DENSITY_OPTIONS, optimization_method=a)) for a in ALGORITHMS}
            trf = outputs["lsq"]
            fit = b.rust._fit_tuple(trf)
            b.compare("density", [fit], [expected])
            old = prior[name, i]
            assert list(fit) == old["after"] and trf["evaluations"] == old["after_evaluations"]
            assert trf["termination"] == old["after_termination"] and trf["sum_squared_residuals"] == old["after_sse"]
            reference_cost = objective(job, fit)
            methods = {}
            for a, value in outputs.items():
                fit = b.rust._fit_tuple(value)
                python_cost = objective(job, fit)
                b.np.testing.assert_allclose(value["sum_squared_residuals"], python_cost, rtol=1e-9, atol=1e-14)
                try:
                    b.compare("density", [fit], [expected])
                    strict = True
                except AssertionError:
                    strict = False
                entry = dict(fit=list(fit), evaluations=value["evaluations"], termination=value["termination"],
                    objective=value["sum_squared_residuals"], objective_evaluated_in_python=python_cost,
                    relative_objective_vs_trf=(python_cost-reference_cost)/reference_cost,
                    density_difference_vs_trf=abs(value["density"]-trf["density"]),
                    density_difference_in_trf_standard_errors=abs(value["density"]-trf["density"])/trf["density_error"],
                    strict_python_parameter_and_error_parity=strict)
                if a != "lsq":
                    scalar = scalar_reference(job, a)
                    b.np.testing.assert_allclose(value["density"], scalar["density"], atol=1e-5, rtol=1e-6)
                    b.np.testing.assert_allclose(python_cost, scalar["objective"], atol=1e-14, rtol=1e-9)
                    entry["independent_scipy"] = scalar
                    if a == "brent_local":
                        # Check quality, without pretending the different
                        # stopping points pass the old density tolerance.
                        assert python_cost <= reference_cost*(1.+1e-10)
                    entry["worse_than_trf"] = python_cost > reference_cost*(1.+1e-8)
                methods[a] = entry
                if i == 0:
                    request = b.rust._density_request(*job, **b.DENSITY_OPTIONS, optimization_method=a)
                    fixtures.append(dict(case=name+"_"+a, request=request,
                        expected=dict(fit=list(fit), objective=value["sum_squared_residuals"])))
            checks.append(dict(case=name, job=i, python=list(expected), methods=methods, trf_exact_previous=True))
    return checks, fixtures


def case(name, jobs, counts, pools, args, rng):
    modes = {"python_serial": lambda: [b.python_one("density", job) for job in jobs]}
    for algorithm in ALGORITHMS:
        for n in ([1] if len(jobs) == 1 else counts):
            if len(jobs) == 1:
                modes[f"rust_{algorithm}_{n}"] = lambda a=algorithm: [b.rust.optimize_density(*jobs[0], **b.DENSITY_OPTIONS, optimization_method=a)]
            else:
                modes[f"rust_{algorithm}_{n}"] = lambda a=algorithm, n=n: b.rust.optimize_density_batch(jobs, threads=n, **b.DENSITY_OPTIONS, optimization_method=a)
    if len(jobs) > 1:
        for n, pool in pools.items():
            modes[f"python_processes_{n}"] = lambda pool=pool: list(pool.map(b.worker_job, ((name,i) for i in range(len(jobs))), chunksize=1))
    timings, references = {}, {}
    for mode, function in modes.items():
        if mode.startswith("rust_"):
            with b.patch("json.dumps", b.blocked_json), b.patch("json.loads", b.blocked_json):
                duration, value = b.timed(function, 1)
        else:
            duration, value = b.timed(function, 1)
        family = mode.rsplit("_",1)[0] if mode.startswith("rust_") else "python"
        references.setdefault(family,value)
        b.compare("density", value, references[family], exact=True)
        timings[mode] = dict(samples_ms=[], warmup_ms=duration,
            repetitions_per_sample=min(500,max(1,b.math.ceil(args.target_ms/max(duration,.001)))))
    orders = []
    for _ in range(args.samples):
        order = list(modes); rng.shuffle(order); orders.append(order)
        for mode in order:
            t = timings[mode]
            duration, value = b.timed(modes[mode], t["repetitions_per_sample"])
            t["samples_ms"].append(duration)
            family = mode.rsplit("_",1)[0] if mode.startswith("rust_") else "python"
            b.compare("density", value, references[family], exact=True)
    for t in timings.values():
        values = t["samples_ms"]
        t.update(median_ms=b.statistics.median(values), min_ms=min(values), max_ms=max(values),
            q25_ms=float(b.np.quantile(values,.25)),q75_ms=float(b.np.quantile(values,.75)))
    return dict(case=name,jobs=len(jobs),timings=timings,measurement_order=orders,
        exact_across_threads_and_repeats=True,
        input=dict(config=jobs[0][1].model_dump(mode="json"),background_scales=[j[0].bkg_scaling for j in jobs]))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--samples",type=int,default=7)
    p.add_argument("--density-jobs",type=int,default=16)
    p.add_argument("--target-ms",type=float,default=100.)
    p.add_argument("--workers",type=int,nargs="+",default=[1,4,min(b.os.cpu_count() or 1,64)])
    p.add_argument("--output",type=Path,default=b.ROOT/"rust/benchmarks/density-brent-results.json")
    args = p.parse_args()
    if args.samples < 3 or not b.math.isfinite(args.target_ms) or args.target_ms <= 0 or args.density_jobs != 16 or any(not 1<=n<=64 for n in args.workers):
        p.error("Require >=3 samples, positive target duration, 16 audit jobs, and workers 1..64")
    counts = sorted(set([1]+args.workers))
    previous_path = b.ROOT/"rust/benchmarks/density-analytic-results.json"
    previous = json.loads(previous_path.read_text())
    for name,sha in previous["metadata"]["source_sha256"].items():
        if name.startswith(("glassure/","tests/data/")) and name != "glassure/rust.py":
            assert b.sha(b.ROOT/name) == sha, "Scientific Python/input changed: "+name
    extension = Path(importlib.util.find_spec("glassure._glassure_numpy").origin)
    files = set((b.ROOT/"rust").rglob("*.rs")) | set((b.ROOT/"rust").rglob("Cargo.toml"))
    files |= set((b.ROOT/"glassure").rglob("*.py")) | set((b.ROOT/"glassure/data").rglob("*.csv"))
    files |= set((b.ROOT/"rust/glassure-core/data").rglob("*.bin"))
    files |= {Path(__file__),b.ROOT/"rust/scripts/benchmark_backend.py",b.ROOT/"rust/scripts/check_density_benchmark.py",b.ROOT/"Cargo.lock",b.ROOT/"Cargo.toml",b.ROOT/"tests/test_rust_backend.py",b.ROOT/"rust/scripts/verify_brent.mjs",b.ROOT/"rust/glassure-core/THIRD_PARTY_NOTICES.md",b.ROOT/"rust/glassure-python/THIRD_PARTY_NOTICES.md"}
    files |= {b.ROOT/name for name in previous["metadata"]["source_sha256"] if name.startswith("tests/data/")}
    fingerprints = {str(f.relative_to(b.ROOT)):b.sha(f) for f in sorted(files)}
    metadata = dict(created_utc=datetime.now(timezone.utc).isoformat(),hardware=b.hardware(),
        python=b.platform.python_version(),numpy=b.np.__version__,scipy=b.scipy.__version__,lmfit=b.lmfit.__version__,
        extension_path=str(extension),extension_sha256=b.sha(extension),source_sha256=fingerprints,
        previous_trf_report_sha256=b.sha(previous_path),samples=args.samples,workers=counts,target_sample_ms=args.target_ms,
        random_seed=20261019,density_options=b.DENSITY_OPTIONS,bounds=[1e-12,100.],brent_xatol=1e-8,
        python_pool_setup={},background_load_before=b.subprocess.check_output(["ps","-A","-o","pcpu,comm"],text=True))
    work = {name:item for name,item in b.workloads(64,args.density_jobs).items() if item[0]=="density"}
    with b.threadpool_limits(limits=1):
        checks,fixtures = audit(work,previous)
    result = dict(metadata=metadata,complete_result_checks=checks,rows=[])
    print("32 TRF fits exactly retain prior results; both Brent variants checked independently against Python/SciPy.",flush=True)
    fixture_path = b.ROOT/"target/density-brent/wasm-fixtures.json"
    fixture_path.parent.mkdir(parents=True,exist_ok=True)
    fixture_path.write_text(json.dumps(fixtures,default=lambda x:x.tolist(),allow_nan=False)+"\n")
    metadata["wasm_fixture_sha256"] = b.sha(fixture_path)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    pools = {}
    rng = random.Random(metadata["random_seed"])
    context = b.mp.get_context("spawn")
    try:
        with b.threadpool_limits(limits=1):
            metadata["detected_threadpools"] = b.threadpool_info()
            for n in counts:
                b.rust._engine(n)
                if n == 1: continue
                start = time.perf_counter(); barrier = context.Barrier(n+1)
                pool = b.ProcessPoolExecutor(n,mp_context=context,initializer=b.initialize_worker,initargs=(work,barrier))
                pools[n] = pool
                futures = [pool.submit(b.worker_probe,i) for i in range(n)]
                barrier.wait(timeout=120)
                for f in futures: f.result(timeout=120)
                metadata["python_pool_setup"][str(n)] = dict(milliseconds=1000*(time.perf_counter()-start),workers=[p.pid for p in pool._processes.values()])
            for name,(_,jobs) in work.items():
                for group in ("single","batch"):
                    print("Measuring",name,group,flush=True)
                    row = case(name,jobs[:1] if group=="single" else jobs,counts,pools,args,rng)
                    row["group"] = group; result["rows"].append(row)
                    args.output.with_suffix(".progress.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
                    print({k:round(v["median_ms"],3) for k,v in row["timings"].items()},flush=True)
    finally:
        for pool in pools.values(): pool.shutdown(wait=True,cancel_futures=True)
    for name,sha in fingerprints.items(): assert b.sha(b.ROOT/name)==sha, "Source changed: "+name
    assert b.sha(extension)==metadata["extension_sha256"]
    metadata.update(finished_utc=datetime.now(timezone.utc).isoformat(),background_load_after=b.subprocess.check_output(["ps","-A","-o","pcpu,comm"],text=True))
    result["passed_with_recorded_solver_differences"] = True
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    args.output.with_suffix(".progress.json").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
