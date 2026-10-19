//! Pure-Rust evaluation of the pinned xraylib 4.2.1 FF/SF spline tables.
//! See data/xraylib for source hashes, original tables and upstream BSD notices.
use std::{f64::consts::PI, sync::OnceLock};
type Tables = Vec<Vec<[f64; 3]>>;
fn decode(data: &[u8]) -> Tables {
    assert_eq!(&data[..8], b"GLXR0001");
    let mut pos = 8;
    let count = u32::from_le_bytes(data[pos..pos + 4].try_into().unwrap()) as usize;
    pos += 4;
    let mut tables = Vec::with_capacity(count);
    for _ in 0..count {
        let n = u32::from_le_bytes(data[pos..pos + 4].try_into().unwrap()) as usize;
        pos += 4;
        let mut rows = Vec::with_capacity(n);
        for _ in 0..n {
            let mut row = [0.; 3];
            for v in &mut row {
                *v = f64::from_le_bytes(data[pos..pos + 8].try_into().unwrap());
                pos += 8;
            }
            rows.push(row);
        }
        tables.push(rows);
    }
    assert_eq!(pos, data.len());
    tables
}
fn table(z: usize, inc: bool) -> Result<&'static [[f64; 3]], String> {
    static FF: OnceLock<Tables> = OnceLock::new();
    static SF: OnceLock<Tables> = OnceLock::new();
    let tables = if inc {
        SF.get_or_init(|| decode(include_bytes!("../data/xraylib/SF.bin")))
    } else {
        FF.get_or_init(|| decode(include_bytes!("../data/xraylib/FF.bin")))
    };
    tables
        .get(z.wrapping_sub(1))
        .map(Vec::as_slice)
        .ok_or("Xraylib FF/SF tables support Z=1..98".into())
}
fn interpolate(rows: &[[f64; 3]], x: f64) -> Result<f64, String> {
    if x < rows[0][0] || x - rows[rows.len() - 1][0] > 1e-7 {
        return Err("Q outside Xraylib table range".into());
    }
    let lo = rows
        .partition_point(|r| r[0] <= x)
        .saturating_sub(1)
        .min(rows.len() - 2);
    let hi = lo + 1;
    let h = rows[hi][0] - rows[lo][0];
    let a = (rows[hi][0] - x) / h;
    let b = (x - rows[lo][0]) / h;
    Ok(a * rows[lo][1]
        + b * rows[hi][1]
        + ((a * a * a - a) * rows[lo][2] + (b * b * b - b) * rows[hi][2]) * (h * h) / 6.)
}
pub fn coherent(element: &str, q: &[f64]) -> Result<Vec<f64>, String> {
    let z = crate::functions::atomic_number(element)?;
    let rows = table(z, false)?;
    q.iter()
        .map(|q| {
            if *q == 0. {
                Ok(z as f64)
            } else {
                interpolate(rows, q / (4. * PI))
            }
        })
        .collect()
}
pub fn incoherent(element: &str, q: &[f64]) -> Result<Vec<f64>, String> {
    let rows = table(crate::functions::atomic_number(element)?, true)?;
    let xx: Vec<_> = q.iter().map(|q| q / (4. * PI)).collect();
    let high: Vec<usize> = xx
        .iter()
        .enumerate()
        .filter(|(_, q)| **q >= 0.001)
        .map(|(i, _)| i)
        .collect();
    let mut values = vec![0.; q.len()];
    for &i in &high {
        values[i] = interpolate(rows, xx[i])?;
    }
    if high.len() >= 4 && high.len() != q.len() {
        let step = xx[1] - xx[0];
        if step <= 0. || !step.is_finite() {
            return Err("Xraylib low-Q extension requires positive first Q step".into());
        }
        let mut x = crate::numeric::arange(0., -1., -step)?;
        x.reverse();
        let mut y = vec![0.; x.len()];
        for i in high.iter().take(3) {
            x.push(xx[*i]);
            y.push(values[*i]);
        }
        let low: Vec<usize> = xx
            .iter()
            .enumerate()
            .filter(|(_, q)| **q < 0.001)
            .map(|(i, _)| i)
            .collect();
        let grid: Vec<_> = low.iter().map(|i| xx[*i]).collect();
        let result = crate::numeric::spline_values(&x, &y, &grid, Some(0.))?;
        for (i, value) in low.iter().zip(result) {
            values[*i] = value;
        }
    }
    Ok(values)
}
