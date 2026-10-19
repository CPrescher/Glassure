//! Density-fit preparation and owned reusable numerical workspaces.
//! Density/background remain variable; only parameter-independent work is cached.
use crate::{
    corrections::{klein_nishina, soller_dac},
    numeric::{arange, lsq, quadratic_extrapolation_fit, spline_values},
    request::{
        interpolate, validate_pattern, Normalization, NormalizationParameters, Pattern, Request,
        Response,
    },
    scattering::{factors_with_source, mean_weight, Factors},
    sq_optimization::{optimize, SqOptimization},
    workspace::{Backward, Forward},
    Method,
};
use nalgebra::{DMatrix, DVector};
use std::f64::consts::PI;

struct Extrapolation {
    x: Vec<f64>,
    prefix: usize,
    remain: usize,
    fit_count: usize,
    fx: Vec<f64>,
    fy: Vec<f64>,
    s0: f64,
}
impl Extrapolation {
    fn new(q: &[f64], s0: f64, req: &Request) -> Result<Self, String> {
        if !s0.is_finite() || !req.overlap.is_finite() || req.overlap <= 0. {
            return Err("Invalid extrapolation settings".into());
        }
        let step = if req.extrapolation == "step" {
            (q[q.len() - 1] - q[0]) / (q.len() - 1) as f64
        } else {
            q[1] - q[0]
        };
        let mut x = if req.extrapolation == "poly" {
            arange(q[0], 0., -step)?
        } else {
            arange(q[0] - step, -step / 2., -step)?
        };
        x.reverse();
        let cutoff = q[0] + req.overlap;
        let fit_count = q.partition_point(|v| *v < cutoff);
        let mut remain = 0;
        if req.replace && req.extrapolation == "spline" {
            x.extend_from_slice(&q[..fit_count]);
            remain = q.partition_point(|v| *v <= cutoff);
        } else if req.replace && req.extrapolation == "poly" {
            x.extend_from_slice(&q[1..fit_count]);
            remain = q.partition_point(|v| *v <= cutoff);
        }
        let prefix = x.len();
        x.extend_from_slice(&q[remain..]);
        let mut fx = vec![0.];
        fx.extend_from_slice(&q[..fit_count]);
        Ok(Self {
            x,
            prefix,
            remain,
            fit_count,
            fx,
            fy: vec![0.; fit_count + 1],
            s0,
        })
    }
    fn evaluate(
        &mut self,
        q: &[f64],
        sq: &[f64],
        req: &Request,
        y: &mut [f64],
    ) -> Result<(), String> {
        let x = &self.x[..self.prefix];
        let prefix = &mut y[..self.prefix];
        let s0 = self.s0;
        match req.extrapolation.as_str() {
            "step" => prefix.fill(s0),
            "linear" => {
                for (v, x) in prefix.iter_mut().zip(x) {
                    *v = (sq[0] - s0) / q[0] * x + s0;
                }
            }
            "spline" => {
                self.fy[0] = s0;
                self.fy[1..].copy_from_slice(&sq[..self.fit_count]);
                let values = spline_values(&self.fx, &self.fy, x, req.smooth_factor)?;
                prefix.copy_from_slice(&values);
                if let Some(last) = prefix.iter().rposition(|v| *v < s0) {
                    prefix[..last].fill(s0);
                }
            }
            "poly" => {
                let [a, b, c] =
                    quadratic_extrapolation_fit(&q[..self.fit_count], &sq[..self.fit_count], s0)?;
                for (v, x) in prefix.iter_mut().zip(x) {
                    *v = (a * (x - c) + b * (x - c).powi(2) - s0).max(s0);
                }
            }
            _ => return Err("Unknown extrapolation".into()),
        }
        y[self.prefix..].copy_from_slice(&sq[self.remain..]);
        Ok(())
    }
}

