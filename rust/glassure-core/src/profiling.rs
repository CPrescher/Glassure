//! Opt-in inclusive stage timers, compiled out of ordinary/native/WASM builds.
use serde::Serialize;
use std::{
    cell::{Cell, RefCell},
    time::Instant,
};

#[derive(Clone, Copy)]
#[repr(usize)]
pub enum Stage {
    Fit,
    Preparation,
    Residual,
    Normalization,
    Extrapolation,
    SqOptimization,
    Forward,
    Backward,
    FftInput,
    FftKernel,
    FftOutput,
}
const COUNT: usize = 11;
const NAMES: [&str; COUNT] = [
    "fit_total",
    "preparation",
    "residual",
    "normalization",
    "extrapolation",
    "sq_optimization",
    "forward_transform",
    "backward_transform",
    "fft_input",
    "fft_kernel",
    "fft_output",
];
thread_local! { static STATS: RefCell<[(u64,u128);COUNT]> = const { RefCell::new([(0,0);COUNT]) }; }
thread_local! { static FORCE_INPLACE: Cell<bool> = const { Cell::new(false) }; }
/// Diagnostic control for comparing FFT paths in the same profiled binary.
pub fn force_inplace_fft(force: bool) {
    FORCE_INPLACE.with(|v| v.set(force));
}
pub(crate) fn inplace_fft_forced() -> bool {
    FORCE_INPLACE.with(Cell::get)
}
pub struct Span {
    stage: Stage,
    start: Instant,
}
impl Span {
    pub fn new(stage: Stage) -> Self {
        Self {
            stage,
            start: Instant::now(),
        }
    }
}
impl Drop for Span {
    fn drop(&mut self) {
        let elapsed = self.start.elapsed().as_nanos();
        STATS.with(|stats| {
            let mut s = stats.borrow_mut();
            let value = &mut s[self.stage as usize];
            value.0 += 1;
            value.1 += elapsed;
        });
    }
}
#[derive(Serialize)]
pub struct Measurement {
    pub stage: &'static str,
    pub calls: u64,
    pub milliseconds: f64,
    pub percent_fit_time: f64,
}
pub fn reset() {
    STATS.with(|s| *s.borrow_mut() = [(0, 0); COUNT]);
}
pub fn snapshot() -> Vec<Measurement> {
    STATS.with(|stats| {
        let s = stats.borrow();
        let total = s[Stage::Fit as usize].1.max(1) as f64;
        s.iter()
            .enumerate()
            .map(|(i, (calls, ns))| Measurement {
                stage: NAMES[i],
                calls: *calls,
                milliseconds: *ns as f64 / 1e6,
                percent_fit_time: 100. * (*ns as f64) / total,
            })
            .collect()
    })
}
