//! Klein–Nishina and Soller/DAC corrections following Glassure's Python equations.
//! General Soller lengths/distances are mm, angles in degrees and Q in Å⁻¹.
//! The high-level [`soller_dac`] helper instead accepts chamber thicknesses in µm.
use crate::numeric::arange;
use serde::{Deserialize, Serialize};
use std::f64::consts::PI;

#[derive(Clone, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields)]
/// Soller slit dimensions in **mm**. Default values reproduce Glassure's geometry.
pub struct SollerGeometry {
    /// Inner slit radius (default 62 mm).
    pub inner_radius: f64,
    /// Outer slit radius (default 210 mm).
    pub outer_radius: f64,
    /// Inner slit width (default 0.05 mm).
    pub inner_width: f64,
    /// Outer slit width (default 0.2 mm).
    pub outer_width: f64,
    /// Inner slit length (default 8 mm).
    pub inner_length: f64,
    /// Outer slit length (default 6 mm).
    pub outer_length: f64,
}
impl Default for SollerGeometry {
    fn default() -> Self {
        Self {
            inner_radius: 62.,
            outer_radius: 210.,
            inner_width: 0.05,
            outer_width: 0.2,
            inner_length: 8.,
            outer_length: 6.,
        }
    }
}
#[derive(Clone, Deserialize, Serialize)]
/// Discrete acceptance-angle map on a two-theta/distance grid.
pub struct SollerMap {
    /// Two-theta columns, in degrees.
    pub two_theta: Vec<f64>,
    /// Sample-distance rows, in mm, spaced by 0.001 mm.
    pub distance: Vec<f64>,
    /// Flattened radians, indexed `row * two_theta.len() + column`.
    pub angles: Vec<f64>,
}
impl SollerMap {
    /// Build a map for two-theta angles in (0, 180) degrees and total thickness
    /// in mm. Positive geometry is required; maps above 20 million cells fail.
    pub fn new(
        two_theta: &[f64],
        max_thickness: f64,
        geometry: &SollerGeometry,
    ) -> Result<Self, String> {
        let g = geometry;
        if two_theta.is_empty()
            || two_theta
                .iter()
                .any(|v| !v.is_finite() || *v <= 0. || *v >= 180.)
            || !max_thickness.is_finite()
            || max_thickness <= 0.
            || [
                g.inner_radius,
                g.outer_radius,
                g.inner_width,
                g.outer_width,
                g.inner_length,
                g.outer_length,
            ]
            .iter()
            .any(|v| !v.is_finite() || *v <= 0.)
            || g.inner_radius + g.inner_length >= g.outer_radius
        {
            return Err("Invalid Soller geometry".into());
        }
        let distance = arange(-max_thickness / 2., max_thickness / 2., 0.001)?;
        let count = two_theta
            .len()
            .checked_mul(distance.len())
            .ok_or("Soller map allocation overflow")?;
        if count > 20_000_000 {
            return Err("Soller map allocation limit".into());
        }
        let mut angles = vec![0.; count];
        for (i, deg) in two_theta.iter().enumerate() {
            let theta = deg / 180. * PI;
            let (a, b) = points(g.inner_radius + g.inner_length, theta, g.inner_width);
            let (c, d) = points(g.outer_radius + g.outer_length, theta, g.outer_width);
            let (e, f) = points(g.inner_radius, theta, g.inner_width);
            let xfa = intercept(f, a);
            let xfc = intercept(f, c);
            let xbd = intercept(b, d);
            let xed = intercept(e, d);
            let xac = intercept(a, c);
            let pos = if xbd < 0. { 0. } else { xbd };
            let neg = if xac > 0. { 0. } else { xac };
            for (j, x) in distance.iter().enumerate() {
                let mut phi = angle(a, b, *x)
                    .min(angle(c, d, *x))
                    .min(angle(c, b, *x))
                    .min(angle(a, d, *x));
                if *x > pos && *x < xfa {
                    phi = angle(f, c, *x).min(angle(d, c, *x));
                }
                if *x > xfa || *x > xfc {
                    phi = 0.;
                }
                if *x < neg && *x > xed {
                    phi = angle(e, d, *x).min(angle(c, d, *x));
                }
                if *x < xed {
                    phi = 0.;
                }
                if !phi.is_finite() {
                    return Err("Nonfinite Soller acceptance".into());
                }
                angles[j * two_theta.len() + i] = phi;
            }
        }
        Ok(Self {
            two_theta: two_theta.to_vec(),
            distance,
            angles,
        })
    }
    /// Build from Q in Å⁻¹ and wavelength in Å; thickness/geometry are mm.
    pub fn from_q(
        q: &[f64],
        wavelength: f64,
        max_thickness: f64,
        geometry: &SollerGeometry,
    ) -> Result<Self, String> {
        if !wavelength.is_finite()
            || wavelength <= 0.
            || q.iter()
                .any(|v| !v.is_finite() || *v * wavelength / (4. * PI) > 1.)
        {
            return Err("Invalid Q/wavelength".into());
        }
        let angles: Vec<_> = q
            .iter()
            .map(|q| (q * wavelength / (4. * PI)).asin() * 360. / PI)
            .collect();
        Self::new(&angles, max_thickness, geometry)
    }
    /// Inverse acceptance summed over `lower < distance < upper` (mm), then
    /// normalized by its minimum. Empty/zero-acceptance regions return errors.
    pub fn region(&self, lower: f64, upper: f64) -> Result<Vec<f64>, String> {
        if !lower.is_finite()
            || !upper.is_finite()
            || lower >= upper
            || self.angles.len() != self.distance.len() * self.two_theta.len()
        {
            return Err("Invalid Soller region/map".into());
        }
        let mut values = vec![0.; self.two_theta.len()];
        for (j, x) in self.distance.iter().enumerate() {
            if *x > lower && *x < upper {
                for (i, v) in values.iter_mut().enumerate() {
                    *v += self.angles[j * self.two_theta.len() + i];
                }
            }
        }
        if values.is_empty() || values.iter().any(|v| !v.is_finite() || *v <= 0.) {
            return Err("Empty/zero-acceptance Soller region".into());
        }
        for v in &mut values {
            *v = 1. / *v;
        }
        let min = values.iter().copied().fold(f64::INFINITY, f64::min);
        for v in &mut values {
            *v /= min;
        }
        Ok(values)
    }
    /// Region correction for thickness and center shift in mm.
    pub fn sample(&self, thickness: f64, shift: f64) -> Result<Vec<f64>, String> {
        self.region(-thickness / 2. + shift, thickness / 2. + shift)
    }
    /// Return (sample correction, diamond-region correction); thicknesses in mm.
    pub fn dac(&self, sample: f64, initial: f64) -> Result<(Vec<f64>, Vec<f64>), String> {
        let a = self.sample(sample, 0.)?;
        let b = self.region(sample / 2., initial / 2.)?;
        let c = self.region(-initial / 2., -sample / 2.)?;
        Ok((a, b.iter().zip(c).map(|(a, b)| (a + b) / 2.).collect()))
    }
}

