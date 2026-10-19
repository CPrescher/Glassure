# Density fitting, corrections and multicore batches

This tutorial extends the fixed-density analysis to density refinement with a
fixed or fitted background multiplier. It uses the same ambient Mg₂SiO₄ files,
but changes the analysis settings deliberately: Brown–Hubbell factors,
Q_max = 20 Å⁻¹, linear low-Q extrapolation and three S(Q)-optimization iterations.
Use matching settings when comparing its results with the first tutorial.

The example illustrates the numerical procedure on measured data. Its fitted
density is **not a physically validated Mg₂SiO₄ density**. In particular, the
joint fit reaches a background bound. That is a diagnostic to investigate,
not evidence that the bound or the density is physically correct.

## Run the complete example

From the repository root:

```sh
cargo run --locked --release -p glassure-core --example density_fitting -- rust/glassure-core/tests/data/Mg2SiO4_ambient.xy rust/glassure-core/tests/data/Mg2SiO4_ambient_bkg.xy target/density-tutorial
```

The program saves initial/fitted curves, fit diagnostics, reusable requests and
ordered batch results. It checks that recalculation with fitted parameters
reproduces the returned curves and that serial/multicore jobs agree exactly.
The following stages form the body of a fallible `main` function; `data_file`,
`background_file` and `output_dir` are paths supplied by the caller.

```rust
use glassure_core::{
    corrections::klein_nishina,
    density::{optimize_density, DensityRequest},
    parallel::{Executor, Item, Job, JobOutput},
    pattern::Pattern,
    request::{calculate, Dac, Normalization, Request},
    scattering::{Composition, Source},
    SqOptimization,
};
use std::{path::Path, time::Instant};
```

## 1. Prepare the measurement and starting values

Keep the measured intensity and background separately. The outer fit varies
`Request::density` in g/cm³ and, optionally, the dimensionless background scale
in `data - background_scale * background`. Do not subtract a scaled background
before also passing it as `request.background`.

```rust
let mut request = Request::new(
    Pattern::from_file(data_file, 0)?,
    Composition::Formula("Mg2SiO4".into()),
    2.7, // starting mass density in g/cm³, not a reference answer
)?;
request.background = Some(Pattern::from_file(background_file, 0)?);
request.background_scale = 1.1;
request.q_min = 1.0; // Å⁻¹; strict crop
request.q_max = 20.0;
request.r_min = 1e-10; // Å; avoid division at exactly zero
request.r_max = 10.0;
request.r_step = 0.01;
request.scattering_factor_source = Source::BrownHubbell;
request.normalization = Normalization::Fit {
    q_cutoff: 5.0,
    scaling: "squared".into(),
    multiple: false,
    container: None,
    dac: None,
};
request.transform = "fft".into();
request.extrapolation = "linear".into();
request.lorch = false;
```

The starting density 2.7 g/cm³ is an estimate, not a target or constraint.
Atomic density conversion is handled internally. Match background grids before
submitting the request: equal-length patterns are combined by index; unequal
lengths are interpolated over their common domain.

## 2. Set the corrections before fitting

The sample header records wavelength 1.908 × 10⁻¹¹ m, or 0.1908 Å.
Klein–Nishina scales the sample's incoherent contribution in **fit normalization**;
it is not a multiplier of the whole measured intensity. The integral-normalization
branch follows Python and does not apply that correction. Incoherent subtraction
is enabled explicitly here.

```rust
// File header: wavelength 1.908e-11 m = 0.1908 Å.
request.wavelength = Some(0.1908);
request.kn_correction = true;
request.incoherent = true;
request.optimize = Some(SqOptimization {
    method: "iterative".into(),
    r_cutoff: 1.4, // Å, below the first physical pair peak
    iterations: 3,
    lorch: false,
    attenuation: 1.0,
});
let initial = calculate(request.clone())?;
```

