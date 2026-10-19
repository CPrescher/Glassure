//! Small numerical helpers shared by corrections, extrapolation and optimization.
use levenberg_marquardt::{LeastSquaresProblem, LevenbergMarquardt};
use nalgebra::{DMatrix, DVector, Dyn, VecStorage, U1};

/// Half-open grid following NumPy's floating-point step convention, capped at
/// one million values. Step must be finite and nonzero.
pub fn arange(start: f64, stop: f64, step: f64) -> Result<Vec<f64>, String> {
    if !start.is_finite() || !stop.is_finite() || !step.is_finite() || step == 0.0 {
        return Err("Invalid grid".into());
    }
    let count = ((stop - start) / step).ceil().max(0.0);
    if count > 1_000_000.0 {
        return Err("Grid allocation limit".into());
    }
    let actual = (start + step) - start;
    Ok((0..count as usize)
        .map(|i| start + i as f64 * actual)
        .collect())
}

/// SVD least squares with a dimension-scaled machine-epsilon rank threshold.
pub fn lsq(a: &DMatrix<f64>, y: &DVector<f64>) -> Result<DVector<f64>, String> {
    if a.nrows() == 0
        || a.ncols() == 0
        || a.nrows() != y.len()
        || a.iter().chain(y.iter()).any(|v| !v.is_finite())
    {
        return Err("Invalid least-squares arrays".into());
    }
    let svd = a.clone().svd(true, true);
    let max = svd.singular_values.iter().copied().fold(0.0, f64::max);
    let eps = f64::EPSILON * a.nrows().max(a.ncols()) as f64 * max;
    svd.solve(y, eps.max(f64::MIN_POSITIVE))
        .map_err(str::to_string)
}

/// Least-squares polynomial constrained through the origin, degree 1–64.
/// Returns ascending coefficients for x¹ through x^degree, **without** a
/// constant term. Fits scaled coordinates before converting coefficients back.
pub fn polynomial_origin(x: &[f64], y: &[f64], degree: usize) -> Result<Vec<f64>, String> {
    if x.is_empty() || x.len() != y.len() || x.iter().chain(y).any(|v| !v.is_finite()) {
        return Err("Invalid polynomial arrays".into());
    }
    if degree == 0 || degree > 64 {
        return Err("Polynomial degree must be in 1..64".into());
    }
    let scale = x.iter().map(|v| v.abs()).fold(0.0, f64::max);
    if scale == 0.0 {
        return Ok(vec![0.0; degree]);
    }
    let a = DMatrix::from_fn(x.len(), degree, |i, j| (x[i] / scale).powi((j + 1) as i32));
    let beta = lsq(&a, &DVector::from_column_slice(y))?;
    Ok(beta
        .iter()
        .enumerate()
        .map(|(j, v)| v / scale.powi((j + 1) as i32))
        .collect())
}
/// Evaluate coefficients in ascending order, **including** the constant term.
pub fn polyval_ascending(c: &[f64], x: f64) -> f64 {
    c.iter().rev().fold(0.0, |v, c| v * x + c)
}

/// Cubic interpolating/smoothing spline evaluated at requested coordinates.
/// `None` uses smoothing factor x.len(); `Some(0.0)` requests interpolation.
/// Outside the data domain, extrapolates the end polynomial.
pub fn spline_values(
    x: &[f64],
    y: &[f64],
    out: &[f64],
    s: Option<f64>,
) -> Result<Vec<f64>, String> {
    if x.len() < 4
        || x.len() != y.len()
        || x.iter().chain(y).chain(out).any(|v| !v.is_finite())
        || x.windows(2).any(|w| w[1] <= w[0])
    {
        return Err("Cubic spline needs four increasing points".into());
    }
    let smoothing = s.unwrap_or(x.len() as f64);
    if !smoothing.is_finite() || smoothing < 0.0 {
        return Err("Invalid spline smoothing factor".into());
    }
    let spline = splinefit::CubicSplineFit::new(x.to_vec(), y.to_vec())
        .smoothing_spline((smoothing / x.len() as f64).sqrt())
        .map_err(|e| e.to_string())?;
    // Extrapolate end polynomials as scipy UnivariateSpline(ext=0) does.
    let knots = &spline.t;
    let c = &spline.c;
    Ok(out
        .iter()
        .map(|v| {
            let k = knots
                .partition_point(|t| t <= v)
                .saturating_sub(1)
                .clamp(3, c.len() - 1);
            let mut d = [0.0; 4];
            d.copy_from_slice(&c[k - 3..=k]);
            for r in 1..=3 {
                for j in (r..=3).rev() {
                    let i = k - 3 + j;
                    let a = (v - knots[i]) / (knots[i + 4 - r] - knots[i]);
                    d[j] = (1.0 - a) * d[j - 1] + a * d[j];
                }
            }
            d[3]
        })
        .collect())
}

