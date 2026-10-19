use glassure_core::{
    density::{optimize_density, DensityRequest},
    profiling,
};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if !(3..=4).contains(&args.len()) {
        return Err("Usage: profile_density REQUEST.json REPETITIONS [inplace|auto]".into());
    }
    let request: DensityRequest = serde_json::from_slice(&std::fs::read(&args[1])?)?;
    let repeats: usize = args[2].parse()?;
    if repeats == 0 {
        return Err("Require positive repetitions".into());
    }
    let mode = args.get(3).map(String::as_str).unwrap_or("auto");
    if !matches!(mode, "inplace" | "auto") {
        return Err("Invalid FFT profiling mode".into());
    }
    profiling::force_inplace_fft(mode == "inplace");
    std::hint::black_box(optimize_density(request.clone())?);
    profiling::reset();
    for _ in 0..repeats {
        std::hint::black_box(optimize_density(request.clone())?);
    }
    println!(
        "{}",
        serde_json::to_string_pretty(
            &serde_json::json!({"mode":mode,"repetitions":repeats,"stages":profiling::snapshot()})
        )?
    );
    Ok(())
}