enum SqPlan {
    None,
    Fit,
    Iterative {
        r: Vec<f64>,
        forward: Box<Forward>,
        backward: Box<Backward>,
        delta: Vec<f64>,
        ddelta: Vec<Vec<f64>>,
    },
}
impl SqPlan {
    fn new(q: &[f64], req: &Request, method: Method) -> Result<Self, String> {
        let Some(opt) = &req.optimize else {
            return Ok(Self::None);
        };
        if !opt.r_cutoff.is_finite()
            || opt.r_cutoff <= 0.
            || opt.iterations > 1000
            || !opt.attenuation.is_finite()
            || opt.attenuation <= 0.
        {
            return Err("Invalid S(Q) optimization settings".into());
        }
        match opt.method.as_str() {
            "fit" => Ok(Self::Fit),
            "iterative" => {
                let r = arange(0., opt.r_cutoff, req.r_step)?;
                if r.len() < 2 {
                    return Err("Optimization needs at least two low-r points".into());
                }
                let forward = Box::new(Forward::new(q, &r, method, opt.lorch)?);
                let backward = Box::new(Backward::new(&r, q, method)?);
                let delta = vec![0.; r.len()];
                Ok(Self::Iterative {
                    r,
                    forward,
                    backward,
                    delta,
                    ddelta: vec![],
                })
            }
            _ => Err("Unknown S(Q) optimization method".into()),
        }
    }
    fn evaluate(
        &mut self,
        q: &[f64],
        y: &mut [f64],
        rho: f64,
        req: &Request,
        method: Method,
    ) -> Result<(), String> {
        crate::profile_span!(SqOptimization);
        match self {
            Self::None => Ok(()),
            Self::Fit => {
                y.copy_from_slice(&optimize(
                    q,
                    y,
                    rho,
                    req.r_step,
                    method,
                    req.optimize.as_ref().unwrap(),
                )?);
                Ok(())
            }
            Self::Iterative {
                r,
                forward,
                backward,
                delta,
                ..
            } => {
                let SqOptimization {
                    iterations,
                    attenuation,
                    ..
                } = req.optimize.as_ref().unwrap();
                for _ in 0..*iterations {
                    forward.evaluate(y, rho)?;
                    for ((d, r), f) in delta.iter_mut().zip(r.iter()).zip(&forward.fr) {
                        *d = f + 4. * PI * r * rho;
                    }
                    backward.evaluate(delta);
                    for (s, iq) in y.iter_mut().zip(&backward.iq) {
                        *s *= 1. - iq / attenuation;
                    }
                    if y.iter().any(|v| !v.is_finite()) {
                        return Err("S(Q) optimization produced nonfinite values".into());
                    }
                }
                Ok(())
            }
        }
    }
    fn derivatives(
        &mut self,
        y: &mut [f64],
        dy: &mut [Vec<f64>],
        rho: f64,
        drho: &[f64],
        req: &Request,
    ) -> Result<(), String> {
        crate::profile_span!(SqOptimization);
        match self {
            Self::None => Ok(()),
            Self::Fit => unreachable!("Polynomial S(Q) optimization uses numerical derivatives"),
            Self::Iterative {
                r,
                forward,
                backward,
                delta,
                ddelta,
            } => {
                let opt = req.optimize.as_ref().unwrap();
                ddelta.resize_with(dy.len(), || vec![0.; r.len()]);
                for _ in 0..opt.iterations {
                    forward.derivatives(y, dy, rho, drho)?;
                    for (i, r) in r.iter().enumerate() {
                        delta[i] = forward.fr[i] + 4. * PI * r * rho;
                        for (k, d) in ddelta.iter_mut().enumerate() {
                            d[i] = forward.dfr[k][i] + 4. * PI * r * drho[k];
                        }
                    }
                    backward.derivatives(delta, ddelta);
                    for (i, s) in y.iter_mut().enumerate() {
                        let factor = 1. - backward.iq[i] / opt.attenuation;
                        for (k, d) in dy.iter_mut().enumerate() {
                            d[i] = d[i] * factor - *s * backward.diq[k][i] / opt.attenuation;
                        }
                        *s *= factor;
                    }
                }
                Ok(())
            }
        }
    }
}

struct FitPlan {
    indices: Vec<usize>,
    weights: Vec<f64>,
    container: Vec<f64>,
    container_scale: f64,
    matrix: DMatrix<f64>,
    target: DVector<f64>,
}

