#![doc = include_str!("../README.md")]

mod bounded_brent;
mod bounded_trf;
pub mod corrections;
pub mod density;
pub mod functions;
pub mod numeric;
pub mod parallel;
pub mod pattern;
mod prepared;
#[cfg(feature = "profiling")]
pub mod profiling;
pub mod project;
pub mod request;
pub mod scattering;
pub mod sq_optimization;
pub mod tutorial;
mod workspace;

macro_rules! profile_span {
    ($stage:ident) => {
        #[cfg(feature = "profiling")]
        let _profile_span = crate::profiling::Span::new(crate::profiling::Stage::$stage);
    };
}
pub(crate) use profile_span;
mod xraylib;
pub use sq_optimization::SqOptimization;

use rustfft::{num_complex::Complex, FftPlanner};
use std::{cell::RefCell, f64::consts::PI};

thread_local! {
    // Match a warm numerical library: retain plans, but allocate work/output
    // buffers on each evaluation. Both the native and WASM builds use this code.
    static PLANNER: RefCell<FftPlanner<f64>> = RefCell::new(FftPlanner::new());
}

#[derive(Clone, Copy, Debug)]
/// Fourier-transform implementation. FFT follows Glassure's padding and indexing
/// convention; direct integration uses the trapezoidal rule.
pub enum Method {
    /// Direct numerical integration.
    Integral,
    /// FFT followed by interpolation onto the requested output grid.
    Fft,
}

#[derive(Debug, PartialEq)]
#[repr(u32)]
/// Validation/calculation errors for the low-level array pipeline and its ABI.
/// Higher-level operations return descriptive `String` errors instead.
pub enum Error {
    InvalidShape = 1,
    InvalidValues = 2,
    InvalidGrid = 3,
    SingularNormalization = 4,
    FftTooLarge = 5,
    InvalidMethod = 6,
    NonFiniteResult = 7,
}

/// Borrowed inputs for integral normalization plus the forward PDF transform.
///
/// Unlike [`request::Request`], scattering moments must already be supplied.
/// All Q-dependent slices must have the same length. Q is Å⁻¹, r is Å,
/// `density` is **atomic density in atoms/Å³** and all calculations use f64.
pub struct Input<'a> {
    pub q: &'a [f64],
    pub intensity: &'a [f64],
    pub f_squared_mean: &'a [f64],
    pub f_mean_squared: &'a [f64],
    pub incoherent: &'a [f64],
    pub r: &'a [f64],
    pub density: f64,
    pub attenuation: f64,
}

#[derive(Debug)]
/// Owned intensity, S(Q), F(r) and g(r) arrays from [`evaluate`].
/// The normalized intensity still includes incoherent scattering; the structure
/// factor subtracts the supplied incoherent contribution.
pub struct Output {
    pub normalization: f64,
    pub normalized: Vec<f64>,
    pub sq: Vec<f64>,
    pub fr: Vec<f64>,
    pub gr: Vec<f64>,
}

fn increasing_nonnegative(x: &[f64]) -> bool {
    x.iter().all(|v| v.is_finite() && *v >= 0.0) && x.windows(2).all(|w| w[1] > w[0])
}

fn uniform(x: &[f64]) -> bool {
    if x.len() < 2 {
        return false;
    }
    let step = x[1] - x[0];
    // Permit roundoff from decimal grids, including Glassure's r[0]=1e-10.
    x.windows(2)
        .all(|w| ((w[1] - w[0]) - step).abs() <= 1e-7 * step.abs())
}

fn trapezoid(x: &[f64], y: &[f64]) -> f64 {
    x.windows(2)
        .zip(y.windows(2))
        .map(|(x, y)| (x[1] - x[0]) * (y[0] + y[1]) / 2.0)
        .sum()
}