struct PolyProblem {
    p: DVector<f64>,
    x: Vec<f64>,
    y: Vec<f64>,
    y0: f64,
}
impl PolyProblem {
    fn residual(&self, p: &DVector<f64>) -> DVector<f64> {
        let a = (p[0] * p[0] + 1.0).sqrt() - 1.0;
        let b = (p[1] * p[1] + 1.0).sqrt() - 1.0;
        let c = p[2];
        DVector::from_iterator(
            self.x.len(),
            self.x
                .iter()
                .zip(&self.y)
                .map(|(x, y)| y - (x - c) * a - (x - c).powi(2) * b + self.y0),
        )
    }
}
impl LeastSquaresProblem<f64, Dyn, Dyn> for PolyProblem {
    type ResidualStorage = VecStorage<f64, Dyn, U1>;
    type JacobianStorage = VecStorage<f64, Dyn, Dyn>;
    type ParameterStorage = VecStorage<f64, Dyn, U1>;
    fn set_params(&mut self, p: &DVector<f64>) {
        self.p = p.clone();
    }
    fn params(&self) -> DVector<f64> {
        self.p.clone()
    }
    fn residuals(&self) -> Option<DVector<f64>> {
        Some(self.residual(&self.p))
    }
    fn jacobian(&self) -> Option<DMatrix<f64>> {
        let f = self.residual(&self.p);
        let mut jac = DMatrix::zeros(f.len(), 3);
        for j in 0..3 {
            let mut p = self.p.clone();
            let h = if p[j] == 0.0 { 1e-5 } else { p[j].abs() * 1e-5 };
            p[j] += h;
            let fd = self.residual(&p);
            for i in 0..f.len() {
                jac[(i, j)] = (fd[i] - f[i]) / h;
            }
        }
        Some(jac)
    }
}
/// Fit the legacy shifted quadratic low-Q extrapolation model, returning `[a,b,c]`
/// for `a*(x-c) + b*(x-c)² - y0`, subject to its reference bounds.
pub fn quadratic_extrapolation_fit(x: &[f64], y: &[f64], y0: f64) -> Result<[f64; 3], String> {
    if x.len() < 3 {
        return Err("Polynomial extrapolation needs three overlap points".into());
    }
    let p = PolyProblem {
        p: DVector::from_vec(vec![3.0f64.sqrt(), 3.0f64.sqrt(), 1.0]),
        x: x.to_vec(),
        y: y.to_vec(),
        y0,
    };
    let (result, report) = LevenbergMarquardt::new()
        .with_ftol(1.5e-8)
        .with_xtol(1.5e-8)
        .with_gtol(0.0)
        .with_patience(2000)
        .minimize(p);
    if !report.termination.was_successful() {
        return Err(format!(
            "Polynomial fit did not converge: {:?}",
            report.termination
        ));
    }
    Ok([
        (result.p[0].powi(2) + 1.0).sqrt() - 1.0,
        (result.p[1].powi(2) + 1.0).sqrt() - 1.0,
        result.p[2],
    ])
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rank_deficient_normalization_uses_minimum_norm() {
        let a = DMatrix::from_row_slice(3, 3, &[1., 0., 1., 2., 0., 2., 3., 0., 3.]);
        let p = lsq(&a, &DVector::from_vec(vec![2., 4., 6.])).unwrap();
        assert!((p[0] - 1.).abs() < 1e-12 && p[1].abs() < 1e-12 && (p[2] - 1.).abs() < 1e-12);
    }
    #[test]
    fn spline_extrapolates_end_polynomial() {
        let x: Vec<_> = (0..8).map(|i| i as f64).collect();
        let y: Vec<_> = x.iter().map(|x| x * x * x - 2. * x + 1.).collect();
        let query = [-1., 0.5, 9.];
        let values = spline_values(&x, &y, &query, None).unwrap();
        for (x, y) in query.iter().zip(values) {
            assert!((y - (x * x * x - 2. * x + 1.)).abs() < 1e-10);
        }
    }
    #[test]
    fn grid_limit_rejects_excessive_allocation() {
        assert!(arange(0., 10., 1e-12).is_err());
        assert!(arange(0., 1., 0.).is_err());
    }
}
