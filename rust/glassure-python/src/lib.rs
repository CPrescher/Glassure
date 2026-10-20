//! Native NumPy buffer bridge. Inputs are snapshotted before releasing the GIL;
//! returned Vec allocations are transferred to NumPy without element conversion.
use glassure_core::{
    density::{optimize_density, DensityRequest, DensityResult},
    parallel::{ExecutionReport, Executor, Item, Job, JobOutput, SweepPoint},
    request::{calculate, Dac, Normalization, Pattern, Request, Response},
    scattering::{Composition, Source},
    SqOptimization,
};
use numpy::{IntoPyArray, PyReadonlyArray1};
use pyo3::{
    exceptions::{PyKeyError, PyValueError},
    prelude::*,
    types::{PyDict, PyList},
};
use std::collections::BTreeMap;
mod operations;

macro_rules! field {
    ($dict:expr, $key:expr) => {
        $dict
            .get_item($key)?
            .ok_or_else(|| PyKeyError::new_err($key))?
            .extract()?
    };
}

fn keys(dict: &Bound<'_, PyDict>, allowed: &[&str]) -> PyResult<()> {
    for key in dict.keys().iter() {
        let name: String = key.extract()?;
        if !allowed.contains(&name.as_str()) {
            return Err(PyValueError::new_err(format!("Unsupported field: {name}")));
        }
    }
    Ok(())
}

fn composition(value: &Bound<'_, PyAny>) -> PyResult<Composition> {
    if let Ok(formula) = value.extract::<String>() {
        Ok(Composition::Formula(formula))
    } else {
        Ok(Composition::Amounts(
            value.extract::<BTreeMap<String, f64>>()?,
        ))
    }
}

fn pattern(dict: &Bound<'_, PyDict>) -> PyResult<Pattern> {
    keys(dict, &["x", "y"])?;
    let x = dict
        .get_item("x")?
        .ok_or_else(|| PyKeyError::new_err("x"))?;
    let y = dict
        .get_item("y")?
        .ok_or_else(|| PyKeyError::new_err("y"))?;
    let x: PyReadonlyArray1<'_, f64> = x.extract()?;
    let y: PyReadonlyArray1<'_, f64> = y.extract()?;
    // Iteration also handles strided/read-only arrays; no Python float objects.
    let x = x.as_array();
    let y = y.as_array();
    if x.len() != y.len() || !(2..=1_000_000).contains(&x.len()) {
        return Err(PyValueError::new_err("Invalid pattern shape"));
    }
    Ok(Pattern {
        x: x.iter().copied().collect(),
        y: y.iter().copied().collect(),
    })
}

fn request(dict: &Bound<'_, PyDict>) -> PyResult<Request> {
    keys(
        dict,
        &[
            "data",
            "background",
            "background_scale",
            "composition",
            "scattering_factor_source",
            "density",
            "q_min",
            "q_max",
            "r_min",
            "r_max",
            "r_step",
            "normalization",
            "incoherent",
            "lorch",
            "transform",
            "extrapolation",
            "kn_correction",
            "wavelength",
            "overlap",
            "replace",
            "s0",
            "smooth_factor",
            "optimize",
        ],
    )?;
    let norm: Bound<'_, PyDict> = field!(dict, "normalization");
    let method: String = field!(norm, "method");
    let normalization = match method.as_str() {
        "integral" => {
            keys(&norm, &["method", "attenuation"])?;
            Normalization::Integral {
                attenuation: field!(norm, "attenuation"),
            }
        }
        "fit" => {
            keys(
                &norm,
                &[
                    "method",
                    "q_cutoff",
                    "scaling",
                    "multiple",
                    "container",
                    "dac",
                ],
            )?;
            let container = norm
                .get_item("container")?
                .filter(|v| !v.is_none())
                .map(|v| composition(&v))
                .transpose()?;
            let dac = match norm.get_item("dac")?.filter(|v| !v.is_none()) {
                None => None,
                Some(value) => {
                    let value = value.cast::<PyDict>()?;
                    keys(value, &["initial_thickness", "sample_thickness"])?;
                    Some(Dac {
                        initial_thickness: field!(value, "initial_thickness"),
                        sample_thickness: field!(value, "sample_thickness"),
                    })
                }
            };
            Normalization::Fit {
                q_cutoff: field!(norm, "q_cutoff"),
                scaling: field!(norm, "scaling"),
                multiple: field!(norm, "multiple"),
                container,
                dac,
            }
        }
        _ => return Err(PyValueError::new_err("Unsupported normalization method")),
    };
    let optimize = match dict.get_item("optimize")?.filter(|v| !v.is_none()) {
        None => None,
        Some(value) => {
            let value = value.cast::<PyDict>()?;
            keys(
                value,
                &["method", "r_cutoff", "iterations", "lorch", "attenuation"],
            )?;
            Some(SqOptimization {
                method: field!(value, "method"),
                r_cutoff: field!(value, "r_cutoff"),
                iterations: field!(value, "iterations"),
                lorch: field!(value, "lorch"),
                attenuation: value
                    .get_item("attenuation")?
                    .map(|v| v.extract())
                    .transpose()?
                    .unwrap_or(1.0),
            })
        }
    };
    let data: Bound<'_, PyDict> = field!(dict, "data");
    let background = dict
        .get_item("background")?
        .filter(|v| !v.is_none())
        .map(|v| pattern(v.cast::<PyDict>()?))
        .transpose()?;
    let comp = dict
        .get_item("composition")?
        .ok_or_else(|| PyKeyError::new_err("composition"))?;
    Ok(Request {
        data: pattern(&data)?,
        background,
        normalization,
        optimize,
        composition: composition(&comp)?,
        scattering_factor_source: Source::parse(
            &dict
                .get_item("scattering_factor_source")?
                .map(|v| v.extract::<String>())
                .transpose()?
                .unwrap_or("brown_hubbell".into()),
        )
        .map_err(PyValueError::new_err)?,
        background_scale: field!(dict, "background_scale"),
        density: field!(dict, "density"),
        q_min: field!(dict, "q_min"),
        q_max: field!(dict, "q_max"),
        r_min: field!(dict, "r_min"),
        r_max: field!(dict, "r_max"),
        r_step: field!(dict, "r_step"),
        incoherent: field!(dict, "incoherent"),
        lorch: field!(dict, "lorch"),
        transform: field!(dict, "transform"),
        extrapolation: field!(dict, "extrapolation"),
        kn_correction: field!(dict, "kn_correction"),
        wavelength: field!(dict, "wavelength"),
        overlap: field!(dict, "overlap"),
        replace: field!(dict, "replace"),
        s0: field!(dict, "s0"),
        smooth_factor: dict
            .get_item("smooth_factor")?
            .map(|v| v.extract())
            .transpose()?
            .flatten(),
    })
}