/// Integrally normalize supplied intensity/scattering arrays and calculate PDFs.
///
/// Use [`request::calculate`] to start from composition and raw/background data.
/// Invalid lengths, grids, nonfinite values, singular normalization and excessive
/// FFT allocations return [`Error`]. `lorch` applies the Lorch modification.
pub fn evaluate(input: &Input<'_>, method: Method, lorch: bool) -> Result<Output, Error> {
    let n = input.q.len();
    if n < 2
        || input.r.is_empty()
        || [
            input.intensity,
            input.f_squared_mean,
            input.f_mean_squared,
            input.incoherent,
        ]
        .iter()
        .any(|a| a.len() != n)
    {
        return Err(Error::InvalidShape);
    }
    if !increasing_nonnegative(input.q) || !increasing_nonnegative(input.r) {
        return Err(Error::InvalidGrid);
    }
    if !input.density.is_finite()
        || input.density <= 0.0
        || !input.attenuation.is_finite()
        || input.attenuation < 0.0
        || [
            input.intensity,
            input.f_squared_mean,
            input.f_mean_squared,
            input.incoherent,
        ]
        .iter()
        .any(|a| a.iter().any(|v| !v.is_finite()))
        || input.f_mean_squared.iter().any(|v| *v <= 0.0)
    {
        return Err(Error::InvalidValues);
    }
    let mut n1 = Vec::with_capacity(n);
    let mut n2 = Vec::with_capacity(n);
    for i in 0..n {
        let q2 = input.q[i].powi(2);
        let attenuation = (-input.attenuation * q2).exp();
        n1.push(
            q2 * ((input.f_squared_mean[i] + input.incoherent[i]) * attenuation)
                / input.f_mean_squared[i],
        );
        n2.push(q2 * input.intensity[i] * attenuation / input.f_mean_squared[i]);
    }
    let denominator = trapezoid(input.q, &n2);
    if denominator == 0.0 || !denominator.is_finite() {
        return Err(Error::SingularNormalization);
    }
    let normalization = (-2.0 * PI.powi(2) * input.density + trapezoid(input.q, &n1)) / denominator;
    let normalized: Vec<_> = (0..n)
        .map(|i| normalization * input.intensity[i] - input.incoherent[i])
        .collect();
    let sq: Vec<_> = (0..n)
        .map(|i| {
            (normalized[i] - input.f_squared_mean[i] + input.f_mean_squared[i])
                / input.f_mean_squared[i]
        })
        .collect();
    if matches!(method, Method::Fft) && (!uniform(input.q) || !uniform(input.r)) {
        return Err(Error::InvalidGrid);
    }
    let (fr, gr) = transform(input.q, &sq, input.r, input.density, method, lorch)?;
    if !normalization.is_finite()
        || [&normalized, &sq, &fr, &gr]
            .iter()
            .any(|a| a.iter().any(|v| !v.is_finite()))
    {
        return Err(Error::NonFiniteResult);
    }
    Ok(Output {
        normalization,
        normalized,
        sq,
        fr,
        gr,
    })
}

