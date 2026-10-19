//! Embedded Hajdu, Brown–Hubbell and pinned Xraylib scattering factors.
//!
//! Q is Å⁻¹. Compositions contain relative atomic amounts, not mass fractions.
//! [`atomic_density`] converts mass density (g/cm³) to atoms/Å³. No runtime
//! Python, filesystem, network or installed xraylib library is used.
use serde::{Deserialize, Serialize};
use std::{collections::BTreeMap, f64::consts::PI};

#[path = "scattering_data.rs"]
mod scattering_data;
use scattering_data::{COHERENT, INCOHERENT, KNOTS, WEIGHTS};
#[path = "hajdu_data.rs"]
mod hajdu_data;
use hajdu_data::{HAJDU_COHERENT, HAJDU_INCOHERENT};

#[derive(Clone, Copy, Default, Debug, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
/// Embedded dataset, serialized as `hajdu`, `brown_hubbell` or `xraylib`.
pub enum Source {
    /// Hajdu parameterization from the original Glassure tables.
    Hajdu,
    #[default]
    /// Four-Gaussian Brown form factors and cubic Hubbell incoherent intensities.
    BrownHubbell,
    /// Xraylib 4.2.1 FF/SF tables and interpolation; elements Z = 1–98.
    Xraylib,
}
impl Source {
    /// Parse the exact serialized dataset name; unknown names are errors.
    pub fn parse(value: &str) -> Result<Self, String> {
        match value {
            "hajdu" => Ok(Self::Hajdu),
            "brown_hubbell" => Ok(Self::BrownHubbell),
            "xraylib" => Ok(Self::Xraylib),
            _ => Err(format!("Unknown scattering source: {value}")),
        }
    }
}

struct CoherentRow {
    key: &'static str,
    a: [f64; 4],
    b: [f64; 4],
    c: f64,
}
struct IncoherentRow {
    element: &'static str,
    coefficients: [f64; 35],
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(untagged)]
/// A formula string or a map of element symbols to relative atomic amounts.
pub enum Composition {
    /// Formula such as `SiO2`, `Mg2[SiO4]` or fractional stoichiometry.
    Formula(String),
    /// Nonnegative finite amounts with a positive total (not weight fractions).
    Amounts(BTreeMap<String, f64>),
}

fn number(chars: &[u8], pos: &mut usize) -> Result<f64, String> {
    let start = *pos;
    while *pos < chars.len() && (chars[*pos].is_ascii_digit() || chars[*pos] == b'.') {
        *pos += 1;
    }
    if start == *pos {
        return Ok(1.0);
    }
    let value: f64 = std::str::from_utf8(&chars[start..*pos])
        .unwrap()
        .parse()
        .map_err(|_| "Invalid stoichiometry")?;
    if !value.is_finite() || value < 0.0 {
        return Err("Stoichiometry must be nonnegative".into());
    }
    Ok(value)
}

fn group(chars: &[u8], pos: &mut usize, depth: usize) -> Result<BTreeMap<String, f64>, String> {
    if depth > 16 {
        return Err("Formula nesting limit".into());
    }
    let mut result = BTreeMap::new();
    while *pos < chars.len() && chars[*pos] != b')' {
        if chars[*pos] == b'(' {
            *pos += 1;
            let nested = group(chars, pos, depth + 1)?;
            if nested.is_empty() || chars.get(*pos) != Some(&b')') {
                return Err("Invalid parentheses".into());
            }
            *pos += 1;
            let count = number(chars, pos)?;
            for (key, value) in nested {
                *result.entry(key).or_default() += value * count;
            }
        } else {
            if !chars[*pos].is_ascii_uppercase() {
                return Err("Expected element symbol".into());
            }
            let start = *pos;
            *pos += 1;
            while *pos < chars.len() && chars[*pos].is_ascii_lowercase() {
                *pos += 1;
            }
            let key = std::str::from_utf8(&chars[start..*pos])
                .unwrap()
                .to_string();
            let count = number(chars, pos)?;
            *result.entry(key).or_default() += count;
        }
    }
    Ok(result)
}

