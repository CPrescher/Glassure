# A complete analysis, step by step

This tutorial follows the workflow of Glassure's Python API quickstart on the
same ambient Mg₂SiO₄ measurement and background. It shows the individual Rust
operations and their intermediate patterns, then expresses the same calculation
with the high-level API. The density is an input estimate throughout this
analysis; no density fit is performed.

## Run the complete program

The complete source is the crate's `examples/full_analysis.rs`. From the Glassure
repository root, run it with the bundled dataset:

```sh
cargo run --locked --release -p glassure-core --example full_analysis -- rust/glassure-core/tests/data/Mg2SiO4_ambient.xy rust/glassure-core/tests/data/Mg2SiO4_ambient_bkg.xy target/full-analysis
```

It writes every intermediate pattern as a two-column XY file, plus `analysis.json`
with the chosen settings and numerical diagnostics. For your own application,
add `glassure-core` as a dependency and put the snippets below inside a fallible
`main` function. `data_file` and `background_file` are paths to your input files,
and `output_dir` is a directory for exported curves. A native filesystem example
is shown here; WASM callers load uploaded text with `Pattern::from_xy_text`.

These imports cover the complete pipeline:

```rust
use glassure_core::{
    functions::{calculate_fr, calculate_gr, calculate_sq, normalize_fit},
    numeric::arange,
    pattern::Pattern,
    request::{calculate, Normalization, Request},
    scattering::{atomic_density, factors_with_source, Composition, Source},
    sq_optimization::optimize,
    Method, SqOptimization,
};
use std::path::Path;
```

## 1. Load the sample and background

The input x axis is already Q in Å⁻¹. Loading an XY/CHI file does not automatically
convert a two-theta axis to Q. Use `functions::two_theta_to_q` first if your file
contains angles. The example files contain Q/intensity columns and `#` headers.

```rust
let measured = Pattern::from_file(data_file, 0)?;
let background = Pattern::from_file(background_file, 0)?;
```

Plot the original measurement and the scaled background together before
subtracting them. Their coordinate grids must be compatible: equal-length
patterns are combined by index, while other lengths are interpolated over the
common domain. This dataset has aligned grids.

## 2. Subtract background and choose the measured Q range

The background multiplier is explicit. `combine(&background, -scale)` returns
a new pattern without modifying either input. `limit` selects a strict interval:
both endpoints are excluded. The example uses the Python quickstart's background
scale 1.1 and Q range 0–16 Å⁻¹; choose values appropriate to your own experiment.

```rust
let background_scale = 1.1;
let scaled_background = background.scale(background_scale)?;
let sample = measured.combine(&background, -background_scale)?;
// Q in Å⁻¹; strict bounds
let sample = sample.limit(0.0, 16.0)?;
```

No low-Q data have been invented at this point. The measured structure factor
will be calculated on this cropped grid before extrapolation is introduced.

## 3. Define composition, density and scattering factors

Composition amounts are atomic amounts, not weight fractions. `mass_density` is
in g/cm³, while the transform/optimization functions need number density `rho`
in atoms/Å³. This example uses the notebook's 2.7 g/cm³ input estimate and Hajdu
scattering factors. The high-level Rust constructor defaults to Brown–Hubbell,
so we select the source explicitly in both versions of the analysis.

```rust
let composition = Composition::Formula("Mg2SiO4".into());
let mass_density = 2.7; // g/cm³: an input estimate, not a fitted result
let rho = atomic_density(&composition, mass_density)?; // atoms/Å³
let source = Source::Hajdu;
let factors = factors_with_source(&composition, mass_density, &sample.x, source)?;
// factors.f2 = <f²>; factors.fm2 = <f>²; these are different quantities.
```

`factors.f2` is the atomic-fraction mean of squared amplitudes, ⟨f²⟩. `factors.fm2`
is the squared mean amplitude, ⟨f⟩². Using one in place of the other changes S(Q)
for a multicomponent material. `factors.incoherent` is the mixture's incoherent
intensity on the same Q grid.

## 4. Normalize the intensity

