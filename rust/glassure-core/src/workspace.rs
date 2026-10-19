//! Per-fit transform storage. Keep the existing arithmetic and FFT sizing;
//! never share mutable buffers between fits or Rayon workers.
use crate::{Method, PLANNER};
use rustfft::{num_complex::Complex, Fft};
use std::{f64::consts::PI, sync::Arc};

struct Interpolation {
    lo: usize,
    delta: f64,
    width: f64,
    endpoint: bool,
}
impl Interpolation {
    fn new(value: f64, step: f64, size: usize) -> Self {
        let endpoint = value >= (size - 1) as f64 * step;
        let lo = ((value / step).floor() as usize).min(size - 2);
        let x0 = lo as f64 * step;
        let x1 = (lo + 1) as f64 * step;
        Self {
            lo,
            delta: value - x0,
            width: x1 - x0,
            endpoint,
        }
    }
    fn value(&self, buffer: &[Complex<f64>], scale: f64) -> f64 {
        if self.endpoint {
            return buffer[buffer.len() - 1].im * scale;
        }
        let y0 = buffer[self.lo].im * scale;
        let y1 = buffer[self.lo + 1].im * scale;
        y0 + (y1 - y0) / self.width * self.delta
    }
    fn paired_value(&self, buffer: &[Complex<f64>], scale: f64, second: bool) -> f64 {
        // Recover the two real-input sine transforms from conjugate symmetry.
        let at = |k: usize| {
            let mirror = (buffer.len() - k) % buffer.len();
            if second {
                (buffer[mirror].re - buffer[k].re) * 0.5 * scale
            } else {
                (buffer[k].im - buffer[mirror].im) * 0.5 * scale
            }
        };
        if self.endpoint {
            return at(buffer.len() - 1);
        }
        let y0 = at(self.lo);
        let y1 = at(self.lo + 1);
        y0 + (y1 - y0) / self.width * self.delta
    }
}

struct FftStorage {
    plan: Arc<dyn Fft<f64>>,
    buffer: Vec<Complex<f64>>,
    scratch: Vec<Complex<f64>>,
    output: Option<Vec<Complex<f64>>>,
    input_len: usize,
    interpolation: Vec<Interpolation>,
    scale: f64,
}
impl FftStorage {
    fn new(size: usize, coordinates: &[f64], step: f64, scale: f64) -> Self {
        let plan = PLANNER.with(|p| p.borrow_mut().plan_fft_inverse(size));
        Self::with_plan(plan, coordinates, step, scale)
    }
    fn with_plan(plan: Arc<dyn Fft<f64>>, coordinates: &[f64], step: f64, scale: f64) -> Self {
        let size = plan.len();
        // Some planners implement in-place execution as out-of-place plus a
        // full copy back. Use the immutable entry point when its output and
        // scratch require no more memory than the old in-place scratch.
        let immutable =
            size.saturating_add(plan.get_immutable_scratch_len()) <= plan.get_inplace_scratch_len();
        #[cfg(feature = "profiling")]
        let immutable = immutable && !crate::profiling::inplace_fft_forced();
        let scratch_len = if immutable {
            plan.get_immutable_scratch_len()
        } else {
            plan.get_inplace_scratch_len()
        };
        let scratch = vec![Complex::new(0., 0.); scratch_len];
        Self {
            plan,
            scratch,
            output: immutable.then(|| vec![Complex::new(0., 0.); size]),
            input_len: 0,
            buffer: vec![Complex::new(0., 0.); size],
            interpolation: coordinates
                .iter()
                .map(|v| Interpolation::new(*v, step, size))
                .collect(),
            scale,
        }
    }
    fn execute(&mut self, values: &[f64]) {
        {
            crate::profile_span!(FftInput);
            if self.output.is_some() {
                // Immutable FFTs leave this real input and its zero padding
                // untouched. Only clear a formerly active tail if it shrinks.
                if values.len() < self.input_len {
                    self.buffer[values.len()..self.input_len].fill(Complex::new(0., 0.));
                }
            } else {
                self.buffer.fill(Complex::new(0., 0.));
            }
            for (z, v) in self.buffer.iter_mut().zip(values) {
                *z = Complex::new(*v, 0.);
            }
            self.input_len = values.len();
        }
        crate::profile_span!(FftKernel);
        if let Some(output) = &mut self.output {
            self.plan
                .process_immutable_with_scratch(&self.buffer, output, &mut self.scratch);
        } else {
            self.plan
                .process_with_scratch(&mut self.buffer, &mut self.scratch);
        }
    }
    fn result(&self) -> &[Complex<f64>] {
        self.output.as_deref().unwrap_or(&self.buffer)
    }
    fn output(&self, values: &mut [f64]) {
        crate::profile_span!(FftOutput);
        for (v, at) in values.iter_mut().zip(&self.interpolation) {
            *v = at.value(self.result(), self.scale);
        }
    }
    fn execute_pair(&mut self, a: &[f64], b: &[f64], out_a: &mut [f64], out_b: &mut [f64]) {
        assert_eq!(a.len(), b.len());
        {
            crate::profile_span!(FftInput);
            if self.output.is_none() {
                self.buffer.fill(Complex::new(0., 0.));
            } else if a.len() < self.input_len {
                self.buffer[a.len()..self.input_len].fill(Complex::new(0., 0.));
            }
            for ((z, a), b) in self.buffer.iter_mut().zip(a).zip(b) {
                *z = Complex::new(*a, *b);
            }
            self.input_len = a.len();
        }
        {
            crate::profile_span!(FftKernel);
            if let Some(output) = &mut self.output {
                self.plan
                    .process_immutable_with_scratch(&self.buffer, output, &mut self.scratch);
            } else {
                self.plan
                    .process_with_scratch(&mut self.buffer, &mut self.scratch);
            }
        }
        crate::profile_span!(FftOutput);
        for ((a, b), at) in out_a.iter_mut().zip(out_b).zip(&self.interpolation) {
            *a = at.paired_value(self.result(), self.scale, false);
            *b = at.paired_value(self.result(), self.scale, true);
        }
    }
}

