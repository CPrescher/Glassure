//! Standalone scientific operations used independently of the full PDF pipeline.
use crate::{
    numeric,
    pattern::Pattern,
    scattering::{self, Composition, Source},
    Method,
};
use nalgebra::{DMatrix, DVector};
use serde::{Deserialize, Serialize};
use std::f64::consts::PI;

/// Parse `"fft"` or `"integral"`; reject all other names.
pub fn method(value: &str) -> Result<Method, String> {
    match value {
        "fft" => Ok(Method::Fft),
        "integral" => Ok(Method::Integral),
        _ => Err(format!("Unknown transform method: {value}")),
    }
}
fn arrays(values: &[&[f64]]) -> Result<(), String> {
    let n = values.first().map_or(0, |v| v.len());
    if n == 0
        || values
            .iter()
            .any(|v| v.len() != n || v.iter().any(|v| !v.is_finite()))
    {
        return Err("Arrays must be finite, nonempty and of matching length".into());
    }
    Ok(())
}
fn grid(values: &[f64]) -> Result<(), String> {
    if values.len() < 2
        || values.len() > 1_000_000
        || values.iter().any(|v| !v.is_finite() || *v < 0.)
        || values.windows(2).any(|v| v[1] < v[0])
        || values[1] <= values[0]
    {
        return Err("Grid needs at least two increasing nonnegative values".into());
    }
    Ok(())
}
fn forward_q_grid(values: &[f64]) -> Result<(), String> {
    if let Err(error) = grid(values) {
        // Python extrapolation chooses the grid point nearest zero and can
        // include one negative endpoint up to half a step below zero. This is
        // a valid S(Q) output, not a negative measured-Q grid. Keep the original
        // coordinates/arithmetic, as the full Rust/Python pipelines already do.
        if values.len() < 3 || values[0] >= 0. || !values[0].is_finite() {
            return Err(error);
        }
        grid(&values[1..])?;
        let step = values[1] - values[0];
        let tolerance = 64. * f64::EPSILON * values.last().unwrap().abs().max(1.);
        if -values[0] > 0.5 * step + tolerance {
            return Err(error);
        }
    }
    Ok(())
}
/// Calculate `S(Q) = (I_normalized - <f²> + <f>²) / <f>²`.
/// The input intensity must already have incoherent scattering subtracted;
/// both scattering-moment arrays must match the pattern length.
pub fn calculate_sq(pattern: &Pattern, f2: &[f64], fm2: &[f64]) -> Result<Pattern, String> {
    pattern.validate()?;
    arrays(&[&pattern.y, f2, fm2])?;
    Pattern::new(
        pattern.x.clone(),
        pattern
            .y
            .iter()
            .zip(f2)
            .zip(fm2)
            .map(|((y, f2), fm2)| (y - f2 + fm2) / fm2)
            .collect(),
    )
}
/// Transform S(Q) versus Q (Å⁻¹) to F(r) (Å⁻²) on the supplied r grid (Å).
/// Uses `2/π * integral Q[S(Q)-1] sin(Qr) dQ`; `lorch` applies sin(x)/x
/// with x = πQ/Q_max. FFT preserves Glassure's padding/indexing convention.
pub fn calculate_fr(
    pattern: &Pattern,
    r: &[f64],
    method: Method,
    lorch: bool,
) -> Result<Pattern, String> {
    pattern.validate()?;
    forward_q_grid(&pattern.x)?;
    if r.len() != 1 || !matches!(method, Method::Integral) {
        grid(r)?;
    } else if !r[0].is_finite() || r[0] < 0. {
        return Err("Invalid r grid".into());
    }
    let (fr, _) = crate::transform(&pattern.x, &pattern.y, r, 1., method, lorch)
        .map_err(|e| format!("Transform: {e:?}"))?;
    Pattern::new(r.to_vec(), fr)
}
/// Inverse transform F(r) (Å⁻²) to dimensionless S(Q) on Q in Å⁻¹.
/// Without Lorch inversion, the Q=0 value uses its removable-limit integral.
pub fn calculate_sq_from_fr(
    pattern: &Pattern,
    q: &[f64],
    method: Method,
    lorch: bool,
) -> Result<Pattern, String> {
    pattern.validate()?;
    grid(&pattern.x)?;
    if q.len() != 1 || !matches!(method, Method::Integral) {
        grid(q)?;
    } else if !q[0].is_finite() || q[0] < 0. {
        return Err("Invalid Q grid".into());
    }
    let r = &pattern.x;
    let fr = &pattern.y;
    let iq = match method {
        Method::Integral => q
            .iter()
            .map(|q| {
                r.windows(2)
                    .zip(fr.windows(2))
                    .map(|(r, f)| {
                        (r[1] - r[0]) * (f[0] * (q * r[0]).sin() + f[1] * (q * r[1]).sin()) / 2.
                    })
                    .sum()
            })
            .collect::<Vec<f64>>(),
        Method::Fft => {
            use rustfft::num_complex::Complex;
            let dr = r[1] - r[0];
            let dq = q[1] - q[0];
            let target = (PI / (dq * dr)) as usize;
            let n = r
                .len()
                .max(target)
                .checked_next_power_of_two()
                .ok_or("FFT size overflow")?;
            if n > 1 << 22 {
                return Err("FFT allocation limit".into());
            }
            let mut buffer = vec![Complex::new(0., 0.); n];
            for (v, y) in buffer.iter_mut().zip(fr) {
                v.re = *y;
            }
            crate::PLANNER
                .with(|p| p.borrow_mut().plan_fft_inverse(n))
                .process(&mut buffer);
            let step = 2. * PI / (n as f64 * dr);
            q.iter()
                .map(|q| {
                    if *q >= (n - 1) as f64 * step {
                        return buffer[n - 1].im * dr;
                    }
                    let i = (*q / step).floor() as usize;
                    (buffer[i].im
                        + (buffer[i + 1].im - buffer[i].im) * (*q - i as f64 * step) / step)
                        * dr
                })
                .collect()
        }
    };
    let mut values: Vec<f64> = iq
        .iter()
        .zip(q)
        .map(|(i, q)| if *q == 0. { f64::NAN } else { i / q })
        .collect();
    if lorch {
        let qmax = q[q.len() - 1];
        let valid: Vec<usize> = q
            .iter()
            .enumerate()
            .filter(|(_, q)| qmax / PI * (PI * **q / qmax).sin() > 1e-9)
            .map(|(i, _)| i)
            .collect();
        if valid.len() < 2 {
            return Err("Insufficient stable points for Lorch inverse".into());
        }
        for &i in &valid {
            let x = PI * q[i] / qmax;
            values[i] = iq[i] / (q[i] * x.sin() / x);
        }
        for i in 0..q.len() {
            if !valid.contains(&i) {
                let at = valid
                    .partition_point(|j| q[*j] <= q[i])
                    .saturating_sub(1)
                    .min(valid.len() - 2);
                let (a, b) = (valid[at], valid[at + 1]);
                values[i] = values[a] + (values[b] - values[a]) * (q[i] - q[a]) / (q[b] - q[a]);
            }
        }
    } else if q[0] == 0. {
        values[0] = r
            .windows(2)
            .zip(fr.windows(2))
            .map(|(r, f)| (r[1] - r[0]) * (r[0] * f[0] + r[1] * f[1]) / 2.)
            .sum();
    }
    Pattern::new(q.to_vec(), values.iter().map(|v| 1. + v).collect())
}
/// Inverse transform dimensionless g(r) to S(Q).
/// `density` is atomic density in atoms/Å³; this Rust helper honors `method`.
pub fn calculate_sq_from_gr(
    pattern: &Pattern,
    q: &[f64],
    density: f64,
    method: Method,
) -> Result<Pattern, String> {
    let fr = Pattern::new(
        pattern.x.clone(),
        pattern
            .x
            .iter()
            .zip(&pattern.y)
            .map(|(r, g)| (g - 1.) * 4. * PI * r * density)
            .collect(),
    )?;
    calculate_sq_from_fr(&fr, q, method, false)
}
/// Convert F(r) to `g(r) = 1 + F(r)/(4πρr)` using atomic density in atoms/Å³.
/// For r=0 the denominator uses Glassure's 1e-10 Å convention.
pub fn calculate_gr(pattern: &Pattern, density: f64) -> Result<Pattern, String> {
    if !density.is_finite() || density <= 0. {
        return Err("Positive atomic density required".into());
    }
    Pattern::new(
        pattern.x.clone(),
        pattern
            .x
            .iter()
            .zip(&pattern.y)
            .map(|(r, f)| {
                let r = if *r == 0. { 1e-10 } else { *r };
                1. + f / (4. * PI * r * density)
            })
            .collect(),
    )
}
/// Convert g(r) to `RDF(r) = 4πρr²g(r)` (Å⁻¹); density is atoms/Å³.
pub fn calculate_rdf(pattern: &Pattern, density: f64) -> Result<Pattern, String> {
    Pattern::new(
        pattern.x.clone(),
        pattern
            .x
            .iter()
            .zip(&pattern.y)
            .map(|(r, g)| 4. * PI * r * r * g * density)
            .collect(),
    )
}
/// Convert g(r) to `T(r) = 4πρrg(r)` (Å⁻²); density is atoms/Å³.
pub fn calculate_tr(pattern: &Pattern, density: f64) -> Result<Pattern, String> {
    Pattern::new(
        pattern.x.clone(),
        pattern
            .x
            .iter()
            .zip(&pattern.y)
            .map(|(r, g)| 4. * PI * r * g * density)
            .collect(),
    )
}
/// Integral normalization, returning (multiplier, normalized intensity).
/// `density` is atoms/Å³. `inc = None` means zero incoherent scattering.
/// The returned intensity includes incoherent scattering, as in Python.
pub fn normalize(
    pattern: &Pattern,
    density: f64,
    f2: &[f64],
    fm2: &[f64],
    inc: Option<&[f64]>,
    attenuation: f64,
) -> Result<(f64, Pattern), String> {
    pattern.validate()?;
    arrays(&[&pattern.y, f2, fm2])?;
    let zeros = vec![0.; pattern.x.len()];
    let inc = inc.unwrap_or(&zeros);
    arrays(&[&pattern.y, inc])?;
    let input = crate::Input {
        q: &pattern.x,
        intensity: &pattern.y,
        f_squared_mean: f2,
        f_mean_squared: fm2,
        incoherent: inc,
        r: &[0.],
        density,
        attenuation,
    };
    let value = crate::evaluate(&input, Method::Integral, false)
        .map_err(|e| format!("Normalization: {e:?}"))?;
    Ok((
        value.normalization,
        Pattern::new(pattern.x.clone(), value.normalized)?,
    ))
}
/// Weighted high-Q normalization fit, returning coefficients and intensity
/// after multiple, incoherent and container contributions are subtracted.
/// `cutoff` is Å⁻¹; scaling is `"linear"` (Q) or `"squared"` (Q²).
/// Optional incoherent/container arrays must match the pattern length.
pub fn normalize_fit(
    pattern: &Pattern,
    f2: &[f64],
    inc: Option<&[f64]>,
    cutoff: f64,
    scaling: &str,
    multiple: bool,
    container: Option<&[f64]>,
) -> Result<(crate::request::NormalizationParameters, Pattern), String> {
    pattern.validate()?;
    arrays(&[&pattern.y, f2])?;
    let zero = vec![0.; pattern.x.len()];
    let inc = inc.unwrap_or(&zero);
    let cont = container.unwrap_or(&zero);
    arrays(&[&pattern.y, inc, cont])?;
    if !["linear", "squared"].contains(&scaling) {
        return Err("Invalid normalization scaling".into());
    }
    let indices: Vec<_> = pattern
        .x
        .iter()
        .enumerate()
        .filter(|(_, q)| **q > cutoff)
        .map(|(i, _)| i)
        .collect();
    if indices.is_empty() {
        return Err("No Q values above cutoff".into());
    }
    let w = |i: usize| {
        if scaling == "squared" {
            pattern.x[i] * pattern.x[i]
        } else {
            pattern.x[i]
        }
    };
    let (mut params, mut residual) = (crate::request::NormalizationParameters::default(), 0.);
    if !multiple && container.is_none() {
        let num: f64 = indices
            .iter()
            .map(|i| pattern.y[*i] * (f2[*i] + inc[*i]) * w(*i).powi(2))
            .sum();
        let den: f64 = indices
            .iter()
            .map(|i| (pattern.y[*i] * w(*i)).powi(2))
            .sum();
        params.n = num / den;
    } else {
        let scale = indices
            .iter()
            .map(|i| pattern.y[*i].abs())
            .fold(0., f64::max);
        let cs = indices.iter().map(|i| cont[*i].abs()).fold(0., f64::max);
        let scale = if scale == 0. { 1. } else { scale };
        let cs = if cs == 0. { 1. } else { cs };
        let a = DMatrix::from_fn(indices.len(), 3, |j, k| {
            let i = indices[j];
            w(i) * match k {
                0 => pattern.y[i] / scale,
                1 => cont[i] / cs,
                _ => {
                    if multiple {
                        1.
                    } else {
                        0.
                    }
                }
            }
        });
        let y = DVector::from_iterator(
            indices.len(),
            indices.iter().map(|i| (f2[*i] + inc[*i]) * w(*i)),
        );
        let beta = numeric::lsq(&a, &y)?;
        residual = (&y - &a * &beta).norm_squared();
        params.n = beta[0] / scale;
        params.n_container = -beta[1] / cs;
        params.multiple = -beta[2];
    }
    params.residual = residual;
    let y = pattern
        .y
        .iter()
        .zip(inc)
        .zip(cont)
        .map(|((i, c), ct)| params.n * i - params.multiple - c - params.n_container * ct)
        .collect();
    Ok((params, Pattern::new(pattern.x.clone(), y)?))
}
/// Nonnegative fit corresponding to the deprecated lmfit normalization API.
/// Nonnegative normalization fit for compatibility with the deprecated Python
/// lmfit interface. Returns coefficients and the corrected intensity; no lmfit
/// runtime is used in Rust. Arguments follow [`normalize_fit`].
pub fn normalize_fit_constrained(
    pattern: &Pattern,
    f2: &[f64],
    inc: Option<&[f64]>,
    cutoff: f64,
    scaling: &str,
    multiple: bool,
    container: Option<&[f64]>,
) -> Result<(crate::request::NormalizationParameters, Pattern), String> {
    pattern.validate()?;
    arrays(&[&pattern.y, f2])?;
    if !["linear", "squared"].contains(&scaling) {
        return Err("Invalid normalization scaling".into());
    }
    let zero = vec![0.; pattern.x.len()];
    let inc = inc.unwrap_or(&zero);
    let cont = container.unwrap_or(&zero);
    arrays(&[&pattern.y, inc, cont])?;
    let indices: Vec<_> = pattern
        .x
        .iter()
        .enumerate()
        .filter(|(_, q)| **q > cutoff)
        .map(|(i, _)| i)
        .collect();
    if indices.is_empty() {
        return Err("No Q values above cutoff".into());
    }
    let scales = [
        indices
            .iter()
            .map(|i| pattern.y[*i].abs())
            .fold(0., f64::max),
        indices.iter().map(|i| cont[*i].abs()).fold(0., f64::max),
        1.,
    ];
    let scales = scales.map(|s| if s == 0. { 1. } else { s });
    let w = |i: usize| {
        if scaling == "squared" {
            pattern.x[i].powi(2)
        } else {
            pattern.x[i]
        }
    };
    let target = DVector::from_iterator(
        indices.len(),
        indices.iter().map(|i| (f2[*i] + inc[*i]) * w(*i)),
    );
    let mut best = target.norm_squared();
    let mut beta = [0.; 3];
    for mask in 1..8 {
        if (!multiple && mask & 4 != 0) || (container.is_none() && mask & 2 != 0) {
            continue;
        }
        let active: Vec<_> = (0..3).filter(|j| mask & (1 << j) != 0).collect();
        let a = DMatrix::from_fn(indices.len(), active.len(), |row, col| {
            let i = indices[row];
            w(i) * match active[col] {
                0 => pattern.y[i] / scales[0],
                1 => -cont[i] / scales[1],
                _ => -1.,
            }
        });
        let values = numeric::lsq(&a, &target)?;
        if values.iter().any(|v| *v < 0.) {
            continue;
        }
        let residual = (&target - &a * &values).norm_squared();
        if residual < best {
            best = residual;
            beta = [0.; 3];
            for (i, j) in active.iter().enumerate() {
                beta[*j] = values[i] / scales[*j];
            }
        }
    }
    let params = crate::request::NormalizationParameters {
        n: beta[0],
        n_container: beta[1],
        multiple: beta[2],
        residual: best,
    };
    let y = pattern
        .y
        .iter()
        .zip(inc)
        .zip(cont)
        .map(|((i, c), ct)| params.n * i - params.multiple - c - params.n_container * ct)
        .collect();
    Ok((params, Pattern::new(pattern.x.clone(), y)?))
}