Iterative S(Q) optimization uses the absence of physical pairs below 1.4 Å.
Both that cutoff and the fitting interval must stay below real pair peaks.
Keep Lorch disabled here so damping and peak broadening do not change the
low-r fitting objective. If enabled, final-transform Lorch also affects the fit;
the optimizer's own `lorch` setting is a separate choice.

All of these settings remain fixed while density/background change. Prepared
scattering factors, correction arrays and FFT buffers are reused within each fit.
The supported fit-normalization path uses analytic derivatives; other supported
combinations fall back to numerical derivatives without changing the API.

## 3. First fit density with background fixed

Start by inspecting a one-parameter fit before allowing correlated parameters
to move together. `"lsq"` selects bounded trust-region reflective least squares
(TRF). The current API's density bounds are 1e-12–100 g/cm³; custom density bounds
are not fields of `DensityRequest`.

```rust
let fixed_request = DensityRequest {
    calculation: request.clone(),
    method: "gr".into(),
    min_range: Some([0.1, 1.3]), // strict r interval in Å
    vary_background: false,
    background_limits: [0.9, 1.1], // unused for the fixed-background fit
    algorithm: "lsq".into(),       // bounded trust-region reflective least squares
    max_evaluations: 500,
};
let fixed = optimize_density(fixed_request.clone())?;
```

The selected objective is explicitly `method = "gr"` with 0.1 < r < 1.3 Å.
The minimized sum of squares is `Σ [Δr × g(r_i)]²` on that strict interval.
It is not normalized by experimental uncertainties, so its value is not a
statistical reduced chi-square.

| Objective | Residual before multiplication by grid spacing | Interval unit |
| --- | --- | --- |
| `gr` | g(r) | Å |
| `fr` | F(r) + 4πρr, with ρ in atoms/Å³ | Å |
| `sq` | Optimized S(Q) minus the initial unoptimized reference | Å⁻¹ |

For `sq`, the reference is generated at the starting settings. It is not an
independent measured target. Changing objective or interval can change the
fitted density; use a suitable reference/calibration when interpreting it.

## 4. Fit density and background together

Clone the original fit request rather than implicitly adopting the result of
the fixed-background fit. Here both fits start at density 2.7 and scale 1.1.
`background_limits` are **multipliers of the starting background scale**.
They are not absolute bounds and do not move during optimization.

```rust
let mut joint_request = fixed_request.clone();
joint_request.vary_background = true;
// Relative to the STARTING scale 1.1: absolute bounds [0.99, 1.21].
joint_request.background_limits = [0.9, 1.1];
let joint = optimize_density(joint_request.clone())?;
let background_bounds = joint_request
    .background_limits
    .map(|v| v * request.background_scale);
let at_background_bound = background_bounds
    .iter()
    .any(|bound| (joint.background_scale - bound).abs() < 1e-6);
println!(
    "density={:.8} g/cm³, background={:.8}, at_bound={}, SSE={:.8e}, evaluations={}, termination={}",
    joint.density, joint.background_scale, at_background_bound,
    joint.sum_squared_residuals, joint.evaluations, joint.termination,
);
// The input settings remain available; the result contains the fitted PDF.
assert_eq!(joint_request.calculation.density, 2.7);
assert_eq!(joint_request.calculation.background_scale, 1.1);
```

For these files/settings, the joint solution is approximately 3.76142 g/cm³
with background scale 1.21, at the upper bound. The example reports this
explicitly. Revisit the background measurement, Q/extrapolation choices and
objective interval before interpreting that result; widening bounds merely
to obtain a preferred density is not a validation procedure.

Inspect `success`, `termination`, `evaluations`, `sum_squared_residuals`,
`density_error`, `background_error` and `error_kind`. Evaluation counts are
residual evaluations, not FFTs or iterations. The budget includes derivative
and error-estimation work where required; nonconvergence/exhaustion returns
`Err`. `?` propagates that failure instead of presenting a last iterate as a fit.