pub(crate) struct Forward {
    q: Vec<f64>,
    r: Vec<f64>,
    coefficient: Vec<f64>,
    fq: Vec<f64>,
    fft: Option<FftStorage>,
    pub fr: Vec<f64>,
    pub gr: Vec<f64>,
    dfq: Vec<Vec<f64>>,
    pub dfr: Vec<Vec<f64>>,
    pub dgr: Vec<Vec<f64>>,
}
impl Forward {
    pub fn new(q: &[f64], r: &[f64], method: Method, lorch: bool) -> Result<Self, String> {
        let qmax = q[q.len() - 1];
        let coefficient = q
            .iter()
            .map(|q| {
                let angle = PI * (q / qmax);
                let modification = if !lorch || angle == 0. {
                    1.
                } else {
                    angle.sin() / angle
                };
                modification * q
            })
            .collect();
        let fft = match method {
            Method::Integral => None,
            Method::Fft => {
                let dq = q[1] - q[0];
                let dr = r[1] - r[0];
                let target = (2. * PI / dr / dq).ceil();
                if !target.is_finite() || target > (1 << 22) as f64 {
                    return Err("Transform: FftTooLarge".into());
                }
                let size = (target as usize)
                    .checked_next_power_of_two()
                    .ok_or("Transform: FftTooLarge")?;
                if size < q.len() {
                    return Err("Transform: InvalidGrid".into());
                }
                let scale = 2. * (size as f64 * dq) / PI / size as f64;
                Some(FftStorage::new(
                    size,
                    r,
                    2. * PI / (size as f64 * dq),
                    scale,
                ))
            }
        };
        Ok(Self {
            q: q.to_vec(),
            r: r.to_vec(),
            coefficient,
            fq: vec![0.; q.len()],
            fft,
            fr: vec![0.; r.len()],
            gr: vec![0.; r.len()],
            dfq: vec![],
            dfr: vec![],
            dgr: vec![],
        })
    }
    pub fn evaluate(&mut self, sq: &[f64], density: f64) -> Result<(), String> {
        crate::profile_span!(Forward);
        for ((v, coefficient), s) in self.fq.iter_mut().zip(&self.coefficient).zip(sq) {
            *v = coefficient * (s - 1.);
        }
        if let Some(fft) = &mut self.fft {
            fft.execute(&self.fq);
            fft.output(&mut self.fr);
        } else {
            for (output, r) in self.fr.iter_mut().zip(&self.r) {
                let mut sum = 0.;
                let mut previous = self.fq[0] * (self.q[0] * r).sin();
                let mut previous_q = self.q[0];
                for (&q, &value) in self.q.iter().zip(&self.fq).skip(1) {
                    let current = value * (q * r).sin();
                    sum += (q - previous_q) * (previous + current) / 2.;
                    previous = current;
                    previous_q = q;
                }
                *output = 2. / PI * sum;
            }
        }
        for ((g, r), f) in self.gr.iter_mut().zip(&self.r).zip(&self.fr) {
            let r_safe = if *r == 0. { 1e-10 } else { *r };
            *g = 1. + f / (4. * PI * r_safe * density);
        }
        if self.fr.iter().chain(&self.gr).any(|v| !v.is_finite()) {
            return Err("Transform: NonFiniteResult".into());
        }
        Ok(())
    }
    pub fn derivatives(
        &mut self,
        sq: &[f64],
        dsq: &[Vec<f64>],
        density: f64,
        drho: &[f64],
    ) -> Result<(), String> {
        crate::profile_span!(Forward);
        let n = dsq.len();
        self.dfq.resize_with(n, || vec![0.; self.q.len()]);
        self.dfr.resize_with(n, || vec![0.; self.r.len()]);
        self.dgr.resize_with(n, || vec![0.; self.r.len()]);
        for (i, coefficient) in self.coefficient.iter().enumerate() {
            self.fq[i] = coefficient * (sq[i] - 1.);
            for (dst, src) in self.dfq.iter_mut().zip(dsq) {
                dst[i] = coefficient * src[i];
            }
        }
        if let Some(fft) = &mut self.fft {
            fft.execute_pair(&self.fq, &self.dfq[0], &mut self.fr, &mut self.dfr[0]);
            for k in 1..n {
                fft.execute(&self.dfq[k]);
                fft.output(&mut self.dfr[k]);
            }
        } else {
            for (out, input) in
                std::iter::once((&mut self.fr, &self.fq)).chain(self.dfr.iter_mut().zip(&self.dfq))
            {
                for (out, r) in out.iter_mut().zip(&self.r) {
                    *out = 2. / PI
                        * self
                            .q
                            .windows(2)
                            .zip(input.windows(2))
                            .map(|(q, f)| {
                                (q[1] - q[0]) * (f[0] * (q[0] * r).sin() + f[1] * (q[1] * r).sin())
                                    / 2.
                            })
                            .sum::<f64>();
                }
            }
        }
        for (i, r) in self.r.iter().enumerate() {
            let r = if *r == 0. { 1e-10 } else { *r };
            let denominator = 4. * PI * r * density;
            self.gr[i] = 1. + self.fr[i] / denominator;
            for (k, drho) in drho.iter().enumerate() {
                self.dgr[k][i] =
                    self.dfr[k][i] / denominator - self.fr[i] / denominator * drho / density;
            }
        }
        if self
            .fr
            .iter()
            .chain(&self.gr)
            .chain(self.dfr.iter().flatten())
            .chain(self.dgr.iter().flatten())
            .any(|v| !v.is_finite())
        {
            return Err("Transform: NonFiniteResult".into());
        }
        Ok(())
    }
}

