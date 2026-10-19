//! Dense bounded trust-region reflective least squares, linear loss/x_scale=1.
//! Adapted from SciPy's BSD-3-Clause trf_bounds/select_step/common routines;
//! see THIRD_PARTY_NOTICES.md. Numerical factorizations are pure Rust nalgebra.
use nalgebra::{DMatrix, DVector};

fn quad(j: &DMatrix<f64>, diag: &DVector<f64>, g: &DVector<f64>, p: &DVector<f64>) -> f64 {
    0.5 * (j * p).norm_squared() + 0.5 * diag.dot(&p.component_mul(p)) + g.dot(p)
}
fn stride(x: &DVector<f64>, p: &DVector<f64>, bounds: &[[f64; 2]]) -> (f64, Vec<bool>) {
    let ratios: Vec<_> = (0..x.len())
        .map(|i| {
            if p[i] > 0.0 {
                (bounds[i][1] - x[i]) / p[i]
            } else if p[i] < 0.0 {
                (bounds[i][0] - x[i]) / p[i]
            } else {
                f64::INFINITY
            }
        })
        .collect();
    let min = ratios.iter().copied().fold(f64::INFINITY, f64::min);
    (min, ratios.iter().map(|v| *v == min).collect())
}
fn minimize_line(
    j: &DMatrix<f64>,
    diag: &DVector<f64>,
    g: &DVector<f64>,
    direction: &DVector<f64>,
    offset: &DVector<f64>,
    lo: f64,
    hi: f64,
) -> (DVector<f64>, f64) {
    let jd = j * direction;
    let jo = j * offset;
    let a = 0.5 * (jd.norm_squared() + diag.dot(&direction.component_mul(direction)));
    let b = jo.dot(&jd) + diag.dot(&offset.component_mul(direction)) + g.dot(direction);
    let mut candidates = vec![lo, hi];
    if a > 0.0 {
        let t = -b / (2.0 * a);
        if t > lo && t < hi {
            candidates.push(t);
        }
    }
    candidates
        .into_iter()
        .map(|t| {
            let p = offset + direction * t;
            let value = quad(j, diag, g, &p);
            (p, value)
        })
        .min_by(|a, b| a.1.total_cmp(&b.1))
        .unwrap()
}
// Keep the reference algorithm's step-selection inputs explicit.
#[allow(clippy::too_many_arguments)]
fn select(
    x: &DVector<f64>,
    j: &DMatrix<f64>,
    diag: &DVector<f64>,
    g: &DVector<f64>,
    mut ph: DVector<f64>,
    d: &DVector<f64>,
    radius: f64,
    bounds: &[[f64; 2]],
    theta: f64,
) -> (DVector<f64>, DVector<f64>, f64) {
    let p = d.component_mul(&ph);
    if (0..x.len()).all(|i| x[i] + p[i] >= bounds[i][0] && x[i] + p[i] <= bounds[i][1]) {
        let predicted = -quad(j, diag, g, &ph);
        return (p, ph, predicted);
    }
    let (alpha, hits) = stride(x, &p, bounds);
    let mut rh = ph.clone();
    for i in 0..rh.len() {
        if hits[i] {
            rh[i] = -rh[i];
        }
    }
    ph *= alpha;
    let on_bound = x + d.component_mul(&ph);
    let r = d.component_mul(&rh);
    let a = rh.norm_squared();
    let b = 2.0 * ph.dot(&rh);
    let c = ph.norm_squared() - radius * radius;
    let to_tr = (-b + (b * b - 4.0 * a * c).max(0.0).sqrt()) / (2.0 * a);
    let (to_bound, _) = stride(&on_bound, &r, bounds);
    let length = to_tr.min(to_bound);
    let low = if length > 0.0 {
        (1.0 - theta) * alpha / length
    } else {
        0.0
    };
    let high = if length <= 0.0 {
        -1.0
    } else if length == to_bound {
        theta * to_bound
    } else {
        to_tr
    };
    let reflection = if low <= high {
        Some(minimize_line(j, diag, g, &rh, &ph, low, high))
    } else {
        None
    };
    let interior = &ph * theta;
    let value = quad(j, diag, g, &interior);
    let gradient = -g;
    let ag = d.component_mul(&gradient);
    let (to_bound, _) = stride(x, &ag, bounds);
    let to_tr = radius / gradient.norm();
    let limit = if to_bound < to_tr {
        theta * to_bound
    } else {
        to_tr
    };
    let (cauchy, cv) = minimize_line(j, diag, g, &gradient, &DVector::zeros(x.len()), 0.0, limit);
    let (mut best, mut objective) = (interior, value);
    if let Some((r, rv)) = reflection {
        if rv < objective {
            best = r;
            objective = rv;
        }
    }
    if cv < objective {
        best = cauchy;
        objective = cv;
    }
    (d.component_mul(&best), best, -objective)
}
fn trust_step(
    uf: &DVector<f64>,
    s: &DVector<f64>,
    v: &DMatrix<f64>,
    radius: f64,
    m: usize,
    initial: f64,
) -> (DVector<f64>, f64) {
    let n = s.len();
    let full = m >= n && s[n - 1] > f64::EPSILON * m as f64 * s[0];
    if full {
        let p = -(v * uf.component_div(s));
        if p.norm() <= radius {
            return (p, 0.0);
        }
    }
    let suf = s.component_mul(uf);
    let phi = |alpha: f64| {
        let denom = s.map(|s| s * s + alpha);
        let norm = suf.component_div(&denom).norm();
        let derivative = -(0..n)
            .map(|i| suf[i] * suf[i] / denom[i].powi(3))
            .sum::<f64>()
            / norm;
        (norm - radius, derivative)
    };
    let mut upper = suf.norm() / radius;
    let mut lower = if full {
        let (f, fp) = phi(0.0);
        -f / fp
    } else {
        0.0
    };
    let mut alpha = if !full && initial == 0.0 {
        (0.001 * upper).max((lower * upper).sqrt())
    } else {
        initial
    };
    for _ in 0..10 {
        if alpha < lower || alpha > upper {
            alpha = (0.001 * upper).max((lower * upper).sqrt());
        }
        let (f, fp) = phi(alpha);
        if f < 0.0 {
            upper = alpha;
        }
        let ratio = f / fp;
        lower = lower.max(alpha - ratio);
        alpha -= (f + radius) * ratio / radius;
        if f.abs() < 0.01 * radius {
            break;
        }
    }
    let mut p = -(v * suf.component_div(&s.map(|s| s * s + alpha)));
    p *= radius / p.norm();
    (p, alpha)
}