The high-Q fit compares `n * sample` with ⟨f²⟩ plus incoherent scattering above
5 Å⁻¹. `"squared"` weights fit residuals by Q². Multiple scattering and additional
container terms are disabled here; they can be enabled when the experiment
requires them.

```rust
let (parameters, normalized) = normalize_fit(
    &sample,
    &factors.f2,
    Some(&factors.incoherent),
    5.0,       // fit only Q > 5 Å⁻¹
    "squared", // multiply fit residuals by Q²
    false,     // no constant multiple-scattering term in this example
    None,      // no additional container contribution
)?;
let normalized_total = sample.scale(parameters.n)?;
// normalized already has incoherent scattering subtracted; do not subtract twice.
```

`normalized_total` is useful for plotting the fitted total intensity against
⟨f²⟩ + incoherent scattering. **The returned `normalized` pattern already has
the incoherent contribution subtracted.** Pass it directly into `calculate_sq`;
subtracting the incoherent array a second time would be incorrect. Inspect the
fit over the measured high-Q range rather than judging it from the multiplier
alone. The simple fit path does not populate `parameters.residual`; its zero
default is not evidence of an exact fit.

## 5. Calculate S(Q), then extend towards zero

The structure-factor conversion is
`S(Q) = [I_coherent(Q) - ⟨f²⟩ + ⟨f⟩²] / ⟨f⟩²`.
Keep the measured and extrapolated versions separately so you can inspect the
effect of the assumed low-Q behavior.

```rust
let sq_measured = calculate_sq(&normalized, &factors.f2, &factors.fm2)?;
let sq_extended = sq_measured.extend_to(0.0, factors.s0)?;
```

`factors.s0 = 1 - ⟨f(0)²⟩/⟨f(0)⟩²` is the mixture convention used by Glassure;
it may be negative for a multicomponent sample. This is not a measured low-Q
signal or a compressibility determination. The example uses a constant extension
towards the grid point nearest zero, which need not be exactly zero. Linear,
spline and polynomial alternatives are available in `functions::extrapolate`.

## 6. Transform the unoptimized structure factor

Choose the real-space grid and the transform method explicitly. The example uses
FFT for both the final transform and the later iterative correction. This avoids
mixing the Python notebook's default direct final transform with its default FFT
optimizer. Use matching choices when comparing implementations.

```rust
let r_step = 0.01; // Å
let r = arange(1e-10, 10.0 + 0.5 * r_step, r_step)?;
let method = Method::Fft;
let fr_unoptimized = calculate_fr(&sq_extended, &r, method, false)?;
let gr_unoptimized = calculate_gr(&fr_unoptimized, rho)?;
```

The grid begins at 1e-10 Å to avoid a division at r = 0. F(r) has units Å⁻² and
`g(r) = 1 + F(r)/(4πρr)` is dimensionless. The near-zero numerical endpoint is
not a physical pair distance. A limited Q range produces termination artifacts,
which can be inspected in `fr_unoptimized` and `gr_unoptimized`.

## 7. Correct low-r artifacts in S(Q)

The iterative correction uses the absence of physical pairs below `r_cutoff`.
Select that cutoff below the first physical pair peak; it is not a parameter to
increase until the plotted curve merely looks smooth. Keep the original S(Q)
and g(r) for comparison with the corrected results.

```rust
let optimization = SqOptimization {
    method: "iterative".into(),
    r_cutoff: 1.4, // Å; choose below the first physical pair peak
    iterations: 5,
    lorch: false, // modification during optimization is a separate choice
    attenuation: 1.0,
};
let sq_optimized = Pattern::new(
    sq_extended.x.clone(),
    optimize(
        &sq_extended.x,
        &sq_extended.y,
        rho,
        r_step,
        method,
        &optimization,
    )?,
)?;
let fr_optimized = calculate_fr(&sq_optimized, &r, method, false)?;
let gr_optimized = calculate_gr(&fr_optimized, rho)?;
```