impl Composition {
    /// Parse/validate amounts, combining repeated symbols and nested groups.
    /// This validates formula syntax and counts; element support is checked by
    /// the operation/dataset that consumes the composition.
    pub fn amounts(&self) -> Result<BTreeMap<String, f64>, String> {
        let values = match self {
            Self::Amounts(values) => values.clone(),
            Self::Formula(formula) => {
                let formula: String = formula
                    .chars()
                    .filter(|c| !c.is_whitespace())
                    .map(|c| match c {
                        '[' | '{' => '(',
                        ']' | '}' => ')',
                        _ => c,
                    })
                    .collect();
                if !formula.is_ascii() || formula.len() > 4096 {
                    return Err("Invalid formula".into());
                }
                let mut pos = 0;
                let values = group(formula.as_bytes(), &mut pos, 0)?;
                if pos != formula.len() {
                    return Err("Unmatched parentheses".into());
                }
                values
            }
        };
        let sum: f64 = values.values().sum();
        if values.is_empty()
            || values.len() > 210
            || !sum.is_finite()
            || sum <= 0.0
            || values.values().any(|v| !v.is_finite() || *v < 0.0)
        {
            return Err(
                "Composition amounts must be finite and nonnegative, with a positive total".into(),
            );
        }
        Ok(values)
    }
    /// Atomic fractions normalized to sum to one.
    pub fn fractions(&self) -> Result<BTreeMap<String, f64>, String> {
        let mut values = self.amounts()?;
        let sum: f64 = values.values().sum();
        for value in values.values_mut() {
            *value /= sum;
        }
        Ok(values)
    }
}