/// Shared forward transform. High-level app requests preserve Python's existing
/// sample-index FFT convention even for quantized or measured nonuniform Q grids.
pub(crate) fn transform(
    q: &[f64],
    sq: &[f64],
    r: &[f64],
    density: f64,
    method: Method,
    lorch: bool,
) -> Result<(Vec<f64>, Vec<f64>), Error> {
    let n = q.len();
    let qmax = q[n - 1];
    let fq: Vec<_> = (0..n)
        .map(|i| {
            let angle = PI * (q[i] / qmax);
            let modification = if !lorch || angle == 0.0 {
                1.0
            } else {
                angle.sin() / angle
            };
            modification * q[i] * (sq[i] - 1.0)
        })
        .collect();
    let fr: Vec<f64> = match method {
        Method::Integral => r
            .iter()
            .map(|r| {
                let mut sum = 0.0;
                let mut previous = fq[0] * (q[0] * r).sin();
                let mut previous_q = q[0];
                for (&q, &value) in q.iter().zip(&fq).skip(1) {
                    let current = value * (q * r).sin();
                    sum += (q - previous_q) * (previous + current) / 2.0;
                    previous = current;
                    previous_q = q;
                }
                2.0 / PI * sum
            })
            .collect(),
        Method::Fft => {
            let dq = q[1] - q[0];
            let dr = r[1] - r[0];
            let target = (2.0 * PI / dr / dq).ceil();
            // Bound allocation in this prototype. Never silently truncate Q.
            if !target.is_finite() || target > (1 << 22) as f64 {
                return Err(Error::FftTooLarge);
            }
            let size = (target as usize)
                .checked_next_power_of_two()
                .ok_or(Error::FftTooLarge)?;
            if size < n {
                return Err(Error::InvalidGrid);
            }
            let mut buffer = vec![Complex::new(0.0, 0.0); size];
            for (value, real) in buffer.iter_mut().zip(&fq) {
                value.re = *real;
            }
            let fft = PLANNER.with(|p| p.borrow_mut().plan_fft_inverse(size));
            fft.process(&mut buffer);
            // RustFFT's inverse is unnormalized; numpy.ifft divides by size.
            let scale = 2.0 * (size as f64 * dq) / PI / size as f64;
            let step = 2.0 * PI / (size as f64 * dq);
            r.iter()
                .map(|r| {
                    // Same endpoint clamping and linear interpolation as np.interp.
                    if *r >= (size - 1) as f64 * step {
                        return buffer[size - 1].im * scale;
                    }
                    let lo = ((*r / step).floor() as usize).min(size - 2);
                    let x0 = lo as f64 * step;
                    let x1 = (lo + 1) as f64 * step;
                    let y0 = buffer[lo].im * scale;
                    let y1 = buffer[lo + 1].im * scale;
                    y0 + (y1 - y0) / (x1 - x0) * (r - x0)
                })
                .collect()
        }
    };
    let gr: Vec<_> = r
        .iter()
        .zip(&fr)
        .map(|(r, f)| {
            let r_safe = if *r == 0.0 { 1e-10 } else { *r };
            1.0 + f / (4.0 * PI * r_safe * density)
        })
        .collect();
    if fr.iter().chain(&gr).any(|v| !v.is_finite()) {
        return Err(Error::NonFiniteResult);
    }
    Ok((fr, gr))
}

/// Allocate a zeroed f64 buffer, owned by this library until buffer_free.
#[no_mangle]
pub extern "C" fn buffer_alloc(len: usize) -> *mut f64 {
    Box::into_raw(vec![0.0; len].into_boxed_slice()) as *mut f64
}

/// # Safety
/// `ptr` and `len` must identify an unfreed allocation from buffer_alloc.
#[no_mangle]
pub unsafe extern "C" fn buffer_free(ptr: *mut f64, len: usize) {
    if !ptr.is_null() {
        drop(Box::from_raw(std::ptr::slice_from_raw_parts_mut(ptr, len)));
    }
}