The example performs five iterations with a 1.4 Å cutoff, following the Python
quickstart. Large changes to measured S(Q), or a need for many iterations, are
reasons to revisit experimental corrections and normalization. This numerical
correction does not replace those steps.

## 8. Compare with Lorch modification

Lorch modification suppresses termination ripples by damping high-Q information.
It also broadens real-space peaks. Compare the same optimized S(Q) with and
without that final-transform modification:

```rust
let fr_lorch = calculate_fr(&sq_optimized, &r, method, true)?;
let gr_lorch = calculate_gr(&fr_lorch, rho)?;
```

The optimizer's `optimization.lorch` and the final `calculate_fr(..., true)` are
separate settings. Here only the final transform uses Lorch, so differences
between `gr_optimized` and `gr_lorch` isolate its effect.

## 9. Express the same analysis with the high-level API

Once the choices are understood, `request::calculate` performs the same pipeline
in one call. Set all relevant options explicitly to reproduce the manual stages:

```rust
let mut request = Request::new(measured.clone(), composition.clone(), mass_density)?;
request.background = Some(background.clone());
request.background_scale = background_scale;
request.q_min = 0.0;
request.q_max = 16.0;
request.scattering_factor_source = source;
request.normalization = Normalization::Fit {
    q_cutoff: 5.0,
    scaling: "squared".into(),
    multiple: false,
    container: None,
    dac: None,
};
request.extrapolation = "step".into();
request.r_min = 1e-10;
request.r_max = 10.0;
request.r_step = r_step;
request.transform = "fft".into();
request.optimize = Some(optimization.clone());
request.lorch = true;
let automatic = calculate(request)?;
```

`automatic.sq` corresponds to `sq_optimized`; `automatic.fr` and `automatic.gr`
correspond to `fr_lorch` and `gr_lorch`. The executable example checks all three
against the manual calculation with numerical tolerances. The automatic API
does not implicitly select the notebook's Hajdu source or normalization cutoff.

For the bundled files, the calculation uses 2630 measured-Q points and extends
them to 2850 points; the real-space curves contain 1001 points. Atomic density
is approximately 0.0808984 atoms/Å³, the normalization multiplier is 0.0144483,
and the extrapolation target is S(0) ≈ −0.0571696. These are reproduction checks
for the stated inputs/settings, not universal values for Mg₂SiO₄.

## 10. Save and inspect the intermediate curves

Every pattern retains its coordinates and values as ordinary Rust vectors.
Export the intermediate states for plotting, comparison or further analysis:

```rust
std::fs::create_dir_all(output_dir)?;
for (name, pattern) in [
    ("measured", &measured),
    ("background-scaled", &scaled_background),
    ("sample", &sample),
    ("normalized-total", &normalized_total),
    ("normalized-coherent", &normalized),
    ("sq-measured", &sq_measured),
    ("sq-extended", &sq_extended),
    ("sq-optimized", &sq_optimized),
    ("fr-unoptimized", &fr_unoptimized),
    ("gr-unoptimized", &gr_unoptimized),
    ("fr-optimized", &fr_optimized),
    ("gr-optimized", &gr_optimized),
    ("fr-lorch", &fr_lorch),
    ("gr-lorch", &gr_lorch),
] {
    pattern.save(output_dir.join(format!("{name}.xy")))?;
}
```

The executable additionally exports the individual scattering moments and
incoherent intensity, making the normalization plot reproducible. The plots below
show the fixed-input analysis; they do not demonstrate a fitted density or
independent physical validation. The Rust/Python audit compares each exported
stage with explicitly selected Python settings.
The low-r panel zooms to −0.5 < g(r) < 0.5; parts of the unoptimized curve lie
outside that vertical range. The full unoptimized curve is exported as well.

## Where to go next

Use `density::optimize_density` when density refinement is justified by the
sample, objective and selected interval; it is a separate operation from this
fixed-density analysis. `parallel::Executor` runs independent analyses or fits
as batches and parameter sweeps. The API reference documents normalization,
scattering, correction and transform options in their respective modules.

## Intermediate results

```{raw} html
:file: ../rust/glassure-core/docs/full_analysis.svg
```
