//! Direct array bindings for the standalone Rust scientific functions.
use super::{composition, output_pattern, pattern};
use glassure_core::{
    corrections::{SollerGeometry, SollerMap},
    functions as f,
    scattering::{self, Source},
    SqOptimization,
};
use numpy::{IntoPyArray, PyReadonlyArray1};
use pyo3::{
    exceptions::{PyKeyError, PyValueError},
    prelude::*,
    types::{PyDict, PyModule},
};

macro_rules! get {
    ($d:expr,$k:expr) => {
        $d.get_item($k)?
            .ok_or_else(|| PyKeyError::new_err($k.to_owned()))?
            .extract()?
    };
}
fn vector(d: &Bound<'_, PyDict>, key: &str) -> PyResult<Vec<f64>> {
    let value = d
        .get_item(key)?
        .ok_or_else(|| PyKeyError::new_err(key.to_owned()))?;
    let a: PyReadonlyArray1<'_, f64> = value.extract()?;
    if a.len()? > 1_000_000 {
        return Err(PyValueError::new_err("Array allocation limit"));
    }
    Ok(a.as_array().iter().copied().collect())
}
fn optional_vector(d: &Bound<'_, PyDict>, key: &str) -> PyResult<Option<Vec<f64>>> {
    match d.get_item(key)?.filter(|v| !v.is_none()) {
        None => Ok(None),
        Some(_) => vector(d, key).map(Some),
    }
}
fn pat(d: &Bound<'_, PyDict>, key: &str) -> PyResult<glassure_core::request::Pattern> {
    let value: Bound<'_, PyDict> = get!(d, key);
    pattern(&value)
}
fn comp(d: &Bound<'_, PyDict>) -> PyResult<scattering::Composition> {
    composition(
        &d.get_item("composition")?
            .ok_or_else(|| PyKeyError::new_err("composition"))?,
    )
}
fn source(d: &Bound<'_, PyDict>) -> PyResult<Source> {
    Source::parse(
        &d.get_item("source")?
            .map(|v| v.extract::<String>())
            .transpose()?
            .unwrap_or("hajdu".into()),
    )
    .map_err(PyValueError::new_err)
}
fn method(d: &Bound<'_, PyDict>) -> PyResult<glassure_core::Method> {
    let value: String = get!(d, "method");
    f::method(&value).map_err(PyValueError::new_err)
}
fn peak(d: &Bound<'_, PyDict>) -> PyResult<f::Peak> {
    Ok(f::Peak {
        coordination: get!(d, "n"),
        position: get!(d, "position"),
        sigma: get!(d, "sigma"),
        composition: comp(d)?,
        element_1: get!(d, "element_1"),
        element_2: get!(d, "element_2"),
    })
}