/// Symbols supported by the selected coherent dataset. Xraylib returns Z = 1–98.
pub fn available_elements(source: Source) -> Vec<&'static str> {
    match source {
        Source::Xraylib => crate::functions::ELEMENTS
            .split_whitespace()
            .take(98)
            .collect(),
        Source::Hajdu => HAJDU_COHERENT.iter().map(|r| r.key).collect(),
        Source::BrownHubbell => COHERENT.iter().map(|r| r.key).collect(),
    }
}
/// Atomic coherent amplitude f(Q) for nonnegative Q in Å⁻¹.
/// Unknown symbols, invalid values and out-of-table Xraylib Q are errors.
pub fn coherent_factor(element: &str, q: &[f64], source: Source) -> Result<Vec<f64>, String> {
    if q.is_empty() || q.iter().any(|v| !v.is_finite() || *v < 0.0) {
        return Err("Invalid Q grid".into());
    }
    if matches!(source, Source::Xraylib) {
        return crate::xraylib::coherent(element, q);
    }
    let table = match source {
        Source::Hajdu => HAJDU_COHERENT,
        Source::BrownHubbell => COHERENT,
        Source::Xraylib => unreachable!(),
    };
    let index = table
        .binary_search_by_key(&element, |r| r.key)
        .map_err(|_| format!("Unknown coherent species: {element}"))?;
    Ok(q.iter().map(|v| coherent(&table[index], *v)).collect())
}
/// Atomic incoherent intensity for Q in Å⁻¹, using the selected source.
/// Tabulated datasets reject coordinates outside their supported range.
pub fn incoherent_intensity(element: &str, q: &[f64], source: Source) -> Result<Vec<f64>, String> {
    if q.is_empty() || q.iter().any(|v| !v.is_finite() || *v < 0.0) {
        return Err("Invalid Q grid".into());
    }
    match source {
        Source::Xraylib => crate::xraylib::incoherent(element, q),
        Source::Hajdu => {
            let i = HAJDU_INCOHERENT
                .binary_search_by_key(&element, |r| r.0)
                .map_err(|_| format!("No Hajdu Compton coefficients for {element}"))?;
            let [z, m, k, l] = HAJDU_INCOHERENT[i].1;
            Ok(coherent_factor(element, q, source)?
                .iter()
                .zip(q)
                .map(|(f, q)| {
                    let s = q / (4.0 * PI);
                    (z - f * f / z) * (1.0 - m * ((-k * s).exp() - (-l * s).exp()))
                })
                .collect())
        }
        Source::BrownHubbell => {
            if q.iter().any(|v| *v < KNOTS[3] || *v > KNOTS[35]) {
                return Err("Q outside Hubbell table range".into());
            }
            let key: String = element
                .chars()
                .take_while(|c| c.is_ascii_alphabetic())
                .collect();
            let i = INCOHERENT
                .binary_search_by_key(&key.as_str(), |r| r.element)
                .map_err(|_| format!("No Compton table for {key}"))?;
            Ok(q.iter().map(|v| cubic(&INCOHERENT[i], *v)).collect())
        }
    }
}
/// Atomic-fraction-weighted mean atomic mass, in g/mol of atoms.
pub fn mean_weight(composition: &Composition) -> Result<f64, String> {
    composition
        .fractions()?
        .iter()
        .map(|(key, c)| {
            let element: String = key
                .chars()
                .take_while(|c| c.is_ascii_alphabetic())
                .collect();
            let i = WEIGHTS
                .binary_search_by_key(&element.as_str(), |r| r.0)
                .map_err(|_| format!("No atomic weight for {element}"))?;
            Ok(c * WEIGHTS[i].1)
        })
        .sum()
}
/// Convert positive mass density (g/cm³) to atomic number density (atoms/Å³).
/// Uses Glassure's reference conversion constant 0.602214129.
pub fn atomic_density(composition: &Composition, density: f64) -> Result<f64, String> {
    if !density.is_finite() || density <= 0.0 {
        return Err("Density must be finite and positive".into());
    }
    Ok(density / mean_weight(composition)? * 0.602214129)
}
/// Convert positive atomic number density (atoms/Å³) to mass density (g/cm³).
pub fn mass_density(composition: &Composition, density: f64) -> Result<f64, String> {
    if !density.is_finite() || density <= 0.0 {
        return Err("Density must be finite and positive".into());
    }
    Ok(density * mean_weight(composition)? / 0.602214129)
}
/// Mixture scattering moments and atomic density for the selected source.
/// `density` is mass density in g/cm³; Q is Å⁻¹. See [`Factors`] for definitions.
pub fn factors_with_source(
    composition: &Composition,
    density: f64,
    q: &[f64],
    source: Source,
) -> Result<Factors, String> {
    if matches!(source, Source::BrownHubbell) {
        return factors(composition, density, q);
    }
    let fractions = composition.fractions()?;
    let mut f2 = vec![0.; q.len()];
    let mut mean = f2.clone();
    let mut incoherent = f2.clone();
    let (mut fzero, mut f2zero) = (0., 0.);
    for (key, c) in fractions {
        let f = coherent_factor(&key, q, source)?;
        let inc = incoherent_intensity(&key, q, source)?;
        let z = coherent_factor(&key, &[0.], source)?[0];
        fzero += c * z;
        f2zero += c * z * z;
        for i in 0..q.len() {
            f2[i] += c * f[i] * f[i];
            mean[i] += c * f[i];
            incoherent[i] += c * inc[i];
        }
    }
    if fzero == 0. || mean.iter().any(|v| !v.is_finite() || *v == 0.) {
        return Err("Singular mean form factor".into());
    }
    Ok(Factors {
        f2,
        fm2: mean.iter().map(|v| v * v).collect(),
        incoherent,
        atomic_density: atomic_density(composition, density)?,
        s0: 1. - f2zero / (fzero * fzero),
    })
}

#[derive(Serialize)]
/// Mixture moments on the requested Q grid; c denotes atomic fraction.
pub struct Factors {
    /// `<f²> = sum(c_i * f_i(Q)²)`.
    pub f2: Vec<f64>,
    /// `<f>² = [sum(c_i * f_i(Q))]²` (different from `f2`).
    pub fm2: Vec<f64>,
    /// Atomic-fraction-weighted incoherent intensity.
    pub incoherent: Vec<f64>,
    /// Number density in atoms/Å³.
    pub atomic_density: f64,
    /// The mixture limit `1 - <f(0)²>/<f(0)>²` used for low-Q extrapolation.
    pub s0: f64,
}

fn coherent(row: &CoherentRow, q: f64) -> f64 {
    let s2 = (q / (4.0 * PI)).powi(2);
    // Preserve Python's sum-of-Gaussians then constant evaluation order.
    let mut value = 0.0;
    for i in 0..4 {
        value += row.a[i] * (-row.b[i] * s2).exp();
    }
    value + row.c
}

