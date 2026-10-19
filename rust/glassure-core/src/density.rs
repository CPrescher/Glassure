//! Bounded density/background refinement with reusable preparation and buffers.
//!
//! [`optimize_density`] fits mass density in g/cm³. Each fit is sequential;
//! [`crate::parallel`] runs independent fits on multiple native cores. Ordinary
//! WASM calls are synchronous; a browser can cancel by terminating its worker.
use crate::prepared::PreparedCalculation;
use crate::request::{calculate, Request, Response};
use nalgebra::DMatrix;
use serde::{Deserialize, Serialize};
use std::cell::{Cell, RefCell};
use std::f64::consts::PI;

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
/// Fit settings. Only the fields with serde defaults may be omitted in JSON.
pub struct DensityRequest {
    /// Initial PDF settings; its density/background scale are starting values.
    pub calculation: Request,
    /// Objective: `"gr"`, `"fr"` or `"sq"`. Residuals are respectively g(r),
    /// `F(r) + 4πρr`, or optimized S(Q) minus the initial unoptimized reference.
    pub method: String,
    #[serde(default)]
    /// Strict objective interval, in Å for gr/fr or Å⁻¹ for sq. `None` uses
    /// [0, r_cutoff] for gr/fr (requires S(Q) optimization) or [0, q_max] for sq.
    pub min_range: Option<[f64; 2]>,
    #[serde(default)]
    /// Fit background scale as a second parameter; default false.
    pub vary_background: bool,
    #[serde(default = "limits")]
    /// Multipliers of the initial background scale; default [0.9, 1.1].
    /// Resulting bounds must be ordered and contain the starting value.
    pub background_limits: [f64; 2],
    #[serde(default = "algorithm")]
    /// `"lsq"` (default bounded TRF), `"nelder"`, `"brent_local"` or `"brent"`.
    /// Brent variants require `vary_background = false`.
    pub algorithm: String,
    #[serde(default = "budget")]
    /// Residual evaluation budget, inclusive of derivative/error work where used.
    /// Must be 10–10000; JSON default is 500.
    pub max_evaluations: usize,
}
fn limits() -> [f64; 2] {
    [0.9, 1.1]
}
fn algorithm() -> String {
    "lsq".into()
}
fn budget() -> usize {
    500
}
#[derive(Serialize)]
/// Successful fit, conditional error estimates and final PDF curves.
/// Nonconvergence returns `Err` rather than a successful final iterate.
pub struct DensityResult {
    /// Fitted mass density, g/cm³.
    pub density: f64,
    /// Local conditional standard error for lsq/Brent, if identifiable.
    /// For legacy Nelder output this contains the residual sum of squares.
    pub density_error: Option<f64>,
    /// Fitted or fixed background multiplier.
    pub background_scale: f64,
    /// Background standard error when fitted (zero when fixed for lsq/Brent),
    /// or legacy residual sum of squares for Nelder; `None` if unidentified.
    pub background_error: Option<f64>,
    /// Sum of squared residuals after multiplying each residual by grid spacing.
    pub sum_squared_residuals: f64,
    /// Count of residual evaluations, not FFTs or optimizer iterations.
    pub evaluations: usize,
    /// True for returned fits; failure is represented by `Err`.
    pub success: bool,
    /// Solver stopping criterion, such as a step/cost/scalar tolerance.
    pub termination: String,
    /// `"conditional_standard_error"` or `"sum_squared_residuals"`.
    pub error_kind: &'static str,
    /// Final S(Q), F(r), g(r) and normalization metadata.
    pub result: Response,
}
struct Problem<'a> {
    req: &'a DensityRequest,
    prepared: RefCell<PreparedCalculation<'a>>,
    indices: Vec<usize>,
    step: f64,
    reference: Option<Vec<f64>>,
    evaluations: Cell<usize>,
    analytic: bool,
    cached_jacobian: RefCell<Option<(Vec<f64>, DMatrix<f64>)>>,
}
impl Problem<'_> {
    fn residual(&self, p: &[f64]) -> Result<Vec<f64>, String> {
        self.evaluate(p, self.analytic && self.req.algorithm == "lsq")
    }
    fn evaluate(&self, p: &[f64], derivatives: bool) -> Result<Vec<f64>, String> {
        crate::profile_span!(Residual);
        if self.evaluations.get() >= self.req.max_evaluations {
            return Err("evaluation_budget".into());
        }
        self.evaluations.set(self.evaluations.get() + 1);
        let background = p
            .get(1)
            .copied()
            .unwrap_or(self.req.calculation.background_scale);
        let mut prepared = self.prepared.borrow_mut();
        let result = if derivatives {
            let d = prepared.derivatives(p[0], background, p.len() == 2)?;
            let values = match self.req.method.as_str() {
                "gr" => d.gr,
                "fr" => d.fr,
                _ => d.sq,
            };
            let jac = DMatrix::from_fn(self.indices.len(), p.len(), |j, k| {
                let i = self.indices[j];
                self.step
                    * (values[k][i]
                        + if self.req.method == "fr" && k == 0 {
                            4. * PI * d.result.r[i] * d.atomic_density
                        } else {
                            0.
                        })
            });
            *self.cached_jacobian.borrow_mut() = Some((p.to_vec(), jac));
            d.result
        } else {
            prepared.evaluate(p[0], background)?
        };
        let values = match self.req.method.as_str() {
            "gr" => result.gr,
            "fr" => result.fr,
            "sq" => result.sq,
            _ => return Err("Unknown density objective".into()),
        };
        Ok(self
            .indices
            .iter()
            .enumerate()
            .map(|(j, i)| {
                self.step
                    * match self.req.method.as_str() {
                        "gr" => values[*i],
                        "fr" => values[*i] + 4.0 * PI * result.r[*i] * result.atomic_density,
                        _ => values[*i] - self.reference.as_ref().unwrap()[j],
                    }
            })
            .collect())
    }
}
fn cost(r: &[f64]) -> f64 {
    r.iter().map(|v| v * v).sum()
}
fn jacobian(
    problem: &Problem<'_>,
    p: &[f64],
    r: &[f64],
    bounds: &[[f64; 2]],
) -> Result<DMatrix<f64>, String> {
    if problem.analytic {
        if !problem
            .cached_jacobian
            .borrow()
            .as_ref()
            .is_some_and(|(at, _)| at == p)
        {
            problem.evaluate(p, true)?;
        }
        return Ok(problem.cached_jacobian.borrow().as_ref().unwrap().1.clone());
    }
    crate::bounded_trf::jacobian(&|p| problem.residual(p), p, r, bounds)
}
fn least_squares(
    problem: &Problem<'_>,
    p: Vec<f64>,
    bounds: &[[f64; 2]],
) -> Result<(Vec<f64>, Vec<f64>, String), String> {
    if problem.analytic {
        crate::bounded_trf::solve_with_jacobian(
            &|p| problem.residual(p),
            &|p, r| jacobian(problem, p, r, bounds),
            &p,
            bounds,
        )
    } else {
        crate::bounded_trf::solve(&|p| problem.residual(p), &p, bounds)
    }
}
fn brent(problem: &Problem<'_>, bounds: [f64; 2]) -> Result<(Vec<f64>, Vec<f64>, String), String> {
    // Cache the best residual so convergence does not require another pipeline.
    let mut best: Option<(f64, f64, Vec<f64>)> = None;
    let mut cache: Vec<(f64, f64)> = vec![];
    let mut objective = |x| {
        if let Some((_, value)) = cache.iter().find(|(at, _)| *at == x) {
            return Ok(*value);
        }
        let r = problem.residual(&[x])?;
        let sse = cost(&r);
        if best.as_ref().is_none_or(|(_, value, _)| sse <= *value) {
            best = Some((x, sse, r));
        }
        cache.push((x, sse));
        Ok(sse)
    };
    let (x, _) = if problem.req.algorithm == "brent_local" {
        let (interval, initial) = crate::bounded_brent::local_bracket(
            &mut objective,
            problem.req.calculation.density,
            bounds,
            problem.req.max_evaluations,
        )?;
        crate::bounded_brent::solve_from(
            &mut objective,
            interval,
            Some(initial),
            1e-8,
            problem.req.max_evaluations,
        )?
    } else {
        crate::bounded_brent::solve(&mut objective, bounds, 1e-8, problem.req.max_evaluations)?
    };
    let (at, _, residual) = best.ok_or("Brent produced no residual")?;
    if at != x {
        return Err("Brent residual cache mismatch".into());
    }
    Ok((vec![x], residual, "scalar_tolerance".into()))
}
fn physical(x: &[f64], bounds: &[[f64; 2]]) -> Vec<f64> {
    x.iter()
        .enumerate()
        .map(|(i, x)| bounds[i][0] + (x.sin() + 1.0) * (bounds[i][1] - bounds[i][0]) / 2.0)
        .collect()
}
fn nelder(
    problem: &Problem<'_>,
    p: &[f64],
    bounds: &[[f64; 2]],
) -> Result<(Vec<f64>, Vec<f64>, String), String> {
    let n = p.len();
    let x: Vec<_> = p
        .iter()
        .enumerate()
        .map(|(i, p)| {
            (2.0 * (p - bounds[i][0]) / (bounds[i][1] - bounds[i][0]) - 1.0)
                .clamp(-1.0, 1.0)
                .asin()
        })
        .map(|v| if v.abs() < 1e-15 { 0.0 } else { v })
        .collect();
    let mut simplex = vec![x.clone(); n + 1];
    for i in 0..n {
        simplex[i + 1][i] = if x[i] != 0.0 { x[i] * 1.05 } else { 0.00025 };
    }
    let mut values: Vec<_> = simplex
        .iter()
        .map(|p| problem.residual(&physical(p, bounds)).map(|r| cost(&r)))
        .collect::<Result<_, _>>()?;
    loop {
        let mut order: Vec<_> = (0..=n).collect();
        order.sort_by(|a, b| values[*a].total_cmp(&values[*b]));
        simplex = order.iter().map(|i| simplex[*i].clone()).collect();
        values = order.iter().map(|i| values[*i]).collect();
        let dx = simplex[1..]
            .iter()
            .flat_map(|p| p.iter().zip(&simplex[0]).map(|(a, b)| (a - b).abs()))
            .fold(0.0, f64::max);
        if dx <= 0.0001 && (values[n] - values[0]).abs() <= 0.0001 {
            let p = physical(&simplex[0], bounds);
            let r = problem.residual(&p)?;
            return Ok((p, r, "simplex_tolerance".into()));
        }
        let center: Vec<_> = (0..n)
            .map(|j| simplex[..n].iter().map(|p| p[j]).sum::<f64>() / n as f64)
            .collect();
        let reflect: Vec<_> = (0..n).map(|j| 2.0 * center[j] - simplex[n][j]).collect();
        let fr = cost(&problem.residual(&physical(&reflect, bounds))?);
        let mut shrink = false;
        if fr < values[0] {
            let expand: Vec<_> = (0..n)
                .map(|j| 3.0 * center[j] - 2.0 * simplex[n][j])
                .collect();
            let fe = cost(&problem.residual(&physical(&expand, bounds))?);
            if fe < fr {
                simplex[n] = expand;
                values[n] = fe;
            } else {
                simplex[n] = reflect;
                values[n] = fr;
            }
        } else if fr < values[n - 1] {
            simplex[n] = reflect;
            values[n] = fr;
        } else {
            let outside = fr < values[n];
            let contract: Vec<_> = (0..n)
                .map(|j| {
                    if outside {
                        1.5 * center[j] - 0.5 * simplex[n][j]
                    } else {
                        0.5 * center[j] + 0.5 * simplex[n][j]
                    }
                })
                .collect();
            let fc = cost(&problem.residual(&physical(&contract, bounds))?);
            if (outside && fc <= fr) || (!outside && fc < values[n]) {
                simplex[n] = contract;
                values[n] = fc;
            } else {
                shrink = true;
            }
        }
        if shrink {
            let best = simplex[0].clone();
            for i in 1..=n {
                for (value, center) in simplex[i].iter_mut().zip(&best) {
                    *value = center + 0.5 * (*value - center);
                }
                values[i] = cost(&problem.residual(&physical(&simplex[i], bounds))?);
            }
        }
    }
}

