//! Independent PDF/density jobs, with deterministic output order and per-job errors.
//! Native executors own a bounded Rayon pool. Ordinary WASM supports serial jobs;
//! browser multicore scheduling can distribute independent jobs to separate workers.
use crate::density::{optimize_density, DensityRequest, DensityResult};
use crate::request::{calculate, Request, Response};
use serde::{Deserialize, Serialize};
#[cfg(not(target_arch = "wasm32"))]
use {
    rayon::prelude::*,
    std::sync::{Arc, Mutex},
};

const MAX_JOBS: usize = 1024;
const MAX_THREADS: usize = 64;

#[derive(Clone, Deserialize, Serialize)]
#[serde(
    tag = "operation",
    content = "request",
    rename_all = "snake_case",
    deny_unknown_fields
)]
pub enum Job {
    /// One complete PDF calculation.
    Calculate(Request),
    /// One density/background fit, including its final PDF.
    Density(DensityRequest),
}
impl Job {
    fn calculation_mut(&mut self) -> &mut Request {
        match self {
            Self::Calculate(req) => req,
            Self::Density(req) => &mut req.calculation,
        }
    }
    fn run(self) -> Item {
        match self {
            Self::Calculate(req) => match calculate(req) {
                Ok(result) => Item::Success {
                    output: Box::new(JobOutput::Calculate(result)),
                },
                Err(error) => Item::Error {
                    operation: "calculate",
                    error,
                },
            },
            Self::Density(req) => match optimize_density(req) {
                Ok(result) => Item::Success {
                    output: Box::new(JobOutput::Density(result)),
                },
                Err(error) => Item::Error {
                    operation: "density",
                    error,
                },
            },
        }
    }
    fn operation(&self) -> &'static str {
        match self {
            Self::Calculate(_) => "calculate",
            Self::Density(_) => "density",
        }
    }
}

