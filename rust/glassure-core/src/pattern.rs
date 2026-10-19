//! Owned x/y patterns and basic processing without Python.
//!
//! Text I/O works on every target; native builds add filesystem methods. General
//! patterns allow repeated coordinates for legacy extrapolation compatibility.
//! Numerical algorithms validate their own additional grid requirements.
pub use crate::request::Pattern;

impl Pattern {
    /// Gaussian smoothing with sigma in **sample indices**, using reflected
    /// boundaries and a kernel truncated at approximately four sigma.
    pub fn smooth(&self, sigma: f64) -> Result<Self, String> {
        self.validate()?;
        if !sigma.is_finite() || sigma <= 0. || sigma > 100_000. {
            return Err("Invalid Gaussian width".into());
        }
        let radius = (4. * sigma + 0.5) as isize;
        let n = self.y.len() as isize;
        let mut kernel: Vec<f64> = (-radius..=radius)
            .map(|j| (-0.5 * (j as f64 / sigma).powi(2)).exp())
            .collect();
        let sum: f64 = kernel.iter().sum();
        for k in &mut kernel {
            *k /= sum;
        }
        let y = (0..n)
            .map(|i| {
                (-radius..=radius)
                    .zip(&kernel)
                    .map(|(j, k)| {
                        let v = (i + j).rem_euclid(2 * n);
                        let v = if v >= n { 2 * n - 1 - v } else { v };
                        k * self.y[v as usize]
                    })
                    .sum()
            })
            .collect();
        Self::new(self.x.clone(), y)
    }
    /// Average values in coordinate bins of positive width `bin_size`.
    /// Empty bins contain NaN; remove or fill them before PDF calculation.
    pub fn rebin(&self, bin_size: f64) -> Result<Self, String> {
        self.validate()?;
        if !bin_size.is_finite() || bin_size <= 0. {
            return Err("Invalid bin size".into());
        }
        let lo = (self.x[0] / bin_size).round_ties_even() * bin_size;
        let hi = (self.x[self.x.len() - 1] / bin_size).round_ties_even() * bin_size;
        let x = crate::numeric::arange(lo, hi + 0.1 * bin_size, bin_size)?;
        let mut y = vec![0.; x.len()];
        let mut counts = vec![0usize; x.len()];
        for (xx, yy) in self.x.iter().zip(&self.y) {
            let mut i = ((xx - (lo - bin_size / 2.)) / bin_size).floor() as isize;
            if *xx == x[x.len() - 1] + bin_size / 2. {
                i = x.len() as isize - 1;
            }
            if i >= 0 && (i as usize) < x.len() {
                y[i as usize] += yy;
                counts[i as usize] += 1;
            }
        }
        for (v, c) in y.iter_mut().zip(counts) {
            *v = if c == 0 { f64::NAN } else { *v / c as f64 };
        }
        Ok(Self { x, y })
    }
    /// Construct a pattern after [`Self::validate`], taking ownership of arrays.
    pub fn new(x: Vec<f64>, y: Vec<f64>) -> Result<Self, String> {
        let p = Self { x, y };
        p.validate()?;
        Ok(p)
    }
    /// Require matching, nonempty finite arrays, nondecreasing coordinates and
    /// at most one million points. PDF requests impose stricter Q requirements.
    pub fn validate(&self) -> Result<(), String> {
        if self.x.len() != self.y.len()
            || self.x.is_empty()
            || self.x.len() > 1_000_000
            || self.x.iter().chain(&self.y).any(|v| !v.is_finite())
            || self.x.windows(2).any(|v| v[1] < v[0])
        {
            return Err("Invalid pattern".into());
        }
        Ok(())
    }
    /// Linear interpolation; outside the domain, extend the nearest end segment.
    /// At least two points are required. Use strictly increasing coordinates to
    /// avoid zero-width interpolation intervals.
    pub fn interpolate(&self, x: f64) -> Result<f64, String> {
        self.validate()?;
        if self.x.len() < 2 || !x.is_finite() {
            return Err("Interpolation needs two points and a finite coordinate".into());
        }
        Ok(self.interpolate_unchecked(x))
    }
    pub(crate) fn interpolate_unchecked(&self, x: f64) -> f64 {
        let i = self
            .x
            .partition_point(|v| *v <= x)
            .saturating_sub(1)
            .min(self.x.len() - 2);
        self.y[i] + (self.y[i + 1] - self.y[i]) * (x - self.x[i]) / (self.x[i + 1] - self.x[i])
    }
    /// Strictly crop to `lower < x < upper`; an empty result is an error.
    pub fn limit(&self, lower: f64, upper: f64) -> Result<Self, String> {
        self.validate()?;
        let (x, y) = self
            .x
            .iter()
            .zip(&self.y)
            .filter(|(x, _)| **x > lower && **x < upper)
            .map(|(x, y)| (*x, *y))
            .unzip();
        Self::new(x, y)
    }
    /// Multiply all y values by a scalar without modifying this pattern.
    pub fn scale(&self, value: f64) -> Result<Self, String> {
        Self::new(self.x.clone(), self.y.iter().map(|y| y * value).collect())
    }
    /// Multiply y elementwise; `values` must have the same length.
    pub fn multiply(&self, values: &[f64]) -> Result<Self, String> {
        if values.len() != self.y.len() {
            return Err("Multiplier length must match pattern".into());
        }
        Self::new(
            self.x.clone(),
            self.y.iter().zip(values).map(|(a, b)| a * b).collect(),
        )
    }
    /// Add a scalar to every y value.
    pub fn add_scalar(&self, value: f64) -> Result<Self, String> {
        Self::new(self.x.clone(), self.y.iter().map(|y| y + value).collect())
    }
    /// Return `self + scale * other`, following Python Pattern arithmetic.
    /// Equal-length arrays are combined by index even if their x values differ;
    /// other lengths use linear interpolation over the common coordinate domain.
    pub fn combine(&self, other: &Self, scale: f64) -> Result<Self, String> {
        self.validate()?;
        other.validate()?;
        if self.x.len() == other.x.len() {
            return Self::new(
                self.x.clone(),
                self.y
                    .iter()
                    .zip(&other.y)
                    .map(|(a, b)| a + scale * b)
                    .collect(),
            );
        }
        if other.x.len() < 2 {
            return Err("Interpolation needs two points".into());
        }
        let (x, y) = self
            .x
            .iter()
            .zip(&self.y)
            .filter(|(x, _)| **x >= other.x[0] && **x <= other.x[other.x.len() - 1])
            .map(|(x, y)| (*x, *y + scale * other.interpolate_unchecked(*x)))
            .unzip();
        Self::new(x, y).map_err(|_| "Patterns do not overlap".into())
    }
    /// Extend toward `value` with constant `y0`, using mean coordinate spacing.
    /// If `value` is already within the domain, return an unchanged copy.
    pub fn extend_to(&self, value: f64, y0: f64) -> Result<Self, String> {
        self.validate()?;
        if self.x.len() < 2 {
            return Err("Extension needs two points".into());
        }
        let step = (self.x[self.x.len() - 1] - self.x[0]) / (self.x.len() - 1) as f64;
        let mut x = self.x.clone();
        let mut y = self.y.clone();
        if value < self.x[0] {
            let mut fill = crate::numeric::arange(self.x[0] - step, value - step * 0.5, -step)?;
            fill.reverse();
            let mut values = vec![y0; fill.len()];
            fill.extend(x);
            values.extend(y);
            x = fill;
            y = values;
        } else if value > *self.x.last().unwrap() {
            let fill =
                crate::numeric::arange(self.x.last().unwrap() + step, value + step * 0.5, step)?;
            y.extend(vec![y0; fill.len()]);
            x.extend(fill);
        }
        Self::new(x, y)
    }
    /// Parse whitespace-separated x/y columns after skipping physical header rows.
    /// `#` comments and blank lines are ignored; additional columns are ignored.
    /// Malformed/nonfinite values and decreasing coordinates return errors.
    pub fn from_xy_text(text: &str, skip_rows: usize) -> Result<Self, String> {
        let (mut x, mut y) = (Vec::new(), Vec::new());
        for (n, line) in text.lines().enumerate().skip(skip_rows) {
            let line = line.split('#').next().unwrap_or("").trim();
            if line.is_empty() {
                continue;
            }
            let parts: Vec<_> = line.split_whitespace().collect();
            if parts.len() < 2 {
                return Err(format!("Expected at least two columns at line {}", n + 1));
            }
            x.push(
                parts[0]
                    .parse::<f64>()
                    .map_err(|_| format!("Invalid x at line {}", n + 1))?,
            );
            y.push(
                parts[1]
                    .parse::<f64>()
                    .map_err(|_| format!("Invalid y at line {}", n + 1))?,
            );
        }
        Self::new(x, y)
    }
    /// Export two numeric columns with enough precision to round-trip f64 values.
    pub fn to_xy_text(&self) -> Result<String, String> {
        use std::fmt::Write;
        self.validate()?;
        let mut text = String::new();
        for (x, y) in self.x.iter().zip(&self.y) {
            writeln!(&mut text, "{x:.17e} {y:.17e}").map_err(|e| e.to_string())?;
        }
        Ok(text)
    }
    #[cfg(not(target_arch = "wasm32"))]
    /// Read UTF-8 XY/CHI data. `.chi` always skips four rows; other extensions
    /// use `skip_rows`. Not available on WASM; use [`Self::from_xy_text`] there.
    pub fn from_file(path: impl AsRef<std::path::Path>, skip_rows: usize) -> Result<Self, String> {
        let path = path.as_ref();
        let skip_rows = if path.extension().and_then(|s| s.to_str()) == Some("chi") {
            4
        } else {
            skip_rows
        };
        Self::from_xy_text(
            &std::fs::read_to_string(path).map_err(|e| e.to_string())?,
            skip_rows,
        )
    }
    #[cfg(not(target_arch = "wasm32"))]
    /// Write [`Self::to_xy_text`] to a native file, replacing existing contents.
    pub fn save(&self, path: impl AsRef<std::path::Path>) -> Result<(), String> {
        std::fs::write(path, self.to_xy_text()?).map_err(|e| e.to_string())
    }
}