fn cubic(row: &IncoherentRow, q: f64) -> f64 {
    // Cubic de Boor evaluation of SciPy's not-a-knot B-spline, including endpoints.
    let k = KNOTS
        .partition_point(|t| *t <= q)
        .saturating_sub(1)
        .clamp(3, 34);
    let mut d = [0.0; 4];
    d.copy_from_slice(&row.coefficients[k - 3..=k]);
    for r in 1..=3 {
        for j in (r..=3).rev() {
            let i = k - 3 + j;
            let alpha = (q - KNOTS[i]) / (KNOTS[i + 4 - r] - KNOTS[i]);
            d[j] = (1.0 - alpha) * d[j - 1] + alpha * d[j];
        }
    }
    d[3]
}

/// Mixture moments using Brown–Hubbell; equivalent to [`factors_with_source`]
/// with [`Source::BrownHubbell`]. Density is g/cm³, Q is Å⁻¹.
pub fn factors(composition: &Composition, density: f64, q: &[f64]) -> Result<Factors, String> {
    if q.is_empty()
        || q.len() > 1_000_000
        || q.iter()
            .any(|v| !v.is_finite() || *v < KNOTS[3] || *v > KNOTS[35])
        || !density.is_finite()
        || density <= 0.0
    {
        return Err("Invalid density or Q outside the Hubbell table range".into());
    }
    let fractions = composition.fractions()?;
    let mut f2 = vec![0.0; q.len()];
    let mut mean = vec![0.0; q.len()];
    let mut incoherent = vec![0.0; q.len()];
    let (mut mean_weight, mut mean_zero, mut square_zero) = (0.0, 0.0, 0.0);
    for (key, concentration) in fractions {
        let index = COHERENT
            .binary_search_by_key(&key.as_str(), |row| row.key)
            .map_err(|_| format!("Unknown coherent species: {key}"))?;
        let row = &COHERENT[index];
        let element: String = key
            .chars()
            .take_while(|c| c.is_ascii_alphabetic())
            .collect();
        let index = INCOHERENT
            .binary_search_by_key(&element.as_str(), |row| row.element)
            .map_err(|_| format!("No Compton table for: {element}"))?;
        let inc = &INCOHERENT[index];
        let index = WEIGHTS
            .binary_search_by_key(&element.as_str(), |row| row.0)
            .map_err(|_| format!("No atomic weight for: {element}"))?;
        mean_weight += concentration * WEIGHTS[index].1;
        let zero = coherent(row, 0.0);
        mean_zero += concentration * zero;
        square_zero += concentration * zero * zero;
        for (i, &value) in q.iter().enumerate() {
            let f = coherent(row, value);
            f2[i] += concentration * f * f;
            mean[i] += concentration * f;
            incoherent[i] += concentration * cubic(inc, value);
        }
    }
    let fm2: Vec<_> = mean.iter().map(|v| v * v).collect();
    if fm2.iter().any(|v| !v.is_finite() || *v <= 0.0) || mean_zero == 0.0 {
        return Err("Singular mean form factor".into());
    }
    Ok(Factors {
        f2,
        fm2,
        incoherent,
        atomic_density: density / mean_weight * 0.602214129,
        s0: -square_zero / (mean_zero * mean_zero) + 1.0,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn formula_groups_and_errors() {
        let c = Composition::Formula("(Mg0.5Fe0.5)2SiO4".into())
            .fractions()
            .unwrap();
        assert_eq!(c["O"], 4.0 / 7.0);
        assert_eq!(c["Mg"], 1.0 / 7.0);
        let zero = Composition::Formula("SiO0".into()).fractions().unwrap();
        assert_eq!(zero["Si"], 1.);
        assert_eq!(zero["O"], 0.);
        for formula in ["", "Si0O0", "(SiO2", "SiO2)", "Si-1", "Fe..2"] {
            assert!(
                Composition::Formula(formula.into()).fractions().is_err(),
                "{formula}"
            );
        }
        assert!(factors(&Composition::Formula("Xx".into()), 2.2, &[0.0]).is_err());
    }
    #[test]
    fn finite_zero_and_range_boundaries() {
        let values = factors(
            &Composition::Formula("SiO2".into()),
            2.2,
            &[0.0, 1.0, KNOTS[35]],
        )
        .unwrap();
        assert_eq!(values.incoherent[0], 0.0);
        assert!(values.atomic_density > 0.06 && values.atomic_density < 0.07);
        assert!(factors(
            &Composition::Formula("SiO2".into()),
            2.2,
            &[KNOTS[35] + 1.0]
        )
        .is_err());
    }
}