#[derive(Serialize)]
#[serde(tag = "operation", content = "result", rename_all = "snake_case")]
/// Successful output, tagged with its operation in JSON.
pub enum JobOutput {
    /// Complete PDF curves and normalization metadata.
    Calculate(Response),
    /// Fit parameters, diagnostics and final PDF curves.
    Density(DensityResult),
}
#[derive(Serialize)]
#[serde(tag = "status", rename_all = "snake_case")]
/// Per-job outcome. A successful batch call can contain `Error` entries.
pub enum Item {
    /// Calculation/fit completed successfully.
    Success {
        /// Operation-specific output, boxed to keep batch entries small.
        output: Box<JobOutput>,
    },
    /// This item failed; other jobs continue.
    Error {
        /// `"calculate"` or `"density"`.
        operation: &'static str,
        /// Validation, numerical or convergence error message.
        error: String,
    },
}
#[derive(Serialize)]
/// Ordered batch/sweep output with execution metadata.
pub struct ExecutionReport {
    /// Effective executor size (not a guarantee that every worker was busy).
    pub threads: usize,
    /// True when more than one thread and more than one item were available.
    pub parallel: bool,
    /// One outcome per input, in exactly the input order.
    pub items: Vec<Item>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
/// Serializable request for up to 1024 independent jobs.
pub struct BatchRequest {
    /// Jobs may mix calculations and density fits; empty batches are valid.
    pub jobs: Vec<Job>,
    /// 0 selects available processors (up to 64); 1 forces serial execution.
    #[serde(default)]
    pub threads: usize,
}
#[derive(Clone, Default, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
/// Overrides applied independently to a cloned base job. `None` retains its value.
/// For density jobs, `density` changes the initial guess, not the fixed answer.
pub struct SweepPoint {
    /// Mass density (or fit starting value), g/cm³.
    pub density: Option<f64>,
    /// Background scale (or fit starting scale).
    pub background_scale: Option<f64>,
    /// Upper strict Q crop bound, Å⁻¹.
    pub q_max: Option<f64>,
    /// S(Q) optimization cutoff, Å; requires enabled optimization on the base job.
    pub r_cutoff: Option<f64>,
}
impl SweepPoint {
    fn apply(&self, job: &mut Job) -> Result<(), String> {
        let req = job.calculation_mut();
        if let Some(value) = self.density {
            req.density = value;
        }
        if let Some(value) = self.background_scale {
            req.background_scale = value;
        }
        if let Some(value) = self.q_max {
            req.q_max = value;
        }
        if let Some(value) = self.r_cutoff {
            req.optimize
                .as_mut()
                .ok_or("r_cutoff sweep needs S(Q) optimization settings")?
                .r_cutoff = value;
        }
        Ok(())
    }
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
/// Up to 1024 independent overrides of a calculation or density-fit job.
pub struct SweepRequest {
    /// Original job; never mutated by a sweep.
    pub base: Job,
    /// Ordered overrides; this is an explicit list, not an implicit Cartesian grid.
    pub points: Vec<SweepPoint>,
    #[serde(default)]
    /// Native worker count: 0 for available CPUs (up to 64), 1 for serial.
    pub threads: usize,
}

/// Reuse one executor over many batches. Only independent jobs are parallelized;
/// each calculation/optimizer keeps the same arithmetic and sequential iterations.
pub struct Executor {
    threads: usize,
    #[cfg(not(target_arch = "wasm32"))]
    pool: Option<rayon::ThreadPool>,
}
impl Executor {
    /// Create a reusable native Rayon pool. 0 selects available CPUs (up to 64),
    /// 1 executes serially; values above 64 are errors. WASM accepts 0/1 only
    /// and executes serially; distribute jobs across Web Workers for multicore.
    pub fn new(threads: usize) -> Result<Self, String> {
        if threads > MAX_THREADS {
            return Err("Thread count exceeds limit 64".into());
        }
        #[cfg(target_arch = "wasm32")]
        {
            if threads > 1 {
                return Err("This WASM build supports one thread; use separate Web Workers for parallel jobs".into());
            }
            Ok(Self { threads: 1 })
        }
        #[cfg(not(target_arch = "wasm32"))]
        {
            let threads = if threads == 0 {
                std::thread::available_parallelism()
                    .map(usize::from)
                    .unwrap_or(1)
                    .min(MAX_THREADS)
            } else {
                threads
            };
            let pool = if threads == 1 {
                None
            } else {
                Some(
                    rayon::ThreadPoolBuilder::new()
                        .num_threads(threads)
                        .thread_name(|i| format!("glassure-{i}"))
                        .build()
                        .map_err(|e| format!("Could not create calculation pool: {e}"))?,
                )
            };
            Ok(Self { threads, pool })
        }
    }
    /// Effective executor size after resolving automatic selection.
    pub fn threads(&self) -> usize {
        self.threads
    }
    fn map<T, F>(&self, values: Vec<T>, function: F) -> Vec<Item>
    where
        T: Send,
        F: Fn(T) -> Item + Send + Sync,
    {
        #[cfg(not(target_arch = "wasm32"))]
        if let Some(pool) = &self.pool {
            // Indexed parallel collection preserves input order, regardless of
            // which job finishes first. There are no floating-point reductions.
            return pool.install(|| values.into_par_iter().map(function).collect());
        }
        values.into_iter().map(function).collect()
    }
    fn report(&self, items: Vec<Item>) -> ExecutionReport {
        ExecutionReport {
            threads: self.threads,
            parallel: self.threads > 1 && items.len() > 1,
            items,
        }
    }
    /// Consume independent jobs, returning outcomes in input order.
    /// More than 1024 jobs is a batch-level error. Individual calculation errors
    /// are retained in [`ExecutionReport::items`] instead of failing the batch.
    pub fn batch(&self, jobs: Vec<Job>) -> Result<ExecutionReport, String> {
        validate_count(jobs.len())?;
        Ok(self.report(self.map(jobs, Job::run)))
    }
    /// Clone the base as each job starts, apply an override and run it.
    /// Input order is retained; invalid overrides become per-item errors. The
    /// base is unchanged. More than 1024 points is a batch-level error.
    pub fn sweep(&self, base: &Job, points: Vec<SweepPoint>) -> Result<ExecutionReport, String> {
        validate_count(points.len())?;
        // Clone the shared patterns only when a job starts, rather than building
        // a whole grid of copies in advance. Memory scales with active workers.
        Ok(self.report(self.map(points, |point| {
            let mut job = base.clone();
            match point.apply(&mut job) {
                Ok(()) => job.run(),
                Err(error) => Item::Error {
                    operation: base.operation(),
                    error,
                },
            }
        })))
    }
}
fn validate_count(count: usize) -> Result<(), String> {
    if count > MAX_JOBS {
        Err("Job count exceeds limit 1024".into())
    } else {
        Ok(())
    }
}

#[cfg(not(target_arch = "wasm32"))]
type CachedPool = Mutex<Option<(usize, Arc<Executor>)>>;
#[cfg(not(target_arch = "wasm32"))]
static EXECUTOR: CachedPool = Mutex::new(None);

/// The JSON bridge retains the most recently selected pool, without growing a
/// process-wide cache for every possible thread count. In-flight calls own Arcs.
#[cfg(not(target_arch = "wasm32"))]
fn executor(threads: usize, count: usize) -> Result<Arc<Executor>, String> {
    let requested = if threads == 0 {
        std::thread::available_parallelism()
            .map(usize::from)
            .unwrap_or(1)
            .min(MAX_THREADS)
    } else {
        threads
    };
    if requested > MAX_THREADS {
        return Err("Thread count exceeds limit 64".into());
    }
    let effective = requested.min(count.max(1));
    let mut cached = EXECUTOR
        .lock()
        .map_err(|_| "Calculation pool lock poisoned")?;
    if let Some((key, value)) = &*cached {
        if *key == effective {
            return Ok(Arc::clone(value));
        }
    }
    let value = Arc::new(Executor::new(effective)?);
    *cached = Some((effective, Arc::clone(&value)));
    Ok(value)
}
#[cfg(target_arch = "wasm32")]
fn executor(threads: usize, _count: usize) -> Result<Executor, String> {
    Executor::new(threads)
}

/// Run an ordered batch using a cached native executor, capped to job count.
/// Prefer an explicitly retained [`Executor`] when controlling pool lifetime.
pub fn calculate_batch(req: BatchRequest) -> Result<ExecutionReport, String> {
    validate_count(req.jobs.len())?;
    executor(req.threads, req.jobs.len())?.batch(req.jobs)
}
/// Run explicit overrides using a cached executor; see [`Executor::sweep`].
pub fn parameter_sweep(req: SweepRequest) -> Result<ExecutionReport, String> {
    validate_count(req.points.len())?;
    executor(req.threads, req.points.len())?.sweep(&req.base, req.points)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;
    #[test]
    fn limits_and_empty_batch() {
        assert!(Executor::new(65).is_err());
        let executor = Executor::new(1).unwrap();
        assert!(executor.batch(Vec::new()).unwrap().items.is_empty());
        assert!(validate_count(1025).is_err());
    }
    #[test]
    fn indexed_map_preserves_order_and_uses_multiple_workers() {
        let executor = Executor::new(4).unwrap();
        let seen = Mutex::new(HashSet::new());
        let items = executor.map((0..32).collect(), |i| {
            seen.lock().unwrap().insert(std::thread::current().id());
            std::thread::sleep(std::time::Duration::from_millis(2));
            Item::Error {
                operation: "test",
                error: i.to_string(),
            }
        });
        assert!(seen.into_inner().unwrap().len() > 1);
        for (i, item) in items.iter().enumerate() {
            assert!(matches!(item, Item::Error {error, ..} if error == &i.to_string()));
        }
    }
}