/// Extend a low-Q pattern toward zero using `step`, `linear`, `poly` or `spline`.
/// `y0` is the target S(0); `xmax` is the **absolute end coordinate** of the fit
/// interval, unlike [`crate::request::Request::overlap`], which is a width.
/// `replace` replaces the overlap for spline/poly; `smoothing` is spline-only.
/// Preserves legacy polynomial boundary duplication and the nearest-zero grid.
pub fn extrapolate(
    pattern: &Pattern,
    method: &str,
    y0: f64,
    xmax: f64,
    replace: bool,
    smoothing: Option<f64>,
) -> Result<Pattern, String> {
    pattern.validate()?;
    grid(&pattern.x)?;
    let x = &pattern.x;
    let y = &pattern.y;
    let step = x[1] - x[0];
    let mut low = if method == "poly" {
        numeric::arange(x[0], 0., -step)?
    } else {
        numeric::arange(x[0] - step, -step / 2., -step)?
    };
    low.reverse();
    let overlap = x.partition_point(|x| *x < xmax);
    let mut remaining = 0;
    let values = match method {
        "step" => vec![y0; low.len()],
        "linear" => low.iter().map(|v| (y[0] - y0) / x[0] * v + y0).collect(),
        "spline" => {
            let mut xx = vec![0.];
            xx.extend_from_slice(&x[..overlap]);
            let mut yy = vec![y0];
            yy.extend_from_slice(&y[..overlap]);
            if replace {
                low.extend_from_slice(&x[..overlap]);
                remaining = x.partition_point(|v| *v <= xmax);
            }
            let mut values = numeric::spline_values(&xx, &yy, &low, smoothing)?;
            if let Some(last) = values.iter().rposition(|v| *v < y0) {
                values[..last].fill(y0);
            }
            values
        }
        "poly" => {
            let [a, b, c] = numeric::quadratic_extrapolation_fit(&x[..overlap], &y[..overlap], y0)?;
            if replace {
                if overlap > 1 {
                    low.extend_from_slice(&x[1..overlap]);
                }
                remaining = x.partition_point(|v| *v <= xmax);
            }
            low.iter()
                .map(|x| (a * (x - c) + b * (x - c).powi(2) - y0).max(y0))
                .collect()
        }
        _ => return Err("Unknown extrapolation method".into()),
    };
    let mut values: Vec<f64> = values;
    low.extend_from_slice(&x[remaining..]);
    values.extend_from_slice(&y[remaining..]);
    // Polynomial extrapolation preserves the historical duplicate boundary point.
    if low.windows(2).any(|w| w[1] < w[0]) || values.iter().any(|v| !v.is_finite()) {
        return Err("Invalid extrapolation".into());
    }
    Ok(Pattern { x: low, y: values })
}
/// Convert two-theta angles in degrees to Q (Å⁻¹), with wavelength in Å.
pub fn two_theta_to_q(values: &[f64], wavelength: f64) -> Result<Vec<f64>, String> {
    if wavelength <= 0. || !wavelength.is_finite() || values.iter().any(|v| !v.is_finite()) {
        return Err("Invalid angle/wavelength".into());
    }
    Ok(values
        .iter()
        .map(|v| 4. * PI / wavelength * (v * PI / 360.).sin())
        .collect())
}
pub(crate) const ELEMENTS:&str="H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og";
/// Atomic number for a known element symbol; unknown symbols are errors.
pub fn atomic_number(symbol: &str) -> Result<usize, String> {
    ELEMENTS
        .split_whitespace()
        .position(|s| s == symbol)
        .map(|i| i + 1)
        .ok_or_else(|| format!("Unknown element: {symbol}"))
}
/// Sum of atomic numbers times unnormalized formula amounts.
pub fn total_atomic_number(composition: &Composition) -> Result<f64, String> {
    composition
        .amounts()?
        .iter()
        .map(|(s, n)| Ok(atomic_number(s)? as f64 * n))
        .sum()
}
/// WKM effective form factor: composition-weighted amplitude divided by the
/// formula's total atomic number. Q is Å⁻¹.
pub fn effective_form_factor(
    composition: &Composition,
    q: &[f64],
    source: Source,
) -> Result<Vec<f64>, String> {
    let total = total_atomic_number(composition)?;
    let mut values = vec![0.; q.len()];
    for (element, c) in composition.amounts()? {
        for (v, f) in values
            .iter_mut()
            .zip(scattering::coherent_factor(&element, q, source)?)
        {
            *v += c * f / total;
        }
    }
    Ok(values)
}
/// Q-dependent X-ray pair weight using atomic fractions and coherent amplitudes.
/// Unlike-pair weights include both orderings; Q is Å⁻¹.
pub fn weighting_factor(
    composition: &Composition,
    e1: &str,
    e2: &str,
    q: &[f64],
    source: Source,
) -> Result<Vec<f64>, String> {
    let c = composition.fractions()?;
    let a = *c.get(e1).ok_or("Pair species missing")?;
    let b = *c.get(e2).ok_or("Pair species missing")?;
    let f1 = scattering::coherent_factor(e1, q, source)?;
    let f2 = scattering::coherent_factor(e2, q, source)?;
    let mut mean = vec![0.; q.len()];
    for (key, c) in c {
        for (m, f) in mean
            .iter_mut()
            .zip(scattering::coherent_factor(&key, q, source)?)
        {
            *m += c * f;
        }
    }
    Ok((0..q.len())
        .map(|i| if e1 == e2 { 1. } else { 2. } * a * b * f1[i] * f2[i] / mean[i].powi(2))
        .collect())
}
/// WKM effective atomic number for one element, averaged over supplied Q points.
pub fn wkm_effective_atomic_number(
    composition: &Composition,
    element: &str,
    q: &[f64],
    source: Source,
) -> Result<f64, String> {
    let effective = effective_form_factor(composition, q, source)?;
    let f = scattering::coherent_factor(element, q, source)?;
    Ok(f.iter().zip(effective).map(|(f, e)| f / e).sum::<f64>() / q.len() as f64)
}
/// Scalar WKM pair weight from Q-averaged effective atomic numbers.
pub fn weighting_factor_wkm(
    composition: &Composition,
    e1: &str,
    e2: &str,
    q: &[f64],
    source: Source,
) -> Result<f64, String> {
    let c = composition.amounts()?;
    let k1 = wkm_effective_atomic_number(composition, e1, q, source)?;
    let k2 = wkm_effective_atomic_number(composition, e2, q, source)?;
    let mut total = 0.;
    for (element, c) in &c {
        total += c * wkm_effective_atomic_number(composition, element, q, source)?;
    }
    let a = *c.get(e1).ok_or("Pair species missing")?;
    let b = *c.get(e2).ok_or("Pair species missing")?;
    Ok(if e1 == e2 { 1. } else { 2. } * a * b * k1 * k2 / (total * total))
}
#[derive(Clone, Deserialize, Serialize)]
/// Gaussian-broadened pair contribution to scattering/real-space peak models.
pub struct Peak {
    /// Coordination number, nonnegative.
    pub coordination: f64,
    /// Positive mean pair distance, Å.
    pub position: f64,
    /// Positive Gaussian standard deviation, Å (not FWHM).
    pub sigma: f64,
    /// Relative atomic composition for scattering weights.
    pub composition: Composition,
    /// Central species.
    pub element_1: String,
    /// Neighbor species; its atomic fraction normalizes the coordination.
    pub element_2: String,
}
impl Peak {
    fn fraction(&self) -> Result<f64, String> {
        if !self.coordination.is_finite()
            || self.coordination < 0.
            || self.position <= 0.
            || !self.position.is_finite()
            || self.sigma <= 0.
            || !self.sigma.is_finite()
        {
            return Err("Invalid peak parameters".into());
        }
        self.composition
            .fractions()?
            .get(&self.element_2)
            .copied()
            .ok_or("Peak neighbour missing".into())
    }
    /// Pair contribution to S(Q)-1 with Gaussian broadening; Q is Å⁻¹.
    pub fn i_q(&self, q: &[f64], source: Source) -> Result<Vec<f64>, String> {
        let c = self.fraction()?;
        let w = weighting_factor(
            &self.composition,
            &self.element_1,
            &self.element_2,
            q,
            source,
        )?;
        Ok(q.iter()
            .zip(w)
            .map(|(q, w)| {
                let x = q * self.position;
                self.coordination * w / c
                    * if x == 0. { 1. } else { x.sin() / x }
                    * (-q * q * self.sigma * self.sigma / 2.).exp()
            })
            .collect())
    }
    /// Transform the pair contribution using the supplied Q grid and r in Å.
    /// Uses the same forward-transform convention as [`calculate_fr`].
    pub fn t_r(
        &self,
        r: &[f64],
        q: &[f64],
        method: Method,
        lorch: bool,
        source: Source,
    ) -> Result<Vec<f64>, String> {
        let sq = Pattern::new(
            q.to_vec(),
            self.i_q(q, source)?.iter().map(|v| 1. + v).collect(),
        )?;
        Ok(calculate_fr(&sq, r, method, lorch)?.y)
    }
    /// WKM-weighted Gaussian real-space pair model. r must be positive (Å);
    /// Q (Å⁻¹) supplies the averaged scattering weight.
    pub fn gaussian(&self, r: &[f64], q: &[f64], source: Source) -> Result<Vec<f64>, String> {
        let c = self.fraction()?;
        let w = weighting_factor_wkm(
            &self.composition,
            &self.element_1,
            &self.element_2,
            q,
            source,
        )?;
        if r.iter().any(|r| !r.is_finite() || *r <= 0.) {
            return Err("Gaussian T(r) requires positive r".into());
        }
        Ok(r.iter()
            .map(|r| {
                self.coordination * w / (c * self.sigma * r * (2. * PI).sqrt())
                    * (-(r - self.position).powi(2) / (2. * self.sigma.powi(2))).exp()
            })
            .collect())
    }
}
#[derive(Clone, Deserialize, Serialize)]
/// Normalized cubic smoothing-spline transfer function; supports evaluation,
/// rather than the entire SciPy `UnivariateSpline` interface.
pub struct TransferFunction {
    /// B-spline knot vector.
    pub knots: Vec<f64>,
    /// Cubic B-spline coefficients.
    pub coefficients: Vec<f64>,
}
impl TransferFunction {
    /// Fit standard/sample intensity ratio, normalized by its minimum.
    /// Patterns must be aligned by index with equal lengths and at least four
    /// samples. `smoothing` must be nonnegative; zero requests interpolation.
    pub fn fit(standard: &Pattern, sample: &Pattern, smoothing: f64) -> Result<Self, String> {
        standard.validate()?;
        sample.validate()?;
        arrays(&[&standard.y, &sample.y])?;
        let mut y: Vec<_> = standard
            .y
            .iter()
            .zip(&sample.y)
            .map(|(a, b)| a / b)
            .collect();
        let min = y.iter().copied().fold(f64::INFINITY, f64::min);
        if !smoothing.is_finite()
            || smoothing < 0.
            || y.iter().any(|y| !y.is_finite())
            || min == 0.
            || y.len() < 4
        {
            return Err("Invalid transfer function/smoothing".into());
        }
        for v in &mut y {
            *v /= min;
        }
        let spline = splinefit::CubicSplineFit::new(standard.x.clone(), y)
            .smoothing_spline((smoothing / standard.x.len() as f64).sqrt())
            .map_err(|e| e.to_string())?;
        Ok(Self {
            knots: spline.t,
            coefficients: spline.c,
        })
    }
    /// Evaluate the spline; outside its domain, extrapolate the end polynomial.
    pub fn evaluate(&self, x: &[f64]) -> Result<Vec<f64>, String> {
        if self.coefficients.len() < 4
            || self.knots.len() != self.coefficients.len() + 4
            || x.iter().any(|x| !x.is_finite())
        {
            return Err("Invalid cubic spline".into());
        }
        Ok(x.iter()
            .map(|v| {
                let k = self
                    .knots
                    .partition_point(|t| t <= v)
                    .saturating_sub(1)
                    .clamp(3, self.coefficients.len() - 1);
                let mut d = [0.; 4];
                d.copy_from_slice(&self.coefficients[k - 3..=k]);
                for r in 1..=3 {
                    for j in (r..=3).rev() {
                        let i = k - 3 + j;
                        let a = (v - self.knots[i]) / (self.knots[i + 4 - r] - self.knots[i]);
                        d[j] = (1. - a) * d[j - 1] + a * d[j];
                    }
                }
                d[3]
            })
            .collect())
    }
}
