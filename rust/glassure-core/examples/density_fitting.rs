//! Density/background refinement and independent native multicore fits.
// ANCHOR: imports
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
// ANCHOR_END: imports

// ANCHOR: dac
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
// ANCHOR_END: dac

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 4 {
        return Err("Usage: density_fitting DATA.xy BACKGROUND.xy OUTPUT_DIRECTORY".into());
    }
    let data_file = Path::new(&args[1]);
    let background_file = Path::new(&args[2]);
    let output_dir = Path::new(&args[3]);

    // ANCHOR: prepare
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
    // ANCHOR_END: prepare

    // ANCHOR: corrections
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
    // ANCHOR_END: corrections

    // ANCHOR: fixed
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
    // ANCHOR_END: fixed

    // ANCHOR: joint
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
    // ANCHOR_END: joint

    // ANCHOR: reuse
    let mut fitted_request = request.clone();
    fitted_request.density = joint.density;
    fitted_request.background_scale = joint.background_scale;
    let recalculated = calculate(fitted_request.clone())?;
    assert_eq!(recalculated.gr.x, joint.result.gr.x);
    for (a, b) in recalculated.gr.y.iter().zip(&joint.result.gr.y) {
        assert!((a - b).abs() < 1e-8 + 1e-8 * b.abs());
    }
    // ANCHOR_END: reuse

    // ANCHOR: batch
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
    // ANCHOR_END: batch

    // Independent fits use the same arithmetic regardless of scheduling.
    for (a, b) in serial.items.iter().zip(&multicore.items) {
        match (a, b) {
            (Item::Success { output: a }, Item::Success { output: b }) => {
                match (a.as_ref(), b.as_ref()) {
                    (JobOutput::Density(a), JobOutput::Density(b)) => {
                        assert_eq!(a.density, b.density);
                        assert_eq!(a.background_scale, b.background_scale);
                        assert_eq!(a.result.sq.y, b.result.sq.y);
                        assert_eq!(a.result.fr.y, b.result.fr.y);
                        assert_eq!(a.result.gr.y, b.result.gr.y);
                    }
                    _ => unreachable!(),
                }
            }
            _ => return Err("An independent serial/multicore fit failed".into()),
        }
    }

    // ANCHOR: save
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
    // ANCHOR_END: save

    let q: Vec<_> = request
        .data
        .x
        .iter()
        .copied()
        .filter(|q| *q > request.q_min && *q < request.q_max)
        .collect();
    Pattern::new(q.clone(), klein_nishina(&q, 0.1908)?)?
        .save(output_dir.join("klein-nishina.xy"))?;
    // Construction check only: no DAC correction is applied to ambient data.
    let dac_template = configure_dac(request.clone(), 0.1908, 40.0, 20.0);
    assert!(matches!(
        dac_template.normalization,
        Normalization::Fit { dac: Some(_), .. }
    ));
    let report = serde_json::json!({
        "measurement": "ambient Mg2SiO4", "physically_validated_density": false,
        "request": request, "fixed": fixed, "joint": joint,
        "background_bounds": background_bounds, "at_background_bound": at_background_bound,
        "starts": starts, "serial": serial, "multicore": multicore,
        "serial_seconds": serial_seconds, "multicore_seconds": multicore_seconds,
        "serial_multicore_identical": true,
        "dac_applied_to_ambient_data": false,
    });
    std::fs::write(
        output_dir.join("analysis.json"),
        serde_json::to_vec_pretty(&report)?,
    )?;
    println!(
        "threads={}, serial={serial_seconds:.4}s, multicore={multicore_seconds:.4}s",
        multicore_executor.threads()
    );
    Ok(())
}
