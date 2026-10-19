//! Derivative-free bounded scalar minimization: safeguarded parabolic steps
//! with golden-section fallback. Adapted from SciPy 1.18.0's
//! scipy/optimize/_optimize.py::_minimize_scalar_bounded (BSD-3-Clause);
//! see THIRD_PARTY_NOTICES.md.

pub fn solve<F>(
    objective: &mut F,
    bounds: [f64; 2],
    xatol: f64,
    max_evaluations: usize,
) -> Result<(f64, f64), String>
where
    F: FnMut(f64) -> Result<f64, String>,
{
    solve_from(objective, bounds, None, xatol, max_evaluations)
}

pub fn solve_from<F>(
    objective: &mut F,
    bounds: [f64; 2],
    initial: Option<f64>,
    xatol: f64,
    max_evaluations: usize,
) -> Result<(f64, f64), String>
where
    F: FnMut(f64) -> Result<f64, String>,
{
    let [mut a, mut b] = bounds;
    if !a.is_finite() || !b.is_finite() || a >= b || !xatol.is_finite() || xatol <= 0. {
        return Err("Invalid Brent bounds/tolerance".into());
    }
    if max_evaluations == 0 {
        return Err("evaluation_budget".into());
    }
    let evaluate = |objective: &mut F, x| -> Result<f64, String> {
        let value = objective(x)?;
        if !value.is_finite() {
            return Err("Nonfinite Brent objective".into());
        }
        Ok(value)
    };
    let sqrt_eps = 2.2e-16_f64.sqrt();
    let golden = 0.5 * (3. - 5_f64.sqrt());
    let mut x = a + golden * (b - a);
    if let Some(start) = initial {
        if !start.is_finite() || start < a || start > b {
            return Err("Invalid Brent starting point".into());
        }
        x = start;
    }
    let (mut w, mut v) = (x, x);
    let mut fx = evaluate(objective, x)?;
    let (mut fw, mut fv) = (fx, fx);
    let (mut d, mut e): (f64, f64) = (0., 0.);
    let mut evaluations = 1;
    loop {
        let midpoint = 0.5 * (a + b);
        let tol = sqrt_eps * x.abs() + xatol / 3.;
        let tol2 = 2. * tol;
        if (x - midpoint).abs() <= tol2 - 0.5 * (b - a) {
            return Ok((x, fx));
        }
        if evaluations >= max_evaluations {
            return Err("evaluation_budget".into());
        }
        let mut parabolic = false;
        if e.abs() > tol {
            let r = (x - w) * (fx - fv);
            let mut q = (x - v) * (fx - fw);
            let mut p = (x - v) * q - (x - w) * r;
            q = 2. * (q - r);
            if q > 0. {
                p = -p;
            }
            q = q.abs();
            let previous = e;
            e = d;
            if p.abs() < (0.5 * q * previous).abs() && p > q * (a - x) && p < q * (b - x) {
                d = p / q;
                let trial = x + d;
                if trial - a < tol2 || b - trial < tol2 {
                    d = if midpoint >= x { tol } else { -tol };
                }
                parabolic = true;
            }
        }
        if !parabolic {
            e = if x >= midpoint { a - x } else { b - x };
            d = golden * e;
        }
        let u = x + if d >= 0. {
            d.abs().max(tol)
        } else {
            -d.abs().max(tol)
        };
        let fu = evaluate(objective, u)?;
        evaluations += 1;
        if fu <= fx {
            if u >= x {
                a = x;
            } else {
                b = x;
            }
            v = w;
            fv = fw;
            w = x;
            fw = fx;
            x = u;
            fx = fu;
        } else {
            if u < x {
                a = u;
            } else {
                b = u;
            }
            if fu <= fw || w == x {
                v = w;
                fv = fw;
                w = u;
                fw = fu;
            } else if fu <= fv || v == x || v == w {
                v = u;
                fv = fu;
            }
        }
    }
}

