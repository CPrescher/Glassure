//! Complete PDF calculation from raw intensity, optional background and composition.
//!
//! Start with [`Request::new`], adjust its fields, then call [`calculate`].
//! Mass density is g/cm³; Q is Å⁻¹ and r is Å. Numeric arrays remain ordinary
//! owned Rust values. Serde and byte-ABI functions provide optional interchange.
use crate::{
    corrections::{klein_nishina, soller_dac},
    numeric::{arange, lsq, quadratic_extrapolation_fit, spline_values},
    sq_optimization::{optimize, SqOptimization},
};
use crate::{evaluate, scattering::Composition, transform, Input, Method};
use nalgebra::{DMatrix, DVector};
use serde::{Deserialize, Serialize};
use std::cell::RefCell;

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
/// Owned coordinates/intensities. Also re-exported as [`crate::pattern::Pattern`].
/// General pattern validation permits repeated x values; full PDF inputs require
/// at least two strictly increasing nonnegative Q coordinates.
pub struct Pattern {
    /// Coordinates (Q or r, depending on the operation).
    pub x: Vec<f64>,
    /// Values corresponding one-to-one with `x`.
    pub y: Vec<f64>,
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(tag = "method", rename_all = "lowercase", deny_unknown_fields)]
/// Intensity normalization. JSON selects variants with `"method"`.
pub enum Normalization {
    /// Integral normalization; the full pipeline follows Python and does not
    /// apply Klein–Nishina correction in this branch.
    Integral {
        /// Nonnegative damping coefficient in exp(-attenuation * Q²).
        attenuation: f64,
    },
    /// High-Q weighted linear least-squares fit.
    Fit {
        /// Fit only Q values strictly above this cutoff (Å⁻¹).
        q_cutoff: f64,
        #[serde(default = "squared")]
        /// `"squared"` multiplies residuals by Q²; `"linear"` uses Q.
        scaling: String,
        #[serde(default)]
        /// Include a constant multiple-scattering term.
        multiple: bool,
        #[serde(default)]
        /// Optional container composition for fitted incoherent scattering.
        container: Option<Composition>,
        #[serde(default)]
        /// Optional Soller/DAC correction, used with a container and wavelength.
        dac: Option<Dac>,
    },
}
fn squared() -> String {
    "squared".into()
}
fn overlap() -> f64 {
    0.2
}
#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
/// Diamond-anvil-cell thicknesses in **µm**, unlike general Soller geometry in mm.
pub struct Dac {
    /// Chamber thickness when background was measured.
    pub initial_thickness: f64,
    /// Current sample thickness (less than initial thickness).
    pub sample_thickness: f64,
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
/// Complete PDF settings and owned input patterns.
///
/// Prefer [`Request::new`] over a struct literal for defaults. Serde does **not**
/// fill every field from that constructor: JSON must supply the required fields,
/// while optional fields may be omitted. `glassure init` creates a complete template.
pub struct Request {
    /// Measured intensity versus Q (Å⁻¹), before background subtraction.
    pub data: Pattern,
    /// Background intensity versus Q; `None` disables subtraction.
    pub background: Option<Pattern>,
    /// Subtract `background_scale * background` from the measured intensity.
    pub background_scale: f64,
    /// Formula or relative atomic amounts; not weight fractions.
    pub composition: Composition,
    #[serde(default)]
    /// Embedded scattering dataset; Brown–Hubbell by default.
    pub scattering_factor_source: crate::scattering::Source,
    /// Mass density in g/cm³ (not atoms/Å³).
    pub density: f64,
    /// Lower strict Q crop bound, Å⁻¹.
    pub q_min: f64,
    /// Upper strict Q crop bound, Å⁻¹.
    pub q_max: f64,
    /// Start of output real-space grid, Å; zero is treated by the legacy convention.
    pub r_min: f64,
    /// Upper target of the real-space grid, Å; rounding to r_step may shift it
    /// by up to half a step.
    pub r_max: f64,
    /// Positive real-space grid spacing, Å.
    pub r_step: f64,
    /// Integral or high-Q fit normalization.
    pub normalization: Normalization,
    /// Subtract the sample's incoherent scattering contribution.
    pub incoherent: bool,
    /// Apply Lorch modification during the final transform.
    pub lorch: bool,
    /// `"fft"` or `"integral"`.
    pub transform: String,
    /// Low-Q extension: `"step"`, `"linear"`, `"poly"` or `"spline"`.
    pub extrapolation: String,
    #[serde(default)]
    /// Apply Klein–Nishina scaling in the fit-normalization branch.
    pub kn_correction: bool,
    #[serde(default)]
    /// Wavelength in Å, required for Klein–Nishina and DAC corrections.
    pub wavelength: Option<f64>,
    #[serde(default = "overlap")]
    /// Width of the low-Q extrapolation fitting interval above q_min, Å⁻¹.
    pub overlap: f64,
    #[serde(default)]
    /// Replace the measured overlap interval for spline/polynomial extrapolation.
    pub replace: bool,
    #[serde(default)]
    /// S(0) override; `None` uses `1 - <f(0)²>/<f(0)>²`.
    pub s0: Option<f64>,
    #[serde(default)]
    /// Optional smoothing parameter for spline extrapolation.
    pub smooth_factor: Option<f64>,
    #[serde(default)]
    /// Optional iterative or polynomial S(Q) correction before the final transform.
    pub optimize: Option<SqOptimization>,
}

#[derive(Serialize)]
/// PDF curves and normalization metadata from a successful calculation.
pub struct Response {
    /// Dimensionless structure factor versus Q (Å⁻¹).
    pub sq: Pattern,
    /// F(r) in Å⁻² versus r (Å).
    pub fr: Pattern,
    /// Dimensionless g(r) versus r (Å).
    pub gr: Pattern,
    /// Intensity normalization multiplier; identical to `normalization_parameters.n`.
    pub normalization: f64,
    /// Atomic number density in atoms/Å³.
    pub atomic_density: f64,
    /// Normalization coefficients and high-Q residual diagnostic.
    pub normalization_parameters: NormalizationParameters,
}

#[derive(Clone, Copy, Default, Serialize)]
/// Coefficients for `n * intensity - multiple - incoherent - n_container * container`.
/// Residual diagnostics are populated by fit normalization with extra terms;
/// zero values are not universal goodness-of-fit measures.
pub struct NormalizationParameters {
    /// Intensity multiplier.
    pub n: f64,
    /// Constant multiple-scattering contribution to subtract.
    pub multiple: f64,
    /// Container-scattering coefficient to subtract.
    pub n_container: f64,
    /// Sum of squared weighted residuals where computed; otherwise zero.
    pub residual: f64,
}

impl Request {
    /// Validate data/composition and construct default PDF settings.
    ///
    /// Q bounds default to the data endpoints (subsequently cropped strictly).
    /// Other defaults: density in g/cm³, Brown–Hubbell factors, fit normalization
    /// above 3 Å⁻¹, step extrapolation, FFT and r = 0–10 Å with 0.01 Å spacing.
    /// No S(Q) optimization, Lorch, Klein–Nishina or DAC correction is enabled.
    pub fn new(data: Pattern, composition: Composition, density: f64) -> Result<Self, String> {
        validate_pattern(&data)?;
        crate::scattering::atomic_density(&composition, density)?;
        let q_min = data.x[0];
        let q_max = data.x[data.x.len() - 1];
        Ok(Self {
            data,
            background: None,
            background_scale: 1.,
            composition,
            density,
            scattering_factor_source: crate::scattering::Source::BrownHubbell,
            q_min,
            q_max,
            r_min: 0.,
            r_max: 10.,
            r_step: 0.01,
            normalization: Normalization::Fit {
                q_cutoff: 3.,
                scaling: "squared".into(),
                multiple: false,
                container: None,
                dac: None,
            },
            incoherent: true,
            lorch: false,
            transform: "fft".into(),
            extrapolation: "step".into(),
            kn_correction: false,
            wavelength: None,
            overlap: 0.2,
            replace: false,
            s0: None,
            smooth_factor: None,
            optimize: None,
        })
    }
}

pub(crate) fn validate_pattern(pattern: &Pattern) -> Result<(), String> {
    if pattern.x.len() != pattern.y.len()
        || !(2..=1_000_000).contains(&pattern.x.len())
        || pattern.x.iter().chain(&pattern.y).any(|v| !v.is_finite())
        || pattern.x.iter().any(|v| *v < 0.0)
        || pattern.x.windows(2).any(|w| w[1] <= w[0])
    {
        return Err("Invalid pattern".into());
    }
    Ok(())
}

pub(crate) fn interpolate(pattern: &Pattern, x: f64) -> f64 {
    let k = pattern
        .x
        .partition_point(|v| *v <= x)
        .saturating_sub(1)
        .min(pattern.x.len() - 2);
    pattern.y[k]
        + (pattern.y[k + 1] - pattern.y[k]) / (pattern.x[k + 1] - pattern.x[k]) * (x - pattern.x[k])
}

/// Run background subtraction, normalization, extrapolation, optional S(Q)
/// optimization and the final F(r)/g(r) transform.
///
/// Consumes its request and returns owned curves. Cropping is strict on both Q
/// bounds. Equal-length backgrounds use indexed subtraction, matching Python;
/// different-length backgrounds are interpolated over the common domain.
/// Unsupported options, insufficient data, invalid grids and numerical failures
/// return an error; no alternate backend or algorithm is tried.
pub fn calculate(req: Request) -> Result<Response, String> {
    validate_pattern(&req.data)?;
    if ![
        req.background_scale,
        req.q_min,
        req.q_max,
        req.r_min,
        req.r_max,
        req.r_step,
    ]
    .iter()
    .all(|v| v.is_finite())
        || req.q_min < 0.0
        || req.q_max <= req.q_min
        || req.r_min < 0.0
        || req.r_max <= req.r_min
        || req.r_step <= 0.0
    {
        return Err("Invalid calculation ranges".into());
    }
    let method = match req.transform.as_str() {
        "fft" => Method::Fft,
        "integral" => Method::Integral,
        _ => return Err("Unsupported transform".into()),
    };
    if !matches!(
        req.extrapolation.as_str(),
        "linear" | "step" | "spline" | "poly"
    ) {
        return Err("Unsupported extrapolation".into());
    }
    if let Some(bkg) = &req.background {
        validate_pattern(bkg)?;
    }
    let mut q = Vec::new();
    let mut intensity = Vec::new();
    for (i, (&x, &y)) in req.data.x.iter().zip(&req.data.y).enumerate() {
        // Match Pattern.limit's strict cropping and Pattern arithmetic's existing
        // same-length/indexed versus different-length/interpolated behavior.
        if x <= req.q_min || x >= req.q_max {
            continue;
        }
        let bkg = match &req.background {
            None => 0.0,
            Some(b) if b.x.len() == req.data.x.len() => b.y[i],
            Some(b) if x >= b.x[0] && x <= b.x[b.x.len() - 1] => interpolate(b, x),
            Some(_) => continue,
        };
        q.push(x);
        intensity.push(y - req.background_scale * bkg);
    }
    if q.len() < 2 {
        return Err("Too few points after cropping/background overlap".into());
    }
    let factors = crate::scattering::factors_with_source(
        &req.composition,
        req.density,
        &q,
        req.scattering_factor_source,
    )?;
    let correction = if req.kn_correction {
        klein_nishina(&q, req.wavelength.ok_or("Wavelength required")?)?
    } else {
        vec![1.0; q.len()]
    };
    let mut incoherent = if req.incoherent {
        factors.incoherent.clone()
    } else {
        vec![0.0; q.len()]
    };
    let mut parameters = NormalizationParameters::default();
    let (normalization, sq) = match &req.normalization {
        Normalization::Integral { attenuation } => {
            // Current Python integral normalization intentionally does not apply KN.
            let input = Input {
                q: &q,
                intensity: &intensity,
                f_squared_mean: &factors.f2,
                f_mean_squared: &factors.fm2,
                incoherent: &incoherent,
                r: &[0.0],
                density: factors.atomic_density,
                attenuation: *attenuation,
            };
            let result = evaluate(&input, Method::Integral, false)
                .map_err(|e| format!("Normalization: {e:?}"))?;
            parameters.n = result.normalization;
            (result.normalization, result.sq)
        }
        Normalization::Fit {
            q_cutoff,
            scaling,
            multiple,
            container,
            dac,
        } => {
            if !q_cutoff.is_finite() || !matches!(scaling.as_str(), "squared" | "linear") {
                return Err("Invalid fit settings".into());
            }
            for (i, v) in incoherent.iter_mut().enumerate() {
                *v *= correction[i];
            }
            let mut cont = match container {
                None => vec![0.0; q.len()],
                Some(c) => factors_for_container(c, &q, &correction, req.scattering_factor_source)?,
            };
            if let (Some(dac), Some(_)) = (dac, container) {
                let (sample_tf, diamond_tf) = soller_dac(
                    &q,
                    req.wavelength.ok_or("Wavelength required for DAC")?,
                    dac.initial_thickness,
                    dac.sample_thickness,
                )?;
                for i in 0..q.len() {
                    intensity[i] *= sample_tf[i];
                    cont[i] /= diamond_tf[i];
                }
            }
            let fit: Vec<_> = q
                .iter()
                .enumerate()
                .filter(|(_, v)| **v > *q_cutoff)
                .map(|(i, _)| i)
                .collect();
            if fit.is_empty() {
                return Err("No points above fit cutoff".into());
            }
            let weight = |i: usize| {
                if scaling == "squared" {
                    q[i] * q[i]
                } else {
                    q[i]
                }
            };
            let n = if !multiple && container.is_none() {
                let (mut num, mut den) = (0.0, 0.0);
                for &i in &fit {
                    let y = intensity[i] * weight(i);
                    let f = (factors.f2[i] + incoherent[i]) * weight(i);
                    num += y * f;
                    den += y * y;
                }
                if den == 0.0 {
                    return Err("Singular fit normalization".into());
                }
                num / den
            } else {
                let scale = fit.iter().map(|i| intensity[*i].abs()).fold(0.0, f64::max);
                let cscale = fit.iter().map(|i| cont[*i].abs()).fold(0.0, f64::max);
                let scale = if scale == 0.0 { 1.0 } else { scale };
                let cscale = if cscale == 0.0 { 1.0 } else { cscale };
                let a = DMatrix::from_fn(fit.len(), 3, |j, k| {
                    let i = fit[j];
                    weight(i)
                        * match k {
                            0 => intensity[i] / scale,
                            1 => cont[i] / cscale,
                            _ => {
                                if *multiple {
                                    1.0
                                } else {
                                    0.0
                                }
                            }
                        }
                });
                let y = DVector::from_iterator(
                    fit.len(),
                    fit.iter()
                        .map(|i| (factors.f2[*i] + incoherent[*i]) * weight(*i)),
                );
                let beta = lsq(&a, &y)?;
                parameters.multiple = -beta[2];
                parameters.n_container = -beta[1] / cscale;
                parameters.residual = (&y - &a * &beta).norm_squared();
                beta[0] / scale
            };
            parameters.n = n;
            let sq = (0..q.len())
                .map(|i| {
                    (n * intensity[i]
                        - parameters.multiple
                        - incoherent[i]
                        - cont[i] * parameters.n_container
                        - factors.f2[i]
                        + factors.fm2[i])
                        / factors.fm2[i]
                })
                .collect();
            (n, sq)
        }
    };
    let (x, mut y) = extrapolate(&q, &sq, req.s0.unwrap_or(factors.s0), &req)?;
    let r = arange(req.r_min, req.r_max + 0.5 * req.r_step, req.r_step)?;
    if r.len() < 2 {
        return Err("Need at least two r points".into());
    }
    if let Some(opt) = &req.optimize {
        y = optimize(&x, &y, factors.atomic_density, req.r_step, method, opt)?;
    }
    let (fr, gr) = transform(&x, &y, &r, factors.atomic_density, method, req.lorch)
        .map_err(|e| format!("Transform: {e:?}"))?;
    if !normalization.is_finite() || y.iter().any(|v| !v.is_finite()) {
        return Err("Nonfinite normalization".into());
    }
    Ok(Response {
        sq: Pattern { x, y },
        fr: Pattern {
            x: r.clone(),
            y: fr,
        },
        gr: Pattern { x: r, y: gr },
        normalization,
        normalization_parameters: parameters,
        atomic_density: factors.atomic_density,
    })
}

fn factors_for_container(
    c: &Composition,
    q: &[f64],
    correction: &[f64],
    source: crate::scattering::Source,
) -> Result<Vec<f64>, String> {
    Ok(crate::scattering::factors_with_source(c, 1.0, q, source)?
        .incoherent
        .iter()
        .zip(correction)
        .map(|(v, c)| v * c)
        .collect())
}

fn extrapolate(
    q: &[f64],
    sq: &[f64],
    s0: f64,
    req: &Request,
) -> Result<(Vec<f64>, Vec<f64>), String> {
    if !s0.is_finite() || !req.overlap.is_finite() || req.overlap <= 0.0 {
        return Err("Invalid extrapolation settings".into());
    }
    let step = if req.extrapolation == "step" {
        (q[q.len() - 1] - q[0]) / (q.len() - 1) as f64
    } else {
        q[1] - q[0]
    };
    let mut x = if req.extrapolation == "poly" {
        arange(q[0], 0.0, -step)?
    } else {
        arange(q[0] - step, -step / 2.0, -step)?
    };
    x.reverse();
    let cutoff = q[0] + req.overlap;
    let fit_count = q.partition_point(|v| *v < cutoff);
    let mut remain = 0;
    let y = match req.extrapolation.as_str() {
        "linear" => x.iter().map(|v| (sq[0] - s0) / q[0] * v + s0).collect(),
        "step" => vec![s0; x.len()],
        "spline" => {
            let mut fx = vec![0.0];
            fx.extend_from_slice(&q[..fit_count]);
            let mut fy = vec![s0];
            fy.extend_from_slice(&sq[..fit_count]);
            if req.replace {
                x.extend_from_slice(&q[..fit_count]);
                remain = q.partition_point(|v| *v <= cutoff);
            }
            let mut y = spline_values(&fx, &fy, &x, req.smooth_factor)?;
            if let Some(last) = y.iter().rposition(|v| *v < s0) {
                y[..last].fill(s0);
            }
            y
        }
        "poly" => {
            let [a, b, c] = quadratic_extrapolation_fit(&q[..fit_count], &sq[..fit_count], s0)?;
            if req.replace {
                x.extend_from_slice(&q[1..fit_count]);
                remain = q.partition_point(|v| *v <= cutoff);
            }
            x.iter()
                .map(|v| (a * (v - c) + b * (v - c).powi(2) - s0).max(s0))
                .collect()
        }
        _ => return Err("Unknown extrapolation".into()),
    };
    let mut y: Vec<f64> = y;
    x.extend_from_slice(&q[remain..]);
    y.extend_from_slice(&sq[remain..]);
    Ok((x, y))
}

thread_local! { static RESPONSE: RefCell<Vec<u8>> = const { RefCell::new(Vec::new()) }; }

/// Retain panic diagnostics across a WASM trap for the browser adapter.
#[no_mangle]
pub extern "C" fn initialize_diagnostics() {
    std::panic::set_hook(Box::new(|info| {
        let message = serde_json::to_vec(&serde_json::json!({"error":info.to_string()})).unwrap();
        RESPONSE.with(|r| *r.borrow_mut() = message);
    }));
}

#[no_mangle]
pub extern "C" fn bytes_alloc(len: usize) -> *mut u8 {
    Box::into_raw(vec![0_u8; len].into_boxed_slice()) as *mut u8
}
/// # Safety
/// Pointer/length must identify a live allocation from bytes_alloc.
#[no_mangle]
pub unsafe extern "C" fn bytes_free(ptr: *mut u8, len: usize) {
    if !ptr.is_null() {
        drop(Box::from_raw(std::ptr::slice_from_raw_parts_mut(ptr, len)));
    }
}

/// # Safety
/// Input must be readable for len bytes; no overlapping writes may occur. Output
/// remains available through response_ptr/response_len until the next request.
#[no_mangle]
pub unsafe extern "C" fn calculate_json(ptr: *const u8, len: usize) -> u32 {
    json_call(ptr, len, 0)
}
/// # Safety
/// Same input/output lifetime requirements as calculate_json.
#[no_mangle]
pub unsafe extern "C" fn factors_json(ptr: *const u8, len: usize) -> u32 {
    json_call(ptr, len, 1)
}

/// # Safety
/// Same byte-buffer lifetime requirements as calculate_json.
#[no_mangle]
pub unsafe extern "C" fn density_json(ptr: *const u8, len: usize) -> u32 {
    json_call(ptr, len, 2)
}

/// # Safety
/// Same byte-buffer lifetime requirements as calculate_json.
#[no_mangle]
pub unsafe extern "C" fn batch_json(ptr: *const u8, len: usize) -> u32 {
    json_call(ptr, len, 3)
}

/// # Safety
/// Same byte-buffer lifetime requirements as calculate_json.
#[no_mangle]
pub unsafe extern "C" fn sweep_json(ptr: *const u8, len: usize) -> u32 {
    json_call(ptr, len, 4)
}

unsafe fn json_call(ptr: *const u8, len: usize, operation: u32) -> u32 {
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct FactorRequest {
        composition: Composition,
        density: f64,
        q: Vec<f64>,
        #[serde(default)]
        source: crate::scattering::Source,
    }
    let result: Result<Vec<u8>, String> = (|| {
        if ptr.is_null() || len == 0 || len > 64_000_000 {
            return Err("Invalid request size".into());
        }
        let bytes = std::slice::from_raw_parts(ptr, len);
        if operation == 4 {
            let req = serde_json::from_slice(bytes).map_err(|e| e.to_string())?;
            serde_json::to_vec(&crate::parallel::parameter_sweep(req)?).map_err(|e| e.to_string())
        } else if operation == 3 {
            let req = serde_json::from_slice(bytes).map_err(|e| e.to_string())?;
            serde_json::to_vec(&crate::parallel::calculate_batch(req)?).map_err(|e| e.to_string())
        } else if operation == 2 {
            let req: crate::density::DensityRequest =
                serde_json::from_slice(bytes).map_err(|e| e.to_string())?;
            serde_json::to_vec(&crate::density::optimize_density(req)?).map_err(|e| e.to_string())
        } else if operation == 1 {
            let req: FactorRequest = serde_json::from_slice(bytes).map_err(|e| e.to_string())?;
            serde_json::to_vec(&crate::scattering::factors_with_source(
                &req.composition,
                req.density,
                &req.q,
                req.source,
            )?)
            .map_err(|e| e.to_string())
        } else {
            let req: Request = serde_json::from_slice(bytes).map_err(|e| e.to_string())?;
            serde_json::to_vec(&calculate(req)?).map_err(|e| e.to_string())
        }
    })();
    let (status, bytes) = match result {
        Ok(bytes) => (0, bytes),
        Err(error) => (
            1,
            serde_json::to_vec(&serde_json::json!({"error":error})).unwrap(),
        ),
    };
    RESPONSE.with(|output| *output.borrow_mut() = bytes);
    status
}
#[no_mangle]
pub extern "C" fn response_ptr() -> *const u8 {
    RESPONSE.with(|r| r.borrow().as_ptr())
}
#[no_mangle]
pub extern "C" fn response_len() -> usize {
    RESPONSE.with(|r| r.borrow().len())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn invalid_json_clears_previous_response() {
        let input = b"{}";
        assert_eq!(unsafe { calculate_json(input.as_ptr(), input.len()) }, 1);
        assert!(response_len() > 0);
        let output = unsafe { std::slice::from_raw_parts(response_ptr(), response_len()) };
        assert!(serde_json::from_slice::<serde_json::Value>(output)
            .unwrap()
            .get("error")
            .is_some());
    }

    #[test]
    fn byte_abi_allocation_and_free_roundtrip() {
        for _ in 0..10 {
            let input = b"{}";
            let ptr = bytes_alloc(input.len());
            unsafe {
                std::ptr::copy_nonoverlapping(input.as_ptr(), ptr, input.len());
                assert_eq!(calculate_json(ptr, input.len()), 1);
                bytes_free(ptr, input.len());
            }
        }
    }
}