pub(crate) struct Backward {
    r: Vec<f64>,
    q: Vec<f64>,
    fft: Option<FftStorage>,
    pub iq: Vec<f64>,
    pub diq: Vec<Vec<f64>>,
}
impl Backward {
    pub fn new(r: &[f64], q: &[f64], method: Method) -> Result<Self, String> {
        let fft = match method {
            Method::Integral => None,
            Method::Fft => {
                let dr = r[1] - r[0];
                let dq = q[1] - q[0];
                let target = (PI / (dq * dr)).trunc().max(r.len() as f64);
                if !target.is_finite() || target > 4194304. {
                    return Err("Inverse FFT allocation limit".into());
                }
                let size = (target as usize).next_power_of_two();
                Some(FftStorage::new(size, q, 2. * PI / (size as f64 * dr), dr))
            }
        };
        Ok(Self {
            r: r.to_vec(),
            q: q.to_vec(),
            fft,
            iq: vec![0.; q.len()],
            diq: vec![],
        })
    }
    pub fn evaluate(&mut self, fr: &[f64]) {
        crate::profile_span!(Backward);
        if let Some(fft) = &mut self.fft {
            fft.execute(fr);
            fft.output(&mut self.iq);
            // Match the reference's explicit Q<=0 endpoint branch.
            for (v, q) in self.iq.iter_mut().zip(&self.q) {
                if *q <= 0. {
                    *v = fft.result()[0].im * fft.scale;
                }
            }
        } else {
            for (output, q) in self.iq.iter_mut().zip(&self.q) {
                *output = self
                    .r
                    .windows(2)
                    .zip(fr.windows(2))
                    .map(|(r, f)| {
                        (r[1] - r[0]) * (f[0] * (r[0] * q).sin() + f[1] * (r[1] * q).sin()) / 2.
                    })
                    .sum();
            }
        }
        for (v, q) in self.iq.iter_mut().zip(&self.q) {
            *v = (1. + *v / q) - 1.;
        }
    }
    pub fn derivatives(&mut self, fr: &[f64], dfr: &[Vec<f64>]) {
        crate::profile_span!(Backward);
        self.diq.resize_with(dfr.len(), || vec![0.; self.q.len()]);
        if let Some(fft) = &mut self.fft {
            fft.execute_pair(fr, &dfr[0], &mut self.iq, &mut self.diq[0]);
            for (out, input) in self.diq.iter_mut().zip(dfr).skip(1) {
                fft.execute(input);
                fft.output(out);
            }
            // The reference evaluates the zero-frequency endpoint for Q<=0.
            for (i, q) in self.q.iter().enumerate() {
                if *q <= 0. {
                    self.iq[i] = 0.;
                    for d in &mut self.diq {
                        d[i] = 0.;
                    }
                }
            }
        } else {
            for (out, input) in std::iter::once((&mut self.iq, fr))
                .chain(self.diq.iter_mut().zip(dfr).map(|(a, b)| (a, b.as_slice())))
            {
                for (out, q) in out.iter_mut().zip(&self.q) {
                    *out = self
                        .r
                        .windows(2)
                        .zip(input.windows(2))
                        .map(|(r, f)| {
                            (r[1] - r[0]) * (f[0] * (r[0] * q).sin() + f[1] * (r[1] * q).sin()) / 2.
                        })
                        .sum();
                }
            }
        }
        for (i, q) in self.q.iter().enumerate() {
            self.iq[i] = (1. + self.iq[i] / q) - 1.;
            for d in &mut self.diq {
                d[i] /= q;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn packed_sine_transforms_match_separate_transforms_and_reset_imaginary_input() {
        for scalar in [false, true] {
            for size in [8, 32, 128, 4096, 65536] {
                let plan = if scalar {
                    rustfft::FftPlannerScalar::<f64>::new().plan_fft_inverse(size)
                } else {
                    PLANNER.with(|p| p.borrow_mut().plan_fft_inverse(size))
                };
                let coordinates = [
                    0.,
                    0.14,
                    0.3,
                    (size / 2) as f64 * 0.2,
                    (size - 1) as f64 * 0.2,
                    size as f64,
                ];
                let mut work = FftStorage::with_plan(plan.clone(), &coordinates, 0.2, 0.13);
                let mut separate = FftStorage::with_plan(plan, &coordinates, 0.2, 0.13);
                for count in [size, size / 5, size / 2, 0, size / 2] {
                    let a: Vec<_> = (0..count).map(|i| (i as f64 * 0.7).sin()).collect();
                    let b: Vec<_> = (0..count).map(|i| (i as f64 * 0.27).cos() * 0.01).collect();
                    let (mut oa, mut ob, mut expected) = (vec![0.; 6], vec![0.; 6], vec![0.; 6]);
                    work.execute_pair(&a, &b, &mut oa, &mut ob);
                    for (input, output) in [(&a, &oa), (&b, &ob)] {
                        separate.execute(input);
                        separate.output(&mut expected);
                        for (a, e) in output.iter().zip(&expected) {
                            assert!(
                                (a - e).abs() < 1e-11 * (1. + e.abs()),
                                "{size} {count}: {a} != {e}"
                            );
                        }
                    }
                    work.execute(&a);
                    work.output(&mut oa);
                    separate.execute(&a);
                    separate.output(&mut expected);
                    assert_eq!(oa, expected);
                }
            }
        }
    }
    #[test]
    fn fft_modes_match_inplace_bits_with_changing_real_input_lengths() {
        for scalar in [false, true] {
            for size in [4, 8, 16, 32, 128, 256, 4096, 65536] {
                let plan = if scalar {
                    rustfft::FftPlannerScalar::<f64>::new().plan_fft_inverse(size)
                } else {
                    PLANNER.with(|p| p.borrow_mut().plan_fft_inverse(size))
                };
                let mut work = FftStorage::with_plan(plan.clone(), &[0., 0.1, 100.], 0.2, 1.);
                let allocated = work.buffer.len()
                    + work.scratch.len()
                    + work.output.as_ref().map_or(0, Vec::len);
                assert!(allocated <= size + plan.get_inplace_scratch_len());
                let ptr = (
                    work.buffer.as_ptr(),
                    work.scratch.as_ptr(),
                    work.output.as_ref().map(Vec::as_ptr),
                );
                for count in [size, size / 5, size / 2, 0, size / 2] {
                    let values: Vec<_> = (0..count).map(|i| (i as f64 * 0.7).sin()).collect();
                    let mut expected = vec![Complex::new(0., 0.); size];
                    for (v, x) in expected.iter_mut().zip(&values) {
                        v.re = *x;
                    }
                    plan.process(&mut expected);
                    work.execute(&values);
                    for (i, (a, e)) in work.result().iter().zip(&expected).enumerate() {
                        assert_eq!(
                            (a.re.to_bits(), a.im.to_bits()),
                            (e.re.to_bits(), e.im.to_bits()),
                            "scalar={scalar}, size={size}, count={count}, index={i}"
                        );
                    }
                    assert_eq!(
                        ptr,
                        (
                            work.buffer.as_ptr(),
                            work.scratch.as_ptr(),
                            work.output.as_ref().map(Vec::as_ptr)
                        )
                    );
                    if work.output.is_some() {
                        assert!(work.buffer.iter().all(|v| v.im == 0.));
                        assert!(work.buffer[count..]
                            .iter()
                            .all(|v| *v == Complex::new(0., 0.)));
                    }
                }
            }
        }
    }
    #[test]
    fn forward_reuse_is_exact_and_clears_padding() {
        let q: Vec<_> = (0..201).map(|i| 0.02 + i as f64 * 0.05).collect();
        let r: Vec<_> = (0..101).map(|i| i as f64 * 0.01).collect();
        for method in [Method::Fft, Method::Integral] {
            for lorch in [false, true] {
                let mut work = Forward::new(&q, &r, method, lorch).unwrap();
                let ptr = work.fq.as_ptr();
                for amplitude in [1., 0., -0.5, 2., 0.] {
                    let sq: Vec<_> = q.iter().map(|q| 1. + amplitude * q.sin()).collect();
                    let expected = crate::transform(&q, &sq, &r, 0.066, method, lorch).unwrap();
                    work.evaluate(&sq, 0.066).unwrap();
                    assert_eq!(work.fr, expected.0);
                    assert_eq!(work.gr, expected.1);
                    assert_eq!(ptr, work.fq.as_ptr());
                }
            }
        }
    }
}