/// Find a local downhill bracket starting at the caller's density. This does
/// not search for a global minimum. Both the probe size and geometric expansion
/// depend only on the starting value, never on a prior fit's answer.
pub fn local_bracket<F>(
    objective: &mut F,
    initial: f64,
    bounds: [f64; 2],
    max_evaluations: usize,
) -> Result<([f64; 2], f64), String>
where
    F: FnMut(f64) -> Result<f64, String>,
{
    let [lo, hi] = bounds;
    if !initial.is_finite()
        || !lo.is_finite()
        || !hi.is_finite()
        || lo >= hi
        || initial < lo
        || initial > hi
    {
        return Err("Invalid Brent bracket".into());
    }
    let mut evaluations = 0;
    let mut eval = |x| -> Result<f64, String> {
        if evaluations >= max_evaluations {
            return Err("evaluation_budget".into());
        }
        evaluations += 1;
        let value = objective(x)?;
        if !value.is_finite() {
            return Err("Nonfinite Brent objective".into());
        }
        Ok(value)
    };
    let f0 = eval(initial)?;
    let step = 0.1 * initial.abs().max(1.);
    let left = (initial - step).max(lo);
    let right = (initial + step).min(hi);
    let fl = if left == initial { f0 } else { eval(left)? };
    let fr = if right == initial { f0 } else { eval(right)? };
    if f0 <= fl && f0 <= fr {
        return Ok(([left, right], initial));
    }
    let (mut x, mut fx) = if fl < fr { (left, fl) } else { (right, fr) };
    let mut previous = initial;
    for _ in 0..max_evaluations {
        let next = (x + (1. + 5_f64.sqrt()) / 2. * (x - previous)).clamp(lo, hi);
        if next == x {
            return Ok(([previous.min(x), previous.max(x)], x));
        }
        let fnext = eval(next)?;
        if fnext >= fx {
            return Ok(([previous.min(next), previous.max(next)], x));
        }
        previous = x;
        x = next;
        fx = fnext;
    }
    Err("evaluation_budget".into())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn quadratic_and_nonquadratic_minima() {
        for power in [2, 4] {
            let mut calls = 0;
            let (x, f) = solve(
                &mut |x| {
                    calls += 1;
                    Ok((x - 2.345).powi(2) + (x - 2.345).powi(power))
                },
                [1e-12, 100.],
                1e-8,
                100,
            )
            .unwrap();
            assert!((x - 2.345).abs() < 1e-7 && f < 1e-14);
            assert!(calls < 30);
        }
    }
    #[test]
    fn endpoint_and_flat_minima_stay_within_bounds() {
        for slope in [-1., 0., 1.] {
            let (x, _) = solve(
                &mut |x| {
                    assert!((0.01..=100.).contains(&x));
                    Ok(slope * x)
                },
                [0.01, 100.],
                1e-8,
                100,
            )
            .unwrap();
            if slope > 0. {
                assert!((x - 0.01).abs() < 1e-7);
            }
            if slope < 0. {
                assert!((x - 100.).abs() < 1e-5);
            }
        }
    }
    #[test]
    fn budgets_invalid_inputs_and_objective_errors_propagate() {
        assert_eq!(
            solve(&mut |x| Ok(x * x), [0., 1.], 1e-8, 1).unwrap_err(),
            "evaluation_budget"
        );
        assert!(solve(&mut |_| Ok(0.), [1., 0.], 1e-8, 100).is_err());
        assert_eq!(
            solve(&mut |_| Ok(f64::NAN), [0., 1.], 1e-8, 100).unwrap_err(),
            "Nonfinite Brent objective"
        );
        assert_eq!(
            solve(
                &mut |_| Err("calculation failed".into()),
                [0., 1.],
                1e-8,
                100
            )
            .unwrap_err(),
            "calculation failed"
        );
    }
    #[test]
    fn downhill_bracket_finds_nearby_well_and_respects_endpoints() {
        let mut f = |x: f64| Ok((x - 3.).powi(2) * (x - 30.).powi(2));
        let (bounds, at) = local_bracket(&mut f, 2., [1e-12, 100.], 100).unwrap();
        assert!(bounds[0] < 3. && bounds[1] > 3. && bounds[1] < 30.);
        let (x, _) = solve_from(&mut f, bounds, Some(at), 1e-8, 100).unwrap();
        assert!((x - 3.).abs() < 1e-7);
        for initial in [0., 1.] {
            let mut f = |x: f64| Ok(-x);
            let (bounds, at) = local_bracket(&mut f, initial, [0., 1.], 100).unwrap();
            let (x, _) = solve_from(&mut f, bounds, Some(at), 1e-8, 100).unwrap();
            assert_eq!(x, 1.);
        }
    }
}