/// Klein–Nishina incoherent-scattering multiplier for Q (Å⁻¹), wavelength (Å).
/// Invalid wavelength, Q or scattering-angle domain returns an error.
pub fn klein_nishina(q: &[f64], wavelength: f64) -> Result<Vec<f64>, String> {
    if !wavelength.is_finite() || wavelength <= 0.0 {
        return Err("Positive wavelength required for Klein–Nishina".into());
    }
    q.iter()
        .map(|q| {
            let arg = q * wavelength / (4.0 * PI);
            if arg.abs() > 1.0 {
                return Err("Q/wavelength outside angular domain".into());
            }
            let tth = 2.0 * arg.asin();
            let p = 1.0
                / (1.0
                    + (6.62607015e-34 / (wavelength * 1e-10 * 9.1093837139e-31 * 299792458.0))
                        * (1.0 - tth.cos()));
            Ok((p.powi(3) - p.powi(2) * tth.sin().powi(2) + p) / (1.0 + tth.cos().powi(2)))
        })
        .collect()
}
type Point = [f64; 2];
fn points(radius: f64, angle: f64, width: f64) -> (Point, Point) {
    let c = radius * angle.cos();
    let s = radius * angle.sin();
    let dx = 0.5 * width * angle.sin();
    let dy = 0.5 * width * angle.cos();
    ([c - dx, s + dy], [c + dx, s - dy])
}
fn intercept(a: Point, b: Point) -> f64 {
    let m = (b[1] - a[1]) / (b[0] - a[0]);
    let c = b[1] - b[0] * m;
    -c / m
}
fn angle(a: Point, b: Point, x: f64) -> f64 {
    let ax = a[0] - x;
    let bx = b[0] - x;
    ((ax * bx + a[1] * b[1]) / ((ax * ax + a[1] * a[1]).sqrt() * (bx * bx + b[1] * b[1]).sqrt()))
        .acos()
}
/// Default-geometry DAC correction with wavelength in Å and thicknesses in µm.
/// Returns (sample correction, diamond-region correction). Requires
/// `0 < sample_um < initial_um <= 10000` and a valid Q angular domain.
pub fn soller_dac(
    q: &[f64],
    wavelength: f64,
    initial_um: f64,
    sample_um: f64,
) -> Result<(Vec<f64>, Vec<f64>), String> {
    if !initial_um.is_finite()
        || !sample_um.is_finite()
        || sample_um <= 0.0
        || initial_um <= sample_um
        || initial_um > 10_000.0
        || !wavelength.is_finite()
        || wavelength <= 0.0
    {
        return Err("Invalid DAC geometry/wavelength".into());
    }
    let initial = initial_um / 1000.0;
    let sample = sample_um / 1000.0;
    let max = initial + 0.1;
    let xs = arange(-max * 0.5, max * 0.5, 0.001)?;
    let mut sums = vec![vec![0.0; q.len()]; 3];
    for (i, q) in q.iter().enumerate() {
        let arg = q * wavelength / (4.0 * PI);
        if arg.abs() > 1.0 {
            return Err("DAC Q outside angular domain".into());
        }
        // Preserve the degree/radian roundtrip used by SollerCorrectionGui.
        let deg = arg.asin() * 360.0 / PI;
        let theta = deg / 180.0 * PI;
        let (a, b) = points(70.0, theta, 0.05);
        let (c, d) = points(216.0, theta, 0.2);
        let (e, f) = points(62.0, theta, 0.05);
        let xfa = intercept(f, a);
        let xfc = intercept(f, c);
        let xbd = intercept(b, d);
        let xed = intercept(e, d);
        let xac = intercept(a, c);
        let pos = if xbd < 0.0 { 0.0 } else { xbd };
        let neg = if xac > 0.0 { 0.0 } else { xac };
        for &x in &xs {
            let mut phi = angle(a, b, x)
                .min(angle(c, d, x))
                .min(angle(c, b, x))
                .min(angle(a, d, x));
            if x > pos && x < xfa {
                phi = angle(f, c, x).min(angle(d, c, x));
            }
            if x > xfa || x > xfc {
                phi = 0.0;
            }
            if x < neg && x > xed {
                phi = angle(e, d, x).min(angle(c, d, x));
            }
            if x < xed {
                phi = 0.0;
            }
            if !phi.is_finite() {
                return Err("Nonfinite Soller geometry".into());
            }
            if x > -sample * 0.5 && x < sample * 0.5 {
                sums[0][i] += phi;
            }
            if x > sample * 0.5 && x < initial * 0.5 {
                sums[1][i] += phi;
            }
            if x > -initial * 0.5 && x < -sample * 0.5 {
                sums[2][i] += phi;
            }
        }
    }
    for region in &mut sums {
        if region.iter().any(|v| *v <= 0.0) {
            return Err("Empty/zero-acceptance Soller region".into());
        }
        for v in region.iter_mut() {
            *v = 1.0 / *v;
        }
        let min = region.iter().copied().fold(f64::INFINITY, f64::min);
        for v in region {
            *v /= min;
        }
    }
    let diamond = sums[1]
        .iter()
        .zip(&sums[2])
        .map(|(a, b)| (a + b) / 2.0)
        .collect();
    Ok((sums[0].clone(), diamond))
}