fn output_pattern(py: Python<'_>, value: Pattern) -> PyResult<Bound<'_, PyDict>> {
    let result = PyDict::new(py);
    result.set_item("x", value.x.into_pyarray(py))?;
    result.set_item("y", value.y.into_pyarray(py))?;
    Ok(result)
}
fn output(py: Python<'_>, value: Response) -> PyResult<Bound<'_, PyDict>> {
    let result = PyDict::new(py);
    result.set_item("sq", output_pattern(py, value.sq)?)?;
    result.set_item("fr", output_pattern(py, value.fr)?)?;
    result.set_item("gr", output_pattern(py, value.gr)?)?;
    result.set_item("normalization", value.normalization)?;
    result.set_item("atomic_density", value.atomic_density)?;
    Ok(result)
}

fn density_request(value: &Bound<'_, PyDict>) -> PyResult<DensityRequest> {
    keys(
        value,
        &[
            "calculation",
            "method",
            "min_range",
            "vary_background",
            "background_limits",
            "algorithm",
            "max_evaluations",
        ],
    )?;
    let calculation: Bound<'_, PyDict> = field!(value, "calculation");
    Ok(DensityRequest {
        calculation: request(&calculation)?,
        method: field!(value, "method"),
        min_range: field!(value, "min_range"),
        vary_background: field!(value, "vary_background"),
        background_limits: field!(value, "background_limits"),
        algorithm: field!(value, "algorithm"),
        max_evaluations: field!(value, "max_evaluations"),
    })
}
fn job(value: &Bound<'_, PyDict>) -> PyResult<Job> {
    keys(value, &["operation", "request"])?;
    let operation: String = field!(value, "operation");
    let req: Bound<'_, PyDict> = field!(value, "request");
    match operation.as_str() {
        "calculate" => Ok(Job::Calculate(request(&req)?)),
        "density" => Ok(Job::Density(density_request(&req)?)),
        _ => Err(PyValueError::new_err("Unsupported job operation")),
    }
}
fn density_output(py: Python<'_>, value: DensityResult) -> PyResult<Bound<'_, PyDict>> {
    let result = PyDict::new(py);
    result.set_item("density", value.density)?;
    result.set_item("density_error", value.density_error)?;
    result.set_item("background_scale", value.background_scale)?;
    result.set_item("background_error", value.background_error)?;
    result.set_item("sum_squared_residuals", value.sum_squared_residuals)?;
    result.set_item("evaluations", value.evaluations)?;
    result.set_item("success", value.success)?;
    result.set_item("termination", value.termination)?;
    result.set_item("error_kind", value.error_kind)?;
    result.set_item("result", output(py, value.result)?)?;
    Ok(result)
}
fn execution_output(py: Python<'_>, report: ExecutionReport) -> PyResult<Bound<'_, PyDict>> {
    let items = PyList::empty(py);
    for item in report.items {
        let value = PyDict::new(py);
        match item {
            Item::Success { output: result } => {
                let wrapped = PyDict::new(py);
                match *result {
                    JobOutput::Calculate(result) => {
                        wrapped.set_item("operation", "calculate")?;
                        wrapped.set_item("result", output(py, result)?)?;
                    }
                    JobOutput::Density(result) => {
                        wrapped.set_item("operation", "density")?;
                        wrapped.set_item("result", density_output(py, result)?)?;
                    }
                }
                value.set_item("status", "success")?;
                value.set_item("output", wrapped)?;
            }
            Item::Error { operation, error } => {
                value.set_item("status", "error")?;
                value.set_item("operation", operation)?;
                value.set_item("error", error)?;
            }
        }
        items.append(value)?;
    }
    let result = PyDict::new(py);
    result.set_item("workers", report.threads)?;
    result.set_item("parallel", report.parallel)?;
    result.set_item("items", items)?;
    Ok(result)
}

#[pyclass]
struct Engine {
    executor: Executor,
}
#[pymethods]
impl Engine {
    #[new]
    #[pyo3(signature = (threads=1))]
    fn new(threads: usize) -> PyResult<Self> {
        Ok(Self {
            executor: Executor::new(threads).map_err(PyValueError::new_err)?,
        })
    }
    fn calculate<'py>(
        &self,
        py: Python<'py>,
        value: &Bound<'py, PyDict>,
    ) -> PyResult<Bound<'py, PyDict>> {
        let value = request(value)?;
        // Only owned snapshots cross into detached Rust; no borrowed Python data
        // can be mutated by another Python thread during calculation.
        let result = py
            .detach(move || calculate(value))
            .map_err(PyValueError::new_err)?;
        output(py, result)
    }
    fn batch<'py>(
        &self,
        py: Python<'py>,
        values: &Bound<'py, PyList>,
    ) -> PyResult<Bound<'py, PyDict>> {
        if values.len() > 1024 {
            return Err(PyValueError::new_err("Job count exceeds limit 1024"));
        }
        let jobs: PyResult<Vec<_>> = values
            .iter()
            .map(|value| Ok(Job::Calculate(request(value.cast::<PyDict>()?)?)))
            .collect();
        let jobs = jobs?;
        let report = py
            .detach(|| self.executor.batch(jobs))
            .map_err(PyValueError::new_err)?;
        execution_output(py, report)
    }
    fn density<'py>(
        &self,
        py: Python<'py>,
        value: &Bound<'py, PyDict>,
    ) -> PyResult<Bound<'py, PyDict>> {
        let req = density_request(value)?;
        let result = py
            .detach(move || optimize_density(req))
            .map_err(PyValueError::new_err)?;
        density_output(py, result)
    }
    fn jobs<'py>(
        &self,
        py: Python<'py>,
        values: &Bound<'py, PyList>,
    ) -> PyResult<Bound<'py, PyDict>> {
        if values.len() > 1024 {
            return Err(PyValueError::new_err("Job count exceeds limit 1024"));
        }
        let jobs: PyResult<Vec<_>> = values
            .iter()
            .map(|value| job(value.cast::<PyDict>()?))
            .collect();
        let jobs = jobs?;
        execution_output(
            py,
            py.detach(|| self.executor.batch(jobs))
                .map_err(PyValueError::new_err)?,
        )
    }
    fn sweep<'py>(
        &self,
        py: Python<'py>,
        base: &Bound<'py, PyDict>,
        points: &Bound<'py, PyList>,
    ) -> PyResult<Bound<'py, PyDict>> {
        if points.len() > 1024 {
            return Err(PyValueError::new_err("Job count exceeds limit 1024"));
        }
        let base = job(base)?;
        let points: PyResult<Vec<_>> = points
            .iter()
            .map(|v| {
                let v = v.cast::<PyDict>()?;
                keys(v, &["density", "background_scale", "q_max", "r_cutoff"])?;
                Ok(SweepPoint {
                    density: v
                        .get_item("density")?
                        .map(|v| v.extract())
                        .transpose()?
                        .flatten(),
                    background_scale: v
                        .get_item("background_scale")?
                        .map(|v| v.extract())
                        .transpose()?
                        .flatten(),
                    q_max: v
                        .get_item("q_max")?
                        .map(|v| v.extract())
                        .transpose()?
                        .flatten(),
                    r_cutoff: v
                        .get_item("r_cutoff")?
                        .map(|v| v.extract())
                        .transpose()?
                        .flatten(),
                })
            })
            .collect();
        let points = points?;
        execution_output(
            py,
            py.detach(|| self.executor.sweep(&base, points))
                .map_err(PyValueError::new_err)?,
        )
    }
}

#[pymodule]
fn _glassure_numpy(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<Engine>()?;
    operations::register(module)?;
    Ok(())
}