pub(crate) struct PreparedCalculation<'a> {
    req: &'a Request,
    method: Method,
    q: Vec<f64>,
    data: Vec<f64>,
    background: Vec<f64>,
    sample_tf: Option<Vec<f64>>,
    factors: Factors,
    weight: f64,
    incoherent: Vec<f64>,
    fit: Option<FitPlan>,
    q2: Vec<f64>,
    attenuation: Vec<f64>,
    numerator: f64,
    denominator: f64,
    cached_background: Option<u64>,
    normalization: f64,
    parameters: NormalizationParameters,
    intensity: Vec<f64>,
    normalized: Vec<f64>,
    sq: Vec<f64>,
    n2: Vec<f64>,
    extrapolation: Extrapolation,
    y: Vec<f64>,
    r: Vec<f64>,
    optimization: SqPlan,
    forward: Forward,
    dsq: Vec<Vec<f64>>,
    dy: Vec<Vec<f64>>,
}

pub(crate) struct View<'a> {
    pub q: &'a [f64],
    pub sq: &'a [f64],
    pub r: &'a [f64],
    pub fr: &'a [f64],
    pub gr: &'a [f64],
    pub atomic_density: f64,
    normalization: f64,
    parameters: NormalizationParameters,
}
pub(crate) struct DerivativeView<'a> {
    pub result: View<'a>,
    pub sq: &'a [Vec<f64>],
    pub fr: &'a [Vec<f64>],
    pub gr: &'a [Vec<f64>],
    pub atomic_density: f64,
}
impl View<'_> {
    pub fn owned(&self) -> Response {
        Response {
            sq: Pattern {
                x: self.q.to_vec(),
                y: self.sq.to_vec(),
            },
            fr: Pattern {
                x: self.r.to_vec(),
                y: self.fr.to_vec(),
            },
            gr: Pattern {
                x: self.r.to_vec(),
                y: self.gr.to_vec(),
            },
            normalization: self.normalization,
            atomic_density: self.atomic_density,
            normalization_parameters: self.parameters,
        }
    }
}
impl<'a> PreparedCalculation<'a> {
    pub fn new(req: &'a Request) -> Result<Self, String> {
        crate::profile_span!(Preparation);
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
            || req.q_min < 0.
            || req.q_max <= req.q_min
            || req.r_min < 0.
            || req.r_max <= req.r_min
            || req.r_step <= 0.
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
        if let Some(b) = &req.background {
            validate_pattern(b)?;
        }
        let (mut q, mut data, mut background) = (vec![], vec![], vec![]);
        for (i, (&x, &y)) in req.data.x.iter().zip(&req.data.y).enumerate() {
            if x <= req.q_min || x >= req.q_max {
                continue;
            }
            let b = match &req.background {
                None => 0.,
                Some(b) if b.x.len() == req.data.x.len() => b.y[i],
                Some(b) if x >= b.x[0] && x <= b.x[b.x.len() - 1] => interpolate(b, x),
                Some(_) => continue,
            };
            q.push(x);
            data.push(y);
            background.push(b);
        }
        if q.len() < 2 {
            return Err("Too few points after cropping/background overlap".into());
        }
        let factors = factors_with_source(
            &req.composition,
            req.density,
            &q,
            req.scattering_factor_source,
        )?;
        let weight = mean_weight(&req.composition)?;
        let correction = if req.kn_correction {
            klein_nishina(&q, req.wavelength.ok_or("Wavelength required")?)?
        } else {
            vec![1.; q.len()]
        };
        let mut incoherent = if req.incoherent {
            factors.incoherent.clone()
        } else {
            vec![0.; q.len()]
        };
        let mut sample_tf = None;
        let mut numerator = 0.;
        let mut q2 = vec![];
        let mut attenuation_values = vec![];
        let fit = match &req.normalization {
            Normalization::Integral { attenuation } => {
                if !attenuation.is_finite() || *attenuation < 0. {
                    return Err("Normalization: InvalidValues".into());
                }
                let mut n1 = Vec::with_capacity(q.len());
                for i in 0..q.len() {
                    let square = q[i].powi(2);
                    let decay = (-attenuation * square).exp();
                    q2.push(square);
                    attenuation_values.push(decay);
                    n1.push(square * ((factors.f2[i] + incoherent[i]) * decay) / factors.fm2[i]);
                }
                numerator = crate::trapezoid(&q, &n1);
                None
            }
            Normalization::Fit {
                q_cutoff,
                scaling,
                multiple: _,
                container,
                dac,
            } => {
                if !q_cutoff.is_finite() || !matches!(scaling.as_str(), "squared" | "linear") {
                    return Err("Invalid fit settings".into());
                }
                for (v, c) in incoherent.iter_mut().zip(&correction) {
                    *v *= c;
                }
                let mut cont = match container {
                    None => vec![0.; q.len()],
                    Some(c) => factors_with_source(c, 1., &q, req.scattering_factor_source)?
                        .incoherent
                        .iter()
                        .zip(&correction)
                        .map(|(v, c)| v * c)
                        .collect(),
                };
                if let (Some(dac), Some(_)) = (dac, container) {
                    let (tf, diamond) = soller_dac(
                        &q,
                        req.wavelength.ok_or("Wavelength required for DAC")?,
                        dac.initial_thickness,
                        dac.sample_thickness,
                    )?;
                    sample_tf = Some(tf);
                    for (c, d) in cont.iter_mut().zip(diamond) {
                        *c /= d;
                    }
                }
                let indices: Vec<_> = q
                    .iter()
                    .enumerate()
                    .filter(|(_, v)| **v > *q_cutoff)
                    .map(|(i, _)| i)
                    .collect();
                if indices.is_empty() {
                    return Err("No points above fit cutoff".into());
                }
                let weights: Vec<_> = q
                    .iter()
                    .map(|q| if scaling == "squared" { q * q } else { *q })
                    .collect();
                let scale = indices.iter().map(|i| cont[*i].abs()).fold(0., f64::max);
                let container_scale = if scale == 0. { 1. } else { scale };
                let matrix = DMatrix::zeros(indices.len(), 3);
                let target = DVector::from_iterator(
                    indices.len(),
                    indices
                        .iter()
                        .map(|i| (factors.f2[*i] + incoherent[*i]) * weights[*i]),
                );
                Some(FitPlan {
                    indices,
                    weights,
                    container: cont,
                    container_scale,
                    matrix,
                    target,
                })
            }
        };
        let extrapolation = Extrapolation::new(&q, req.s0.unwrap_or(factors.s0), req)?;
        let r = arange(req.r_min, req.r_max + 0.5 * req.r_step, req.r_step)?;
        if r.len() < 2 {
            return Err("Need at least two r points".into());
        }
        let optimization = SqPlan::new(&extrapolation.x, req, method)?;
        let forward = Forward::new(&extrapolation.x, &r, method, req.lorch)?;
        let n = q.len();
        let ny = extrapolation.x.len();
        Ok(Self {
            req,
            method,
            q,
            data,
            background,
            sample_tf,
            factors,
            weight,
            incoherent,
            fit,
            q2,
            attenuation: attenuation_values,
            numerator,
            denominator: 0.,
            cached_background: None,
            normalization: 0.,
            parameters: NormalizationParameters::default(),
            intensity: vec![0.; n],
            normalized: vec![0.; n],
            sq: vec![0.; n],
            n2: vec![0.; n],
            extrapolation,
            y: vec![0.; ny],
            r,
            optimization,
            forward,
            dsq: vec![],
            dy: vec![],
        })
    }
    pub fn q(&self) -> &[f64] {
        &self.extrapolation.x
    }
    pub fn r(&self) -> &[f64] {
        &self.r
    }
    fn background(&mut self, scale: f64) -> Result<(), String> {
        if self.cached_background == Some(scale.to_bits()) {
            return Ok(());
        }
        if !scale.is_finite() {
            return Err("Invalid calculation ranges".into());
        }
        for i in 0..self.q.len() {
            self.intensity[i] = self.data[i] - scale * self.background[i];
            if let Some(tf) = &self.sample_tf {
                self.intensity[i] *= tf[i];
            }
        }
        match &self.req.normalization {
            Normalization::Integral { .. } => {
                for i in 0..self.q.len() {
                    self.n2[i] =
                        self.q2[i] * self.intensity[i] * self.attenuation[i] / self.factors.fm2[i];
                }
                self.denominator = crate::trapezoid(&self.q, &self.n2);
                if self.denominator == 0. || !self.denominator.is_finite() {
                    return Err("Normalization: SingularNormalization".into());
                }
            }
            Normalization::Fit {
                multiple,
                container,
                ..
            } => {
                let f = self.fit.as_mut().unwrap();
                let n = if !multiple && container.is_none() {
                    let (mut num, mut den) = (0., 0.);
                    for &i in &f.indices {
                        let y = self.intensity[i] * f.weights[i];
                        let v = (self.factors.f2[i] + self.incoherent[i]) * f.weights[i];
                        num += y * v;
                        den += y * y;
                    }
                    if den == 0. {
                        return Err("Singular fit normalization".into());
                    }
                    num / den
                } else {
                    let scale = f
                        .indices
                        .iter()
                        .map(|i| self.intensity[*i].abs())
                        .fold(0., f64::max);
                    let scale = if scale == 0. { 1. } else { scale };
                    for (j, &i) in f.indices.iter().enumerate() {
                        f.matrix[(j, 0)] = f.weights[i] * (self.intensity[i] / scale);
                        f.matrix[(j, 1)] = f.weights[i] * (f.container[i] / f.container_scale);
                        f.matrix[(j, 2)] = f.weights[i] * if *multiple { 1. } else { 0. };
                    }
                    let beta = lsq(&f.matrix, &f.target)?;
                    self.parameters.multiple = -beta[2];
                    self.parameters.n_container = -beta[1] / f.container_scale;
                    self.parameters.residual = (&f.target - &f.matrix * &beta).norm_squared();
                    beta[0] / scale
                };
                self.normalization = n;
                self.parameters.n = n;
                for i in 0..self.q.len() {
                    self.sq[i] = (n * self.intensity[i]
                        - self.parameters.multiple
                        - self.incoherent[i]
                        - f.container[i] * self.parameters.n_container
                        - self.factors.f2[i]
                        + self.factors.fm2[i])
                        / self.factors.fm2[i];
                }
            }
        }
        self.cached_background = Some(scale.to_bits());
        Ok(())
    }
    pub fn analytic(&self, vary_background: bool) -> bool {
        matches!(self.req.extrapolation.as_str(), "step" | "linear")
            && !matches!(self.optimization, SqPlan::Fit)
            && (!vary_background
                || !matches!(&self.req.normalization, Normalization::Fit { multiple, container, .. } if *multiple || container.is_some()))
    }
    pub fn derivatives(
        &mut self,
        density: f64,
        background: f64,
        vary_background: bool,
    ) -> Result<DerivativeView<'_>, String> {
        self.evaluate_impl(density, background, if vary_background { 2 } else { 1 })?;
        Ok(DerivativeView {
            result: self.view(density),
            sq: &self.dy,
            fr: &self.forward.dfr,
            gr: &self.forward.dgr,
            atomic_density: 0.602214129 / self.weight,
        })
    }
    pub fn evaluate(&mut self, density: f64, background: f64) -> Result<View<'_>, String> {
        self.evaluate_impl(density, background, 0)?;
        Ok(self.view(density))
    }
    fn evaluate_impl(
        &mut self,
        density: f64,
        background: f64,
        derivatives: usize,
    ) -> Result<(), String> {
        if !density.is_finite() || density <= 0. {
            return Err("Density must be finite and positive".into());
        }
        let rho = density / self.weight * 0.602214129;
        {
            crate::profile_span!(Normalization);
            self.background(background)?;
            if matches!(self.req.normalization, Normalization::Integral { .. }) {
                self.normalization = (-2. * PI.powi(2) * rho + self.numerator) / self.denominator;
                self.parameters.n = self.normalization;
                for i in 0..self.q.len() {
                    self.normalized[i] =
                        self.normalization * self.intensity[i] - self.incoherent[i];
                    self.sq[i] = (self.normalized[i] - self.factors.f2[i] + self.factors.fm2[i])
                        / self.factors.fm2[i];
                }
                if self.normalized.iter().any(|v| !v.is_finite()) {
                    return Err("Normalization: NonFiniteResult".into());
                }
            }
        }
        let drho = [0.602214129 / self.weight, 0.];
        if derivatives > 0 {
            self.dsq.resize_with(derivatives, || vec![0.; self.q.len()]);
            self.dy.resize_with(derivatives, || vec![0.; self.y.len()]);
            let mut dn = [0., 0.];
            match &self.req.normalization {
                Normalization::Integral { .. } => {
                    dn[0] = -2. * PI.powi(2) * drho[0] / self.denominator;
                    if derivatives == 2 {
                        for i in 0..self.q.len() {
                            self.n2[i] = -self.q2[i] * self.background[i] * self.attenuation[i]
                                / self.factors.fm2[i];
                        }
                        dn[1] = -self.normalization * crate::trapezoid(&self.q, &self.n2)
                            / self.denominator;
                    }
                }
                Normalization::Fit { .. } => {
                    if derivatives == 2 {
                        let f = self.fit.as_ref().unwrap();
                        let (mut da, mut db, mut b) = (0., 0., 0.);
                        for &i in &f.indices {
                            let y = self.intensity[i] * f.weights[i];
                            let dy = -self.background[i] * f.weights[i];
                            da += dy * (self.factors.f2[i] + self.incoherent[i]) * f.weights[i];
                            db += 2. * y * dy;
                            b += y * y;
                        }
                        dn[1] = (da - self.normalization * db) / b;
                    }
                }
            }
            for (k, dsq) in self.dsq.iter_mut().enumerate() {
                for (i, d) in dsq.iter_mut().enumerate() {
                    *d = (dn[k] * self.intensity[i]
                        - if k == 1 {
                            self.normalization * self.background[i]
                        } else {
                            0.
                        })
                        / self.factors.fm2[i];
                }
                let ex = &self.extrapolation;
                for (i, d) in self.dy[k][..ex.prefix].iter_mut().enumerate() {
                    *d = if self.req.extrapolation == "linear" {
                        dsq[0] / self.q[0] * ex.x[i]
                    } else {
                        0.
                    };
                }
                self.dy[k][ex.prefix..].copy_from_slice(&dsq[ex.remain..]);
            }
        }
        {
            crate::profile_span!(Extrapolation);
            self.extrapolation
                .evaluate(&self.q, &self.sq, self.req, &mut self.y)?;
        }
        if derivatives == 0 {
            self.optimization.evaluate(
                &self.extrapolation.x,
                &mut self.y,
                rho,
                self.req,
                self.method,
            )?;
            self.forward.evaluate(&self.y, rho)?;
        } else {
            self.optimization.derivatives(
                &mut self.y,
                &mut self.dy,
                rho,
                &drho[..derivatives],
                self.req,
            )?;
            self.forward
                .derivatives(&self.y, &self.dy, rho, &drho[..derivatives])?;
        }
        if !self.normalization.is_finite() || self.y.iter().any(|v| !v.is_finite()) {
            return Err("Nonfinite normalization".into());
        }
        Ok(())
    }
    fn view(&self, density: f64) -> View<'_> {
        View {
            q: &self.extrapolation.x,
            sq: &self.y,
            r: &self.r,
            fr: &self.forward.fr,
            gr: &self.forward.gr,
            atomic_density: density / self.weight * 0.602214129,
            normalization: self.normalization,
            parameters: self.parameters,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::scattering::{Composition, Source};

    #[test]
    fn analytic_pipeline_matches_central_differences_and_primal() {
        let q: Vec<_> = (0..110).map(|i| 0.12 + i as f64 * 0.1).collect();
        let mut req = Request::new(
            Pattern {
                x: q.clone(),
                y: q.iter().map(|q| 100. + 3. * q.sin() + q).collect(),
            },
            Composition::Formula("Mg2SiO4".into()),
            2.9,
        )
        .unwrap();
        req.background = Some(Pattern {
            x: q.clone(),
            y: q.iter().map(|q| 2. + q.cos()).collect(),
        });
        req.q_min = 0.;
        req.q_max = 11.;
        req.r_min = 0.;
        req.r_max = 2.;
        req.r_step = 0.02;
        req.kn_correction = true;
        req.wavelength = Some(0.29);
        for source in [Source::Hajdu, Source::BrownHubbell, Source::Xraylib] {
            req.scattering_factor_source = source;
            for norm in 0..3 {
                req.normalization = if norm == 0 {
                    Normalization::Integral { attenuation: 0.001 }
                } else {
                    Normalization::Fit {
                        q_cutoff: 3.,
                        scaling: "squared".into(),
                        multiple: norm == 2,
                        container: (norm == 2).then(|| Composition::Formula("C".into())),
                        dac: (norm == 2).then_some(crate::request::Dac {
                            initial_thickness: 40.,
                            sample_thickness: 20.,
                        }),
                    }
                };
                for extrap in ["step", "linear"] {
                    req.extrapolation = extrap.into();
                    for method in ["fft", "integral"] {
                        req.transform = method.into();
                        for opt in [false, true] {
                            req.lorch = opt;
                            req.optimize = opt.then_some(SqOptimization {
                                method: "iterative".into(),
                                r_cutoff: 0.6,
                                iterations: 3,
                                lorch: true,
                                attenuation: 1.2,
                            });
                            let mut work = PreparedCalculation::new(&req).unwrap();
                            for vary in [false, true] {
                                if norm == 2 && vary {
                                    assert!(!work.analytic(vary));
                                    continue;
                                }
                                assert!(work.analytic(vary));
                                for (rho, bg) in [(2.9, 0.98), (3.1, 1.02), (2.9, 0.98)] {
                                    let d = work.derivatives(rho, bg, vary).unwrap();
                                    let primal = d.result.owned();
                                    let derivatives = [d.sq.to_vec(), d.fr.to_vec(), d.gr.to_vec()];
                                    let expected = work.evaluate(rho, bg).unwrap().owned();
                                    for (a, e) in [
                                        (&primal.sq.y, &expected.sq.y),
                                        (&primal.fr.y, &expected.fr.y),
                                        (&primal.gr.y, &expected.gr.y),
                                    ] {
                                        for (a, e) in a.iter().zip(e) {
                                            assert!(
                                                (a - e).abs() < 2e-10 * (1. + e.abs()),
                                                "Primal {a} != {e}"
                                            );
                                        }
                                    }
                                    for k in 0..if vary { 2 } else { 1 } {
                                        let h = 2e-5 * if k == 0 { rho } else { bg };
                                        let a = work
                                            .evaluate(
                                                rho + if k == 0 { h } else { 0. },
                                                bg + if k == 1 { h } else { 0. },
                                            )
                                            .unwrap()
                                            .owned();
                                        let b = work
                                            .evaluate(
                                                rho - if k == 0 { h } else { 0. },
                                                bg - if k == 1 { h } else { 0. },
                                            )
                                            .unwrap()
                                            .owned();
                                        for ((name, ap, bp), deriv) in [
                                            ("sq", a.sq, b.sq),
                                            ("fr", a.fr, b.fr),
                                            ("gr", a.gr, b.gr),
                                        ]
                                        .into_iter()
                                        .zip(&derivatives)
                                        {
                                            let numerical: Vec<_> =
                                                ap.y.iter()
                                                    .zip(bp.y)
                                                    .map(|(a, b)| (a - b) / (2. * h))
                                                    .collect();
                                            let scale = numerical
                                                .iter()
                                                .map(|v| v.abs())
                                                .fold(1., f64::max);
                                            let error = numerical
                                                .iter()
                                                .zip(&deriv[k])
                                                .map(|(a, b)| (a - b).abs())
                                                .fold(0., f64::max);
                                            assert!(error/scale < 2e-7, "source={source:?} norm={norm} extrap={extrap} method={method} opt={opt} k={k} {name}: {error}/{scale}");
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    fn same(actual: &Response, expected: &Response) {
        for (name, a, e) in [
            ("sq", &actual.sq, &expected.sq),
            ("fr", &actual.fr, &expected.fr),
            ("gr", &actual.gr, &expected.gr),
        ] {
            for (axis, a, e) in [("x", &a.x, &e.x), ("y", &a.y, &e.y)] {
                assert_eq!(a.len(), e.len());
                for (i, (a, e)) in a.iter().zip(e).enumerate() {
                    assert_eq!(a.to_bits(), e.to_bits(), "{name}.{axis}[{i}]: {a} != {e}");
                }
            }
        }
        assert_eq!(
            actual.normalization.to_bits(),
            expected.normalization.to_bits()
        );
        assert_eq!(
            actual.atomic_density.to_bits(),
            expected.atomic_density.to_bits()
        );
        assert_eq!(
            serde_json::to_string(&actual.normalization_parameters).unwrap(),
            serde_json::to_string(&expected.normalization_parameters).unwrap()
        );
    }

    #[test]
    fn prepared_pipeline_matches_reference_and_resets_between_parameters() {
        let q: Vec<_> = (1..121).map(|i| (i as f32 * 0.1) as f64).collect();
        let data = Pattern {
            y: q.iter().map(|q| 100. + 3. * q.sin() + q).collect(),
            x: q,
        };
        // Different background length exercises interpolation and overlap.
        let bq: Vec<_> = (0..65).map(|i| i as f64 * 0.2).collect();
        let bkg = Pattern {
            y: bq.iter().map(|q| 2. + q.cos()).collect(),
            x: bq,
        };
        let mut req = Request::new(data, Composition::Formula("Mg2SiO4".into()), 2.9).unwrap();
        req.background = Some(bkg);
        req.q_min = 0.4;
        req.q_max = 11.;
        req.r_min = 1e-13;
        req.r_max = 2.;
        req.r_step = 0.02;
        req.overlap = 0.6;
        req.lorch = true;
        req.kn_correction = true;
        req.wavelength = Some(0.29);
        for source in [Source::Hajdu, Source::BrownHubbell, Source::Xraylib] {
            for norm in 0..3 {
                req.scattering_factor_source = source;
                req.normalization = if norm == 0 {
                    Normalization::Integral { attenuation: 0.001 }
                } else {
                    Normalization::Fit {
                        q_cutoff: 3.,
                        scaling: if norm == 1 {
                            "linear".into()
                        } else {
                            "squared".into()
                        },
                        multiple: norm == 2,
                        container: if norm == 2 {
                            Some(Composition::Formula("C".into()))
                        } else {
                            None
                        },
                        dac: if norm == 2 {
                            Some(crate::request::Dac {
                                initial_thickness: 40.,
                                sample_thickness: 20.,
                            })
                        } else {
                            None
                        },
                    }
                };
                for extrapolation in ["step", "linear", "spline", "poly"] {
                    req.extrapolation = extrapolation.into();
                    req.replace = matches!(extrapolation, "spline" | "poly");
                    for method in ["fft", "integral"] {
                        req.transform = method.into();
                        for opt in ["iterative", "fit"] {
                            req.optimize = Some(SqOptimization {
                                method: opt.into(),
                                r_cutoff: 0.6,
                                iterations: 2,
                                lorch: true,
                                attenuation: 1.,
                            });
                            let mut work = PreparedCalculation::new(&req).unwrap();
                            let pointers = (
                                work.intensity.as_ptr(),
                                work.sq.as_ptr(),
                                work.y.as_ptr(),
                                work.forward.fr.as_ptr(),
                            );
                            for (density, background) in [(2.9, 0.98), (3.1, 1.02), (2.9, 0.98)] {
                                let mut reference = req.clone();
                                reference.density = density;
                                reference.background_scale = background;
                                let expected = crate::request::calculate(reference);
                                let actual =
                                    work.evaluate(density, background).map(|view| view.owned());
                                match (actual, expected) {
                                    (Ok(actual), Ok(expected)) => same(&actual, &expected),
                                    (Err(actual), Err(expected)) => assert_eq!(actual, expected),
                                    (actual, expected) => panic!(
                                        "Prepared/reference success differs: {} vs {}",
                                        actual.is_ok(),
                                        expected.is_ok()
                                    ),
                                }
                                assert_eq!(
                                    pointers,
                                    (
                                        work.intensity.as_ptr(),
                                        work.sq.as_ptr(),
                                        work.y.as_ptr(),
                                        work.forward.fr.as_ptr()
                                    )
                                );
                            }
                        }
                    }
                }
            }
        }
    }
}