#[pyfunction]
fn run<'py>(
    py: Python<'py>,
    name: &str,
    args: &Bound<'py, PyDict>,
) -> PyResult<Bound<'py, PyDict>> {
    let result = PyDict::new(py);
    macro_rules! array {
        ($v:expr) => {
            result.set_item("value", $v.map_err(PyValueError::new_err)?.into_pyarray(py))?
        };
    }
    macro_rules! scalar {
        ($v:expr) => {
            result.set_item("value", $v.map_err(PyValueError::new_err)?)?
        };
    }
    macro_rules! output {
        ($v:expr) => {
            result.set_item(
                "value",
                output_pattern(py, $v.map_err(PyValueError::new_err)?)?,
            )?
        };
    }
    match name {
        "composition" => {
            scalar!(comp(args)?.amounts());
        }
        "fractions" => {
            scalar!(comp(args)?.fractions());
        }
        "elements" => {
            result.set_item("value", scattering::available_elements(source(args)?))?;
        }
        "coherent" | "incoherent" => {
            let element: String = get!(args, "element");
            let q = vector(args, "q")?;
            let s = source(args)?;
            array!(py.detach(move || if name == "coherent" {
                scattering::coherent_factor(&element, &q, s)
            } else {
                scattering::incoherent_intensity(&element, &q, s)
            }));
        }
        "f2" | "fm2" | "incoherent_mean" | "s0" => {
            let c = comp(args)?;
            let q = vector(args, "q")?;
            let s = source(args)?;
            let value = py
                .detach(move || scattering::factors_with_source(&c, 1., &q, s))
                .map_err(PyValueError::new_err)?;
            match name {
                "f2" => result.set_item("value", value.f2.into_pyarray(py))?,
                "fm2" => result.set_item("value", value.fm2.into_pyarray(py))?,
                "incoherent_mean" => result.set_item("value", value.incoherent.into_pyarray(py))?,
                _ => result.set_item("value", value.s0)?,
            }
        }
        "atomic_density" | "mass_density" => {
            let c = comp(args)?;
            let density: f64 = get!(args, "density");
            scalar!(if name == "atomic_density" {
                scattering::atomic_density(&c, density)
            } else {
                scattering::mass_density(&c, density)
            });
        }
        "ztotal" => {
            scalar!(f::total_atomic_number(&comp(args)?));
        }
        "effective" | "keff" | "weight" | "wkm" => {
            let c = comp(args)?;
            let q = vector(args, "q")?;
            let s = source(args)?;
            match name {
                "effective" => {
                    array!(py.detach(|| f::effective_form_factor(&c, &q, s)));
                }
                "keff" => {
                    let element: String = get!(args, "element");
                    scalar!(py.detach(|| f::wkm_effective_atomic_number(&c, &element, &q, s)));
                }
                _ => {
                    let a: String = get!(args, "element_1");
                    let b: String = get!(args, "element_2");
                    if name == "weight" {
                        array!(py.detach(|| f::weighting_factor(&c, &a, &b, &q, s)));
                    } else {
                        scalar!(py.detach(|| f::weighting_factor_wkm(&c, &a, &b, &q, s)));
                    }
                }
            }
        }
        "kn" => {
            let q = vector(args, "q")?;
            let wavelength: f64 = get!(args, "wavelength");
            array!(py.detach(|| glassure_core::corrections::klein_nishina(&q, wavelength)));
        }
        "two_theta" => {
            let q = vector(args, "q")?;
            let wavelength: f64 = get!(args, "wavelength");
            array!(f::two_theta_to_q(&q, wavelength));
        }
        "sq" => {
            let p = pat(args, "pattern")?;
            let a = vector(args, "f2")?;
            let b = vector(args, "fm2")?;
            output!(py.detach(|| f::calculate_sq(&p, &a, &b)));
        }
        "fr" | "sq_from_fr" | "sq_from_gr" => {
            let p = pat(args, "pattern")?;
            let grid = vector(args, "grid")?;
            let m = method(args)?;
            let lorch: bool = get!(args, "lorch");
            if name == "fr" {
                output!(py.detach(|| f::calculate_fr(&p, &grid, m, lorch)));
            } else if name == "sq_from_fr" {
                output!(py.detach(|| f::calculate_sq_from_fr(&p, &grid, m, lorch)));
            } else {
                let rho: f64 = get!(args, "density");
                output!(py.detach(|| f::calculate_sq_from_gr(&p, &grid, rho, m)));
            }
        }
        "gr" | "rdf" | "tr" => {
            let p = pat(args, "pattern")?;
            let rho: f64 = get!(args, "density");
            output!(py.detach(|| match name {
                "gr" => f::calculate_gr(&p, rho),
                "rdf" => f::calculate_rdf(&p, rho),
                _ => f::calculate_tr(&p, rho),
            }));
        }
        "normalize" => {
            let p = pat(args, "pattern")?;
            let rho: f64 = get!(args, "density");
            let a = vector(args, "f2")?;
            let b = vector(args, "fm2")?;
            let inc = optional_vector(args, "incoherent")?;
            let attenuation: f64 = get!(args, "attenuation");
            let (n, p) = py
                .detach(|| f::normalize(&p, rho, &a, &b, inc.as_deref(), attenuation))
                .map_err(PyValueError::new_err)?;
            result.set_item("value", (n, output_pattern(py, p)?))?;
        }
        "normalize_fit" | "normalize_fit_lmfit" => {
            let p = pat(args, "pattern")?;
            let a = vector(args, "f2")?;
            let inc = optional_vector(args, "incoherent")?;
            let cont = optional_vector(args, "container")?;
            let cutoff: f64 = get!(args, "cutoff");
            let scaling: String = get!(args, "scaling");
            let multiple: bool = get!(args, "multiple");
            let (params, p) = py
                .detach(|| {
                    (if name == "normalize_fit_lmfit" {
                        f::normalize_fit_constrained
                    } else {
                        f::normalize_fit
                    })(
                        &p,
                        &a,
                        inc.as_deref(),
                        cutoff,
                        &scaling,
                        multiple,
                        cont.as_deref(),
                    )
                })
                .map_err(PyValueError::new_err)?;
            let pp = PyDict::new(py);
            pp.set_item("n", params.n)?;
            pp.set_item("multiple", params.multiple)?;
            pp.set_item("n_container", params.n_container)?;
            pp.set_item("residual", params.residual)?;
            result.set_item("value", (pp, output_pattern(py, p)?))?;
        }
        "extrapolate" => {
            let p = pat(args, "pattern")?;
            let m: String = get!(args, "method");
            let y0: f64 = get!(args, "y0");
            let xmax: f64 = get!(args, "x_max");
            let replace: bool = get!(args, "replace");
            let smoothing: Option<f64> = get!(args, "smoothing");
            output!(py.detach(|| f::extrapolate(&p, &m, y0, xmax, replace, smoothing)));
        }
        "optimize_sq" => {
            let p = pat(args, "pattern")?;
            let rho: f64 = get!(args, "density");
            let step: f64 = get!(args, "r_step");
            let m = method(args)?;
            let opt = SqOptimization {
                method: get!(args, "optimization"),
                r_cutoff: get!(args, "r_cutoff"),
                iterations: get!(args, "iterations"),
                lorch: get!(args, "lorch"),
                attenuation: get!(args, "attenuation"),
            };
            let y = py
                .detach(|| glassure_core::sq_optimization::optimize(&p.x, &p.y, rho, step, m, &opt))
                .map_err(PyValueError::new_err)?;
            result.set_item(
                "value",
                output_pattern(py, glassure_core::request::Pattern { x: p.x, y })?,
            )?;
        }
        "polynomial" => {
            let x = vector(args, "x")?;
            let y = vector(args, "y")?;
            let degree: usize = get!(args, "degree");
            let mut values = py
                .detach(|| glassure_core::numeric::polynomial_origin(&x, &y, degree))
                .map_err(PyValueError::new_err)?;
            values.reverse();
            values.push(0.);
            result.set_item("value", values.into_pyarray(py))?;
        }
        "iq_peak" | "tr_peak" | "gaussian" => {
            let peak = peak(args)?;
            let s = source(args)?;
            let q = vector(args, "q")?;
            if name == "iq_peak" {
                array!(py.detach(|| peak.i_q(&q, s)));
            } else {
                let r = vector(args, "r")?;
                if name == "gaussian" {
                    array!(py.detach(|| peak.gaussian(&r, &q, s)));
                } else {
                    let m = method(args)?;
                    let lorch: bool = get!(args, "lorch");
                    array!(py.detach(|| peak.t_r(&r, &q, m, lorch, s)));
                }
            }
        }
        "smooth" | "rebin" => {
            let p = pat(args, "pattern")?;
            let amount: f64 = get!(args, "amount");
            output!(py.detach(|| if name == "smooth" {
                p.smooth(amount)
            } else {
                p.rebin(amount)
            }));
        }
        "vector_length" => {
            let x = vector(args, "x")?;
            result.set_item("value", glassure_core::corrections::vector_length(&x))?;
        }
        "angles" => {
            let a: [f64; 2] = get!(args, "point1");
            let b: [f64; 2] = get!(args, "point2");
            let x = vector(args, "x")?;
            let y = vector(args, "y")?;
            if x.len() != y.len() {
                return Err(PyValueError::new_err("Center array length mismatch"));
            }
            let centers: Vec<_> = x.iter().zip(y).map(|(x, y)| [*x, y]).collect();
            array!(glassure_core::corrections::calculate_angles(a, b, &centers));
        }
        "x_intercept" | "y_intercept" => {
            let a: [f64; 2] = get!(args, "point1");
            let b: [f64; 2] = get!(args, "point2");
            result.set_item(
                "value",
                if name == "x_intercept" {
                    glassure_core::corrections::x_axis_intercept(a, b)
                } else {
                    glassure_core::corrections::y_axis_intercept(a, b)
                },
            )?;
        }
        "side_points" => {
            let radius: f64 = get!(args, "radius");
            let angle: f64 = get!(args, "angle");
            let width: f64 = get!(args, "width");
            result.set_item(
                "value",
                glassure_core::corrections::rectangular_side_points(radius, angle, width),
            )?;
        }
        _ => {
            return Err(PyValueError::new_err(format!(
                "Unknown native operation: {name}"
            )))
        }
    }
    Ok(result)
}