With `lsq`, errors are local conditional standard errors when identifiable;
`None` means unidentified. Boundary solutions and density/background correlation
limit their interpretation, and they do not include uncertainty in background,
composition, geometry or analysis choices. Do not read a bound-limited standard
error as a symmetric experimental confidence interval.

## 5. Use the result explicitly

`optimize_density` returns fitted parameters and final curves without modifying
your original request. Use `joint.result` directly, or copy both fitted values
into a new request for subsequent calculations:

```rust
let mut fitted_request = request.clone();
fitted_request.density = joint.density;
fitted_request.background_scale = joint.background_scale;
let recalculated = calculate(fitted_request.clone())?;
assert_eq!(recalculated.gr.x, joint.result.gr.x);
for (a, b) in recalculated.gr.y.iter().zip(&joint.result.gr.y) {
    assert!((a - b).abs() < 1e-8 + 1e-8 * b.abs());
}
```

Updating density alone would lose the fitted background correction.

## 6. Run independent fits on native CPU cores

Keep an `Executor` and reuse it across batches. This example compares identical
jobs in serial and on an automatically sized native Rayon pool. It varies only
the starting density, so the runs test sensitivity to initial guesses for one
measurement; they are not independent experimental replicates.
Close agreement between starts checks numerical stability for those starts;
it does not establish a global minimum or physical validity.

```rust
// Here the independent jobs are different initial density guesses for one
// measurement. For a sample series, provide each sample's own calculation.
let starts = [2.4, 2.7, 3.0, 3.3];
let jobs: Vec<_> = starts
    .iter()
    .map(|density| {
        let mut fit = joint_request.clone();
        fit.calculation.density = *density;
        // Keep background starts equal so all jobs have identical absolute bounds.
        Job::Density(fit)
    })
    .collect();
let serial_executor = Executor::new(1)?;
let multicore_executor = Executor::new(0)?; // available CPUs, up to 64
let started = Instant::now();
let serial = serial_executor.batch(jobs.clone())?;
let serial_seconds = started.elapsed().as_secs_f64();
let started = Instant::now();
let multicore = multicore_executor.batch(jobs)?;
let multicore_seconds = started.elapsed().as_secs_f64();
// Both reports retain input order. A batch-level Ok can contain item errors.
for (index, item) in multicore.items.iter().enumerate() {
    match item {
        Item::Success { output } => match output.as_ref() {
            JobOutput::Density(fit) => println!(
                "start={} -> density={:.8}, background={:.8}",
                starts[index], fit.density, fit.background_scale,
            ),
            JobOutput::Calculate(_) => unreachable!("Only density jobs were submitted"),
        },
        Item::Error { operation, error } => {
            return Err(format!("Job {index} ({operation}): {error}").into());
        }
    }
}
```

The example's timing includes batch execution and owned-job handling, while pool
creation is outside the timed region. It is an illustrative timing, not a stable
speedup benchmark; use repeated warm runs and realistic batch sizes for performance
claims. A small batch can be slower with more threads.

Each individual fit is sequential. Parallelism distributes **independent fits**,
retains input order and records failures per item. Always inspect `Item::Error`,
even when `batch()` returns `Ok`. Each job owns its settings/data; cloning requests
copies arrays. Reuse the executor, avoid nested process/thread pools and choose
an explicit thread count such as `Executor::new(4)` when needed. The limit is
64 threads and 1024 jobs per call.

For a sample series, replace each job's calculation with that sample's measured
patterns and metadata. For systematic overrides, `Executor::sweep` with
`Job::Density` accepts starting density/background, Q_max and r_cutoff values.
Changing the background start also changes its absolute bounds; use explicit
jobs with adjusted relative limits if bounds must stay identical.

### Browser/WASM execution

