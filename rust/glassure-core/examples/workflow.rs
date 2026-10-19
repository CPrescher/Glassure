//! Executable documentation: file input, PDF, TRF fit, batches and sweeps.
use glassure_core::{
    density::{optimize_density, DensityRequest},
    parallel::{Executor, Item, Job, JobOutput, SweepPoint},
    pattern::Pattern,
    request::{calculate, Request},
    scattering::Composition,
    SqOptimization,
};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 4 {
        return Err("Usage: workflow DATA.xy BACKGROUND.xy OUTPUT_DIRECTORY".into());
    }
    let mut request = Request::new(
        Pattern::from_file(&args[1], 0)?,
        Composition::Formula("SiO2".into()),
        2.2, // mass density, g/cm³
    )?;
    request.background = Some(Pattern::from_file(&args[2], 0)?);
    request.q_min = 1.; // Å⁻¹, strict crop
    request.q_max = 17.;
    request.extrapolation = "linear".into();
    request.optimize = Some(SqOptimization {
        method: "iterative".into(),
        r_cutoff: 1.1, // Å, below the first Si–O peak
        iterations: 5,
        lorch: false,
        attenuation: 1.,
    });

    let output = std::path::Path::new(&args[3]);
    std::fs::create_dir_all(output)?;
    std::fs::write(
        output.join("pdf-request.json"),
        serde_json::to_vec_pretty(&request)?,
    )?;
    let pdf = calculate(request.clone())?;
    pdf.sq.save(output.join("sq.xy"))?;
    pdf.fr.save(output.join("fr.xy"))?;
    pdf.gr.save(output.join("gr.xy"))?;

    let fit_request = DensityRequest {
        calculation: request.clone(),
        method: "gr".into(),
        min_range: Some([0.1, 1.1]), // Å for g(r)/F(r), Å⁻¹ for S(Q)
        vary_background: false,
        background_limits: [0.9, 1.1], // unused when background is fixed
        algorithm: "lsq".into(),       // bounded TRF
        max_evaluations: 500,
    };
    let fit = optimize_density(fit_request.clone())?;
    std::fs::write(
        output.join("density-request.json"),
        serde_json::to_vec_pretty(&fit_request)?,
    )?;
    println!(
        "Density: {:.8} g/cm³; conditional error: {:?}",
        fit.density, fit.density_error
    );
    fit.result.gr.save(output.join("gr-fitted.xy"))?;

    // Reuse this pool across calls. Each individual fit remains sequential.
    let executor = Executor::new(0)?;
    let jobs = vec![Job::Calculate(request.clone()), Job::Density(fit_request)];
    std::fs::write(
        output.join("batch-request.json"),
        serde_json::to_vec_pretty(&serde_json::json!({"jobs": jobs, "threads": 2}))?,
    )?;
    let batch = executor.batch(jobs)?;
    for (index, item) in batch.items.into_iter().enumerate() {
        match item {
            Item::Success { output } => match *output {
                JobOutput::Calculate(pdf) => {
                    println!("Job {index}: {} g(r) points", pdf.gr.x.len())
                }
                JobOutput::Density(fit) => {
                    println!("Job {index}: density {:.8} g/cm³", fit.density)
                }
            },
            Item::Error { operation, error } => {
                return Err(format!("Job {index} ({operation}): {error}").into())
            }
        }
    }
    let points = vec![
        SweepPoint {
            q_max: Some(15.),
            ..Default::default()
        },
        SweepPoint {
            q_max: Some(17.),
            ..Default::default()
        },
    ];
    let base = Job::Calculate(request);
    std::fs::write(
        output.join("sweep-request.json"),
        serde_json::to_vec_pretty(
            &serde_json::json!({"base": base, "points": points, "threads": 2}),
        )?,
    )?;
    let sweep = executor.sweep(&base, points)?;
    for (index, item) in sweep.items.into_iter().enumerate() {
        match item {
            Item::Success { output: result } => {
                let JobOutput::Calculate(pdf) = *result else {
                    unreachable!()
                };
                pdf.gr.save(output.join(format!("gr-sweep-{index}.xy")))?;
            }
            Item::Error { error, .. } => return Err(format!("Sweep point {index}: {error}").into()),
        }
    }
    Ok(())
}
