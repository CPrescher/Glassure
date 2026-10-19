use std::io::{self, Read, Write};

fn load_patterns(
    value: &mut serde_json::Value,
    base: &std::path::Path,
) -> Result<(), Box<dyn std::error::Error>> {
    if let Some(object) = value.as_object_mut() {
        if let Some(path) = object.get("file").and_then(|v| v.as_str()) {
            if object.keys().any(|k| k != "file" && k != "skip_rows") {
                return Err("A file pattern accepts only file and skip_rows".into());
            }
            let skip = object
                .get("skip_rows")
                .map(|v| serde_json::from_value::<usize>(v.clone()))
                .transpose()?
                .unwrap_or(if path.ends_with(".chi") { 4 } else { 0 });
            *value = serde_json::to_value(glassure_core::pattern::Pattern::from_file(
                base.join(path),
                skip,
            )?)?;
        } else {
            for value in object.values_mut() {
                load_patterns(value, base)?;
            }
        }
    } else if let Some(values) = value.as_array_mut() {
        for value in values {
            load_patterns(value, base)?;
        }
    }
    Ok(())
}
fn run() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args.get(1).is_some_and(|s| s == "--version") {
        println!("glassure {}", env!("CARGO_PKG_VERSION"));
        return Ok(());
    }
    let command = args.get(1).map(String::as_str).unwrap_or("help");
    if command == "help" || command == "--help" {
        println!("glassure <pdf|density|batch|sweep|factors> [request.json|-] [output.json]\nglassure project <web-project.json> [recalculated-project.json]\nglassure init <data.xy> <composition> <density> [background.xy]\nStandalone Rust total-scattering engine. Omit input or use - for stdin.\nPatterns may contain x/y arrays or a file path relative to the request file.");
        return Ok(());
    }
    if command == "init" {
        if !(5..=6).contains(&args.len()) {
            return Err("Usage: glassure init DATA COMPOSITION DENSITY [BACKGROUND]".into());
        }
        let data = glassure_core::pattern::Pattern::from_file(&args[2], 0)?;
        let mut req = glassure_core::request::Request::new(
            data,
            glassure_core::scattering::Composition::Formula(args[3].clone()),
            args[4].parse()?,
        )?;
        if let Some(path) = args.get(5) {
            req.background = Some(glassure_core::pattern::Pattern::from_file(path, 0)?);
        }
        serde_json::to_writer(io::stdout().lock(), &req)?;
        return Ok(());
    }
    let mut bytes = Vec::new();
    match args.get(2).map(String::as_str) {
        None | Some("-") => {
            io::stdin().read_to_end(&mut bytes)?;
        }
        Some(path) => bytes = std::fs::read(path)?,
    }
    let mut decoded: serde_json::Value = serde_json::from_slice(&bytes)?;
    let base = args
        .get(2)
        .filter(|s| s.as_str() != "-")
        .and_then(|p| std::path::Path::new(p).parent())
        .unwrap_or(std::path::Path::new("."));
    load_patterns(&mut decoded, base)?;
    use glassure_core::{density, parallel, request, scattering};
    let value = match command {
        "project" => glassure_core::project::recalculate(decoded)?,
        "pdf" => serde_json::to_value(request::calculate(serde_json::from_value(decoded)?)?)?,
        "density" => {
            serde_json::to_value(density::optimize_density(serde_json::from_value(decoded)?)?)?
        }
        "batch" => {
            serde_json::to_value(parallel::calculate_batch(serde_json::from_value(decoded)?)?)?
        }
        "sweep" => {
            serde_json::to_value(parallel::parameter_sweep(serde_json::from_value(decoded)?)?)?
        }
        "factors" => {
            let v = decoded;
            let object = v.as_object().ok_or("Factor request must be an object")?;
            if object
                .keys()
                .any(|k| !["composition", "density", "q", "source"].contains(&k.as_str()))
            {
                return Err("Unknown factor request field".into());
            }
            let composition = serde_json::from_value(v["composition"].clone())?;
            let q = serde_json::from_value::<Vec<f64>>(v["q"].clone())?;
            let source = v
                .get("source")
                .map(|v| serde_json::from_value::<scattering::Source>(v.clone()))
                .transpose()?
                .unwrap_or_default();
            let density = v
                .get("density")
                .map(|v| serde_json::from_value::<f64>(v.clone()))
                .transpose()?
                .unwrap_or(1.);
            serde_json::to_value(scattering::factors_with_source(
                &composition,
                density,
                &q,
                source,
            )?)?
        }
        _ => return Err(format!("Unknown command: {command}").into()),
    };
    let mut encoded = serde_json::to_vec(&value)?;
    encoded.push(b'\n');
    if let Some(path) = args.get(3) {
        std::fs::write(path, encoded)?;
    } else {
        io::stdout().lock().write_all(&encoded)?;
    }
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("glassure: {error}");
        std::process::exit(1);
    }
}