The numerical fitter and corrections also compile to WASM. This native example
uses filesystem I/O and `Instant`; a browser instead parses uploads with
`Pattern::from_xy_text`, loads independent WASM instances in Web Workers and
uses browser timing APIs. Ordinary WASM `Executor::new(0)`/`new(1)` is serial;
counts above one return an error. A Web Worker pool provides browser multicore
scheduling; compiling the core does not create that pool automatically.

## 7. Save curves, diagnostics and reusable settings

Preserve the initial settings alongside the fitted result so the analysis can
be reproduced. The fitted request is suitable for a subsequent calculation;
`fit-request.json` retains the fit configuration and original starting values.

```rust
std::fs::create_dir_all(output_dir)?;
for (name, result) in [
    ("initial", &initial),
    ("fixed", &fixed.result),
    ("joint", &joint.result),
] {
    result.sq.save(output_dir.join(format!("{name}-sq.xy")))?;
    result.fr.save(output_dir.join(format!("{name}-fr.xy")))?;
    result.gr.save(output_dir.join(format!("{name}-gr.xy")))?;
}
std::fs::write(
    output_dir.join("fit-request.json"),
    serde_json::to_vec_pretty(&joint_request)?,
)?;
std::fs::write(
    output_dir.join("fitted-request.json"),
    serde_json::to_vec_pretty(&fitted_request)?,
)?;
std::fs::write(
    output_dir.join("fit-result.json"),
    serde_json::to_vec_pretty(&joint)?,
)?;
std::fs::write(
    output_dir.join("batch-result.json"),
    serde_json::to_vec_pretty(&multicore)?,
)?;
```

The native CLI can consume these without Python:

```sh
glassure density target/density-tutorial/fit-request.json target/density-tutorial/refit.json
glassure pdf target/density-tutorial/fitted-request.json target/density-tutorial/recalculated.json
```

The full program additionally writes `analysis.json`, including both fits,
serial/multicore reports, start values, absolute background bounds and timings.
Fitted curves and parameter agreement are checked against an explicitly selected
Python reference by the maintainer audit.

## 8. Adapt corrections for a DAC experiment

For your **own DAC measurement**, this helper enables constant multiple-scattering
and carbon-container incoherent terms in high-Q normalization, plus the Soller/DAC
geometry correction. These inner linear coefficients are re-estimated at each
outer density/background trial. The background scale is a separate parameter.

```rust
// Call with your own DAC measurement and measured geometry.
fn configure_dac(
    mut request: Request,
    wavelength: f64,        // Å
    initial_thickness: f64, // µm, when background was measured
    sample_thickness: f64,  // µm, current sample thickness
) -> Request {
    request.wavelength = Some(wavelength);
    request.kn_correction = true;
    request.normalization = Normalization::Fit {
        q_cutoff: 5.0,
        scaling: "squared".into(),
        multiple: true,
        container: Some(Composition::Formula("C".into())),
        dac: Some(Dac {
            initial_thickness,
            sample_thickness,
        }),
    };
    request
}
```

Call this helper on a request containing your DAC data, then place that request
in the same `DensityRequest` shown above. Supply measured wavelength and
thicknesses, with `0 < sample_thickness < initial_thickness`.
`Dac` thicknesses are in **µm**; the general `SollerMap` geometry API uses **mm**.
Both container composition and wavelength are required for this DAC path.

The DAC correction uses Glassure's default slit geometry. For another instrument,
construct a `corrections::SollerMap` with its measured `SollerGeometry` and apply
the appropriate transfer functions in your preprocessing. The carbon term
models incoherent container scattering; it does not remove diamond Bragg peaks
or provide a general absorption correction. Constant multiple scattering is
also an approximation, not a full scattering simulation.

The example only constructs a DAC configuration to check this helper. It does
**not** apply fictitious DAC geometry to the ambient measurement. Verify these
corrections against your instrument and sample before interpreting fitted values.

## Intermediate results

```{raw} html
:file: ../rust/glassure-core/docs/density_fitting.svg
```
