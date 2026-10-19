//! Low-r artifact corrections applied to S(Q) before the final PDF transform.
//! [`optimize`] accepts atomic density (atoms/Å³), not mass density.
use crate::{
    numeric::{arange, polynomial_origin, polyval_ascending},
    transform, Method, PLANNER,
};
use rustfft::num_complex::Complex;
use serde::{Deserialize, Serialize};
use std::f64::consts::PI;

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
/// Iterative Kaplow or polynomial S(Q) optimization settings.
pub struct SqOptimization {
    /// `"iterative"` or `"fit"` (polynomial correction through the origin).
    pub method: String,
    /// Low-r cutoff below the first physical pair peak, in Å.
    pub r_cutoff: f64,
    #[serde(default = "iterations")]
    /// Iterative passes, at most 1000; ignored by polynomial optimization.
    pub iterations: usize,
    #[serde(default)]
    /// Lorch modification during iterative optimization; independent of the
    /// final transform's modification setting.
    pub lorch: bool,
    #[serde(default = "one")]
    /// Positive iterative correction divisor (default 1); ignored by polynomial fit.
    pub attenuation: f64,
}
fn iterations() -> usize {
    5
}
fn one() -> f64 {
    1.0
}

/// Correct S(Q) on the supplied Q grid (Å⁻¹), using atomic density (atoms/Å³).
/// `r_step` and `r_cutoff` are Å. Returns corrected values on the same Q grid.
/// Polynomial degree is derived from Q_max*r_cutoff/π and capped at 64.
/// Invalid grids/settings and nonfinite corrections return errors.
pub fn optimize(
    q: &[f64],
    sq: &[f64],
    density: f64,
    r_step: f64,
    method: Method,
    opt: &SqOptimization,
) -> Result<Vec<f64>, String> {
    if q.len() < 2
        || q.len() != sq.len()
        || q.iter().chain(sq).any(|v| !v.is_finite())
        || q.windows(2).any(|v| v[1] < v[0])
        || !r_step.is_finite()
        || r_step <= 0.
        || !density.is_finite()
        || density <= 0.
    {
        return Err("Invalid optimization inputs".into());
    }
    if !opt.r_cutoff.is_finite()
        || opt.r_cutoff <= 0.0
        || opt.iterations > 1000
        || !opt.attenuation.is_finite()
        || opt.attenuation <= 0.0
    {
        return Err("Invalid S(Q) optimization settings".into());
    }
    match opt.method.as_str() {
        "fit" => {
            let degree = (q[q.len() - 1] * opt.r_cutoff / PI).max(1.0);
            if degree > 64.0 {
                return Err("S(Q) polynomial exceeds degree limit 64".into());
            }
            let low = degree.floor() as usize;
            let high = degree.ceil() as usize;
            let fq: Vec<_> = q.iter().zip(sq).map(|(q, s)| q * (s - 1.0)).collect();
            let a = polynomial_origin(q, &fq, low)?;
            let b = if low == high {
                a.clone()
            } else {
                polynomial_origin(q, &fq, high)?
            };
            Ok(q.iter()
                .zip(sq)
                .map(|(q, s)| {
                    s - if low == high {
                        polyval_ascending(&a, *q)
                    } else {
                        polyval_ascending(&a, *q) * (high as f64 - degree)
                            + polyval_ascending(&b, *q) * (degree - low as f64)
                    }
                })
                .collect())
        }
        "iterative" => {
            let r = arange(0.0, opt.r_cutoff, r_step)?;
            if r.len() < 2 {
                return Err("Optimization needs at least two low-r points".into());
            }
            let mut result = sq.to_vec();
            for _ in 0..opt.iterations {
                let (fr, _) = transform(q, &result, &r, density, method, opt.lorch)
                    .map_err(|e| format!("Optimization transform: {e:?}"))?;
                let delta: Vec<_> = r
                    .iter()
                    .zip(fr)
                    .map(|(r, f)| f + 4.0 * PI * r * density)
                    .collect();
                let iq = back_integral(&r, &delta, q, method)?;
                for (i, s) in result.iter_mut().enumerate() {
                    *s *= 1.0 - iq[i] / opt.attenuation;
                }
                if result.iter().any(|v| !v.is_finite()) {
                    return Err("S(Q) optimization produced nonfinite values".into());
                }
            }
            Ok(result)
        }
        _ => Err("Unknown S(Q) optimization method".into()),
    }
}

fn back_integral(r: &[f64], fr: &[f64], q: &[f64], method: Method) -> Result<Vec<f64>, String> {
    let integral = match method {
        Method::Integral => q
            .iter()
            .map(|q| {
                r.windows(2)
                    .zip(fr.windows(2))
                    .map(|(r, f)| {
                        (r[1] - r[0]) * (f[0] * (r[0] * q).sin() + f[1] * (r[1] * q).sin()) / 2.0
                    })
                    .sum()
            })
            .collect::<Vec<f64>>(),
        Method::Fft => {
            let dr = r[1] - r[0];
            let dq = q[1] - q[0];
            let target = (PI / (dq * dr)).trunc().max(r.len() as f64);
            if !target.is_finite() || target > 4194304.0 {
                return Err("Inverse FFT allocation limit".into());
            }
            let size = (target as usize).next_power_of_two();
            let mut buf = vec![Complex::new(0.0, 0.0); size];
            for (z, f) in buf.iter_mut().zip(fr) {
                z.re = *f;
            }
            let fft = PLANNER.with(|p| p.borrow_mut().plan_fft_inverse(size));
            fft.process(&mut buf);
            let step = 2.0 * PI / (size as f64 * dr);
            q.iter()
                .map(|q| {
                    if *q <= 0.0 {
                        return buf[0].im * dr;
                    }
                    if *q >= (size - 1) as f64 * step {
                        return buf[size - 1].im * dr;
                    }
                    let lo = ((*q / step).floor() as usize).min(size - 2);
                    let x = lo as f64 * step;
                    let next = (lo + 1) as f64 * step;
                    let a = buf[lo].im * dr;
                    let b = buf[lo + 1].im * dr;
                    a + (b - a) / (next - x) * (q - x)
                })
                .collect()
        }
    };
    // Python's inverse adds one, then its caller subtracts one, before applying
    // the correction. Keep that rounding, rather than cancelling it algebraically.
    Ok(integral
        .iter()
        .zip(q)
        .map(|(i, q)| (1.0 + i / q) - 1.0)
        .collect())
}