pub fn solve<F>(
    residual: &F,
    initial: &[f64],
    bounds: &[[f64; 2]],
) -> Result<(Vec<f64>, Vec<f64>, String), String>
where
    F: Fn(&[f64]) -> Result<Vec<f64>, String>,
{
    solve_with_jacobian(
        residual,
        &|p, r| jacobian(residual, p, r, bounds),
        initial,
        bounds,
    )
}
pub fn solve_with_jacobian<F, J>(
    residual: &F,
    derivative: &J,
    initial: &[f64],
    bounds: &[[f64; 2]],
) -> Result<(Vec<f64>, Vec<f64>, String), String>
where
    F: Fn(&[f64]) -> Result<Vec<f64>, String>,
    J: Fn(&[f64], &[f64]) -> Result<DMatrix<f64>, String>,
{
    let mut x = DVector::from_column_slice(initial);
    let mut f = DVector::from_vec(residual(x.as_slice())?);
    let mut j = derivative(x.as_slice(), f.as_slice())?;
    let mut g = j.transpose() * &f;
    let (mut radius, mut alpha) = (0.0, 0.0);
    for iteration in 0..500 {
        let mut v = DVector::from_element(x.len(), 1.0);
        let mut dv = DVector::zeros(x.len());
        for i in 0..x.len() {
            if g[i] < 0.0 {
                v[i] = bounds[i][1] - x[i];
                dv[i] = -1.0;
            } else if g[i] > 0.0 {
                v[i] = x[i] - bounds[i][0];
                dv[i] = 1.0;
            }
        }
        if iteration == 0 {
            radius = x.component_div(&v.map(f64::sqrt)).norm();
            if radius == 0.0 {
                radius = 1.0;
            }
        }
        let gnorm = g.component_mul(&v).amax();
        if gnorm < 1e-8 {
            return Ok((
                x.as_slice().to_vec(),
                f.as_slice().to_vec(),
                "gradient_tolerance".into(),
            ));
        }
        let d = v.map(f64::sqrt);
        let diag = g.component_mul(&dv);
        let gh = d.component_mul(&g);
        let jh = DMatrix::from_fn(j.nrows(), j.ncols(), |i, k| j[(i, k)] * d[k]);
        let mut augmented = DMatrix::zeros(j.nrows() + x.len(), x.len());
        augmented.rows_mut(0, j.nrows()).copy_from(&jh);
        for i in 0..x.len() {
            augmented[(j.nrows() + i, i)] = diag[i].max(0.0).sqrt();
        }
        let svd = augmented.svd(true, true);
        let u = svd.u.unwrap();
        let vs = svd.v_t.unwrap().transpose();
        let uf = u.rows(0, f.len()).transpose() * &f;
        let theta = 0.995f64.max(1.0 - gnorm);
        let base = 0.5 * f.norm_squared();
        let mut accepted = false;
        let mut termination = None;
        for _ in 0..100 {
            let (ph, a) = trust_step(&uf, &svd.singular_values, &vs, radius, j.nrows(), alpha);
            alpha = a;
            let (step, step_h, predicted) =
                select(&x, &jh, &diag, &gh, ph, &d, radius, bounds, theta);
            let mut next = &x + &step;
            for i in 0..next.len() {
                if next[i] <= bounds[i][0] {
                    next[i] = bounds[i][0].next_up();
                } else if next[i] >= bounds[i][1] {
                    next[i] = bounds[i][1].next_down();
                }
            }
            let nextf = DVector::from_vec(residual(next.as_slice())?);
            let next_cost = 0.5 * nextf.norm_squared();
            let reduction = base - next_cost;
            let ratio = if predicted > 0.0 {
                reduction / predicted
            } else if predicted == 0.0 && reduction == 0.0 {
                1.0
            } else {
                0.0
            };
            let next_radius = if ratio < 0.25 {
                0.25 * step_h.norm()
            } else if ratio > 0.75 && step_h.norm() > 0.95 * radius {
                2.0 * radius
            } else {
                radius
            };
            let ftol = reduction < 1e-8 * base && ratio > 0.25;
            let xtol = step.norm() < 1e-8 * (1e-8 + x.norm());
            if ftol || xtol {
                termination = Some(if ftol {
                    "cost_tolerance"
                } else {
                    "step_tolerance"
                });
            }
            if reduction > 0.0 {
                x = next;
                f = nextf;
                accepted = true;
            }
            if termination.is_some() {
                break;
            }
            alpha *= radius / next_radius;
            radius = next_radius;
            if accepted {
                break;
            }
        }
        if let Some(reason) = termination {
            return Ok((x.as_slice().to_vec(), f.as_slice().to_vec(), reason.into()));
        }
        if accepted {
            j = derivative(x.as_slice(), f.as_slice())?;
            g = j.transpose() * &f;
        } else {
            return Err("Trust-region step failed".into());
        }
    }
    Err("iteration_budget".into())
}
pub fn jacobian<F>(
    residual: &F,
    p: &[f64],
    r: &[f64],
    bounds: &[[f64; 2]],
) -> Result<DMatrix<f64>, String>
where
    F: Fn(&[f64]) -> Result<Vec<f64>, String>,
{
    let mut jac = DMatrix::zeros(r.len(), p.len());
    for k in 0..p.len() {
        let mut h = f64::EPSILON.sqrt() * p[k].abs().max(1.0) * if p[k] < 0.0 { -1.0 } else { 1.0 };
        if p[k] + h > bounds[k][1] || p[k] + h < bounds[k][0] {
            h = -h;
        }
        let mut next = p.to_vec();
        next[k] = (p[k] + h).clamp(bounds[k][0], bounds[k][1]);
        h = next[k] - p[k];
        if h == 0.0 {
            return Err("Zero finite-difference interval".into());
        }
        let f = residual(&next)?;
        for i in 0..r.len() {
            jac[(i, k)] = (f[i] - r[i]) / h;
        }
    }
    Ok(jac)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn solves_correlated_parameters_and_respects_bounds() {
        let residual = |p: &[f64]| Ok(vec![p[0] + 2.0 * p[1] - 5.0, 3.0 * p[0] - p[1] - 1.0]);
        let (p, _, _) = solve(&residual, &[0.5, 0.5], &[[0.0, 10.0], [0.0, 10.0]]).unwrap();
        assert!((p[0] - 1.0).abs() < 1e-7 && (p[1] - 2.0).abs() < 1e-7);
        let residual = |p: &[f64]| Ok(vec![p[0] - 4.0, 2.0 * (p[0] - 4.0)]);
        let (p, _, _) = solve(&residual, &[0.5], &[[0.0, 1.0]]).unwrap();
        assert!((p[0] - 1.0).abs() < 1e-7);
    }
}