/// Packed input: q, intensity, `<f²>`, `<f>²`, incoherent (nq each), r (nr).
/// Packed output: normalization (1), normalized, sq (nq each), fr, gr (nr each).
/// Return 0 on success; otherwise an Error discriminant. Output is invalid on error.
///
/// # Safety
/// Input/output must be nonoverlapping aligned buffers valid for respectively
/// 5*nq+nr and 1+2*nq+2*nr f64 values. Caller retains ownership throughout.
#[no_mangle]
pub unsafe extern "C" fn pipeline(
    ptr: *const f64,
    nq: usize,
    nr: usize,
    density: f64,
    attenuation: f64,
    lorch: u32,
    method: u32,
    out: *mut f64,
) -> u32 {
    if ptr.is_null()
        || out.is_null()
        || !(2..=1_000_000).contains(&nq)
        || !(1..=1_000_000).contains(&nr)
    {
        return Error::InvalidShape as u32;
    }
    if lorch > 1 {
        return Error::InvalidValues as u32;
    }
    let method = match method {
        0 => Method::Integral,
        1 => Method::Fft,
        _ => return Error::InvalidMethod as u32,
    };
    let packed = std::slice::from_raw_parts(ptr, 5 * nq + nr);
    let input = Input {
        q: &packed[..nq],
        intensity: &packed[nq..2 * nq],
        f_squared_mean: &packed[2 * nq..3 * nq],
        f_mean_squared: &packed[3 * nq..4 * nq],
        incoherent: &packed[4 * nq..5 * nq],
        r: &packed[5 * nq..],
        density,
        attenuation,
    };
    match evaluate(&input, method, lorch == 1) {
        Ok(result) => {
            let output = std::slice::from_raw_parts_mut(out, 1 + 2 * nq + 2 * nr);
            output[0] = result.normalization;
            output[1..1 + nq].copy_from_slice(&result.normalized);
            output[1 + nq..1 + 2 * nq].copy_from_slice(&result.sq);
            output[1 + 2 * nq..1 + 2 * nq + nr].copy_from_slice(&result.fr);
            output[1 + 2 * nq + nr..].copy_from_slice(&result.gr);
            0
        }
        Err(error) => error as u32,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn constant_sq_is_analytic_and_q_zero_is_finite() {
        // With attenuation=0, choose density so that normalization is exactly 1.
        let q = [0.0, 1.0, 2.0];
        let intensity = [1.0; 3];
        let f2 = [2.0; 3];
        let fm2 = [1.0; 3];
        let incoherent = [0.0; 3];
        let r = [0.0, 0.1, 0.2];
        let input = Input {
            q: &q,
            intensity: &intensity,
            f_squared_mean: &f2,
            f_mean_squared: &fm2,
            incoherent: &incoherent,
            r: &r,
            density: 3.0 / (2.0 * PI.powi(2)),
            attenuation: 0.0,
        };
        for method in [Method::Integral, Method::Fft] {
            for lorch in [false, true] {
                let result = evaluate(&input, method, lorch).unwrap();
                assert!((result.normalization - 1.0).abs() < 1e-14);
                assert!(result.sq.iter().all(|v| v.abs() < 1e-14));
                assert!(result.gr.iter().all(|v| v.is_finite()));
                assert_eq!(result.fr[0], 0.0);
                assert_eq!(result.gr[0], 1.0);
            }
        }
        // Independent trapezoidal sum for S(Q)=0, without Lorch at r=0.1.
        let result = evaluate(&input, Method::Integral, false).unwrap();
        let expected = 2.0 / PI * (-0.1_f64.sin() - 0.2_f64.sin());
        assert!((result.fr[1] - expected).abs() < 1e-14);
    }

    #[test]
    fn rejects_invalid_inputs_before_calculating() {
        let q = [0.0, 1.0, 2.1];
        let ones = [1.0; 3];
        let zeros = [0.0; 3];
        let r = [0.0, 0.1];
        let mut input = Input {
            q: &q,
            intensity: &ones,
            f_squared_mean: &ones,
            f_mean_squared: &ones,
            incoherent: &zeros,
            r: &r,
            density: 0.05,
            attenuation: 0.001,
        };
        assert_eq!(
            evaluate(&input, Method::Fft, true).unwrap_err(),
            Error::InvalidGrid
        );
        assert!(evaluate(&input, Method::Integral, true).is_ok());
        input.intensity = &zeros;
        assert_eq!(
            evaluate(&input, Method::Integral, false).unwrap_err(),
            Error::SingularNormalization
        );
        input.intensity = &ones;
        input.f_mean_squared = &zeros;
        assert_eq!(
            evaluate(&input, Method::Integral, false).unwrap_err(),
            Error::InvalidValues
        );
        input.f_mean_squared = &ones;
        input.density = f64::NAN;
        assert_eq!(
            evaluate(&input, Method::Integral, false).unwrap_err(),
            Error::InvalidValues
        );
        input.density = 0.05;
        input.intensity = &ones[..2];
        assert_eq!(
            evaluate(&input, Method::Integral, false).unwrap_err(),
            Error::InvalidShape
        );
    }
}
