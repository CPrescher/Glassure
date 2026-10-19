//! Stage-by-stage Mg2SiO4 analysis matching the Python quickstart's operations.
// ANCHOR: imports
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
// ANCHOR_END: imports

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 4 {
        return Err("Usage: full_analysis DATA.xy BACKGROUND.xy OUTPUT_DIRECTORY".into());
    }
    let data_file = Path::new(&args[1]);
    let background_file = Path::new(&args[2]);
    let output_dir = Path::new(&args[3]);

    // ANCHOR: load
    let measured = Pattern::from_file(data_file, 0)?;
    let background = Pattern::from_file(background_file, 0)?;
    // ANCHOR_END: load

    // ANCHOR: subtract
    let background_scale = 1.1;
    let scaled_background = background.scale(background_scale)?;
    let sample = measured.combine(&background, -background_scale)?;
    // Q in Å⁻¹; strict bounds
    let sample = sample.limit(0.0, 16.0)?;
    // ANCHOR_END: subtract

    // ANCHOR: scattering
    let composition = Composition::Formula("Mg2SiO4".into());
    let mass_density = 2.7; // g/cm³: an input estimate, not a fitted result
    let rho = atomic_density(&composition, mass_density)?; // atoms/Å³
    let source = Source::Hajdu;
    let factors = factors_with_source(&composition, mass_density, &sample.x, source)?;
    // factors.f2 = <f²>; factors.fm2 = <f>²; these are different quantities.
    // ANCHOR_END: scattering

    // ANCHOR: normalize
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
    // ANCHOR_END: normalize

    // ANCHOR: structure
    let sq_measured = calculate_sq(&normalized, &factors.f2, &factors.fm2)?;
    let sq_extended = sq_measured.extend_to(0.0, factors.s0)?;
    // ANCHOR_END: structure

    // ANCHOR: transform
    let r_step = 0.01; // Å
    let r = arange(1e-10, 10.0 + 0.5 * r_step, r_step)?;
    let method = Method::Fft;
    let fr_unoptimized = calculate_fr(&sq_extended, &r, method, false)?;
    let gr_unoptimized = calculate_gr(&fr_unoptimized, rho)?;
    // ANCHOR_END: transform

    // ANCHOR: optimize
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
    // ANCHOR_END: optimize

    // ANCHOR: lorch
    let fr_lorch = calculate_fr(&sq_optimized, &r, method, true)?;
    let gr_lorch = calculate_gr(&fr_lorch, rho)?;
    // ANCHOR_END: lorch

    // ANCHOR: high_level
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
    // ANCHOR_END: high_level

    let mut high_level_max_error = 0.0_f64;
    for (manual, automatic) in [
        (&sq_optimized, &automatic.sq),
        (&fr_lorch, &automatic.fr),
        (&gr_lorch, &automatic.gr),
    ] {
        assert_eq!(manual.x, automatic.x);
        for (a, b) in manual.y.iter().zip(&automatic.y) {
            high_level_max_error = high_level_max_error.max((a - b).abs());
            assert!(
                (a - b).abs() <= 1e-9 + 1e-9 * b.abs(),
                "manual/high-level mismatch: {a} vs {b}"
            );
        }
    }

    // ANCHOR: save
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
    // ANCHOR_END: save

    for (name, y) in [
        ("f-squared-mean", factors.f2.clone()),
        ("f-mean-squared", factors.fm2.clone()),
        ("incoherent", factors.incoherent.clone()),
    ] {
        Pattern::new(sample.x.clone(), y)?.save(output_dir.join(format!("{name}.xy")))?;
    }
    let metrics = serde_json::json!({
        "composition": "Mg2SiO4", "mass_density_g_cm3": mass_density,
        "atomic_density_atoms_A3": rho, "background_scale": background_scale,
        "scattering_source": source, "normalization": parameters,
        "s0": factors.s0, "q_points_measured": sq_measured.x.len(),
        "q_points_extended": sq_extended.x.len(), "r_points": r.len(),
        "high_level_max_absolute_difference": high_level_max_error,
        "density_was_fitted": false,
    });
    std::fs::write(
        output_dir.join("analysis.json"),
        serde_json::to_vec_pretty(&metrics)?,
    )?;
    println!("{metrics}");
    Ok(())
}