#[pyclass]
struct TransferFunction {
    inner: f::TransferFunction,
}
#[pymethods]
impl TransferFunction {
    #[new]
    fn new(
        py: Python<'_>,
        standard: &Bound<'_, PyDict>,
        sample: &Bound<'_, PyDict>,
        smoothing: f64,
    ) -> PyResult<Self> {
        let a = pattern(standard)?;
        let b = pattern(sample)?;
        Ok(Self {
            inner: py
                .detach(|| f::TransferFunction::fit(&a, &b, smoothing))
                .map_err(PyValueError::new_err)?,
        })
    }
    fn __call__<'py>(
        &self,
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        let x: Vec<_> = x.as_array().iter().copied().collect();
        Ok(py
            .detach(|| self.inner.evaluate(&x))
            .map_err(PyValueError::new_err)?
            .into_pyarray(py))
    }
}
type ArrayPair<'py> = (
    Bound<'py, numpy::PyArray1<f64>>,
    Bound<'py, numpy::PyArray1<f64>>,
);
#[pyclass]
struct Soller {
    inner: SollerMap,
}
fn geometry(d: &Bound<'_, PyDict>) -> PyResult<SollerGeometry> {
    Ok(SollerGeometry {
        inner_radius: get!(d, "inner_radius"),
        outer_radius: get!(d, "outer_radius"),
        inner_width: get!(d, "inner_width"),
        outer_width: get!(d, "outer_width"),
        inner_length: get!(d, "inner_length"),
        outer_length: get!(d, "outer_length"),
    })
}
#[pymethods]
impl Soller {
    #[new]
    fn new(
        py: Python<'_>,
        two_theta: PyReadonlyArray1<'_, f64>,
        max_thickness: f64,
        options: &Bound<'_, PyDict>,
    ) -> PyResult<Self> {
        let x: Vec<_> = two_theta.as_array().iter().copied().collect();
        let g = geometry(options)?;
        Ok(Self {
            inner: py
                .detach(|| SollerMap::new(&x, max_thickness, &g))
                .map_err(PyValueError::new_err)?,
        })
    }
    fn region<'py>(
        &self,
        py: Python<'py>,
        lower: f64,
        upper: f64,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        Ok(py
            .detach(|| self.inner.region(lower, upper))
            .map_err(PyValueError::new_err)?
            .into_pyarray(py))
    }
    fn sample<'py>(
        &self,
        py: Python<'py>,
        thickness: f64,
        shift: f64,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        Ok(py
            .detach(|| self.inner.sample(thickness, shift))
            .map_err(PyValueError::new_err)?
            .into_pyarray(py))
    }
    fn dac<'py>(&self, py: Python<'py>, sample: f64, initial: f64) -> PyResult<ArrayPair<'py>> {
        let (a, b) = py
            .detach(|| self.inner.dac(sample, initial))
            .map_err(PyValueError::new_err)?;
        Ok((a.into_pyarray(py), b.into_pyarray(py)))
    }
    fn map<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let value = PyDict::new(py);
        value.set_item("two_theta", self.inner.two_theta.clone().into_pyarray(py))?;
        value.set_item("distance", self.inner.distance.clone().into_pyarray(py))?;
        value.set_item("angles", self.inner.angles.clone().into_pyarray(py))?;
        Ok(value)
    }
}
pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(run, module)?)?;
    module.add_class::<TransferFunction>()?;
    module.add_class::<Soller>()?;
    Ok(())
}