/// Euclidean norm of a coordinate vector.
pub fn vector_length(values: &[f64]) -> f64 {
    values.iter().map(|v| v * v).sum::<f64>().sqrt()
}
/// Angle between vectors from each 2D center position to two side points,
/// in radians. Inputs use a common length unit.
pub fn calculate_angles(
    a: [f64; 2],
    b: [f64; 2],
    centers: &[[f64; 2]],
) -> Result<Vec<f64>, String> {
    centers
        .iter()
        .map(|p| {
            let aa = [a[0] - p[0], a[1] - p[1]];
            let bb = [b[0] - p[0], b[1] - p[1]];
            let n = vector_length(&aa) * vector_length(&bb);
            if !n.is_finite() || n == 0. {
                return Err("Degenerate angle vectors".into());
            }
            Ok(((aa[0] * bb[0] + aa[1] * bb[1]) / n).clamp(-1., 1.).acos())
        })
        .collect()
}
/// Side points for a slit at radius/width in a common length unit, angle in radians.
pub fn rectangular_side_points(radius: f64, angle: f64, width: f64) -> ([f64; 2], [f64; 2]) {
    points(radius, angle, width)
}
/// x-axis intercept of the line through two points; degenerate/parallel inputs
/// can produce nonfinite values, following the reference arithmetic.
pub fn x_axis_intercept(a: [f64; 2], b: [f64; 2]) -> f64 {
    intercept(a, b)
}
/// y-axis intercept of the line through two points; degenerate/vertical inputs
/// can produce nonfinite values, following the reference arithmetic.
pub fn y_axis_intercept(a: [f64; 2], b: [f64; 2]) -> f64 {
    (b[1] - a[1]) / (b[0] - a[0]) * (-b[0]) + b[1]
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn forward_scattering_kn_limit_and_angular_domain() {
        assert_eq!(klein_nishina(&[0.], 0.29).unwrap(), vec![1.]);
        assert!(klein_nishina(&[100.], 0.29).is_err());
        assert!(soller_dac(&[1., 2.], 0.29, 20., 40.).is_err());
    }
}