/// Fit density in [1e-12, 100] g/cm³, optionally with a bounded background scale.
///
/// Prepares fixed quantities once. TRF uses analytic derivatives for supported
/// step/linear extrapolation and no/iterative S(Q) optimization; unsupported
/// derivative combinations use finite differences within the same solver.
/// Residuals use strict interval selection and are multiplied by grid spacing.
/// Invalid settings, a depleted evaluation budget and nonconvergence are errors.
/// Error estimates condition on the selected normalization/model and objective;
/// they do not include experimental systematic uncertainty.
pub fn optimize_density(req: DensityRequest) -> Result<DensityResult, String> {
    crate::profile_span!(Fit);
    if !matches!(req.method.as_str(), "sq" | "fr" | "gr")
        || !matches!(
            req.algorithm.as_str(),
            "lsq" | "nelder" | "brent" | "brent_local"
        )
        || !(10..=10000).contains(&req.max_evaluations)
    {
        return Err("Invalid density optimizer settings".into());
    }
    if matches!(req.algorithm.as_str(), "brent" | "brent_local") && req.vary_background {
        return Err("Brent requires fixed background (one fitted parameter)".into());
    }
    let range = match req.min_range {
        Some(range) => range,
        None => {
            if req.method == "sq" {
                [0.0, req.calculation.q_max]
            } else {
                [
                    0.0,
                    req.calculation
                        .optimize
                        .as_ref()
                        .ok_or("Density objective needs explicit range or S(Q) optimization")?
                        .r_cutoff,
                ]
            }
        }
    };
    if !range.iter().all(|v| v.is_finite()) || range[0] >= range[1] {
        return Err("Invalid density objective range".into());
    }
    let reference = if req.method == "sq" {
        let mut c = req.calculation.clone();
        c.optimize = None;
        Some(calculate(c)?)
    } else {
        None
    };
    let mut p = vec![req.calculation.density];
    let mut bounds = vec![[1e-12, 100.0]];
    if req.vary_background {
        let v = req.calculation.background_scale;
        let b = [v * req.background_limits[0], v * req.background_limits[1]];
        if !b.iter().all(|v| v.is_finite()) || b[0] >= b[1] || v < b[0] || v > b[1] {
            return Err("Invalid background bounds".into());
        }
        p.push(v);
        bounds.push(b);
    }
    if p[0] < bounds[0][0] || p[0] > bounds[0][1] {
        return Err("Density outside optimizer bounds".into());
    }
    let prepared = PreparedCalculation::new(&req.calculation)?;
    let coordinates = if req.method == "sq" {
        prepared.q()
    } else {
        prepared.r()
    };
    let indices: Vec<_> = coordinates
        .iter()
        .enumerate()
        .filter(|(_, x)| **x > range[0] && **x < range[1])
        .map(|(i, _)| i)
        .collect();
    if indices.len() < 2 {
        return Err("Density objective needs two in-range points".into());
    }
    let step = coordinates[indices[1]] - coordinates[indices[0]];
    let reference = reference.map(|r| {
        r.sq.y
            .iter()
            .zip(&r.sq.x)
            .filter(|(_, x)| **x > range[0] && **x < range[1])
            .map(|(y, _)| *y)
            .collect::<Vec<_>>()
    });
    if reference.as_ref().is_some_and(|r| r.len() != indices.len()) {
        return Err("Density reference grid mismatch".into());
    }
    let analytic = req.algorithm != "nelder" && prepared.analytic(req.vary_background);
    let problem = Problem {
        req: &req,
        prepared: RefCell::new(prepared),
        indices,
        step,
        reference,
        evaluations: Cell::new(0),
        analytic,
        cached_jacobian: RefCell::new(None),
    };
    let (p, r, termination) = if req.algorithm == "nelder" {
        nelder(&problem, &p, &bounds)?
    } else if matches!(req.algorithm.as_str(), "brent" | "brent_local") {
        brent(&problem, bounds[0])?
    } else {
        least_squares(&problem, p, &bounds)?
    };
    let sse = cost(&r);
    let mut errors = vec![None; p.len()];
    if req.algorithm != "nelder" {
        let jac = jacobian(&problem, &p, &r, &bounds)?;
        let svd = jac.svd(false, true);
        let max = svd.singular_values[0];
        if r.len() > p.len()
            && svd
                .singular_values
                .iter()
                .all(|v| *v > f64::EPSILON * r.len().max(p.len()) as f64 * max)
        {
            let vt = svd.v_t.unwrap();
            for j in 0..p.len() {
                let variance = svd
                    .singular_values
                    .iter()
                    .enumerate()
                    .map(|(i, v)| vt[(i, j)].powi(2) / v.powi(2))
                    .sum::<f64>()
                    * sse
                    / (r.len() - p.len()) as f64;
                errors[j] = Some(variance.sqrt());
            }
        }
    } else {
        errors.fill(Some(sse));
    }
    let background_scale = p
        .get(1)
        .copied()
        .unwrap_or(req.calculation.background_scale);
    let result = problem
        .prepared
        .borrow_mut()
        .evaluate(p[0], background_scale)?
        .owned();
    Ok(DensityResult {
        density: p[0],
        density_error: errors[0],
        background_scale,
        background_error: if p.len() == 2 {
            errors[1]
        } else if req.algorithm == "nelder" {
            Some(sse)
        } else {
            Some(0.0)
        },
        sum_squared_residuals: sse,
        evaluations: problem.evaluations.get(),
        success: true,
        termination,
        error_kind: if req.algorithm != "nelder" {
            "conditional_standard_error"
        } else {
            "sum_squared_residuals"
        },
        result,
    })
}
