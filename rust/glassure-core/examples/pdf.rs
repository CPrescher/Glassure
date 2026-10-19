use glassure_core::{
    pattern::Pattern,
    request::{calculate, Request},
    scattering::Composition,
};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 4 {
        return Err("Usage: pdf DATA.xy BACKGROUND.xy OUTPUT_DIRECTORY".into());
    }
    let mut req = Request::new(
        Pattern::from_file(&args[1], 0)?,
        Composition::Formula("SiO2".into()),
        2.2,
    )?;
    req.background = Some(Pattern::from_file(&args[2], 0)?);
    req.q_min = 1.;
    req.q_max = 17.;
    let result = calculate(req)?;
    let directory = std::path::Path::new(&args[3]);
    std::fs::create_dir_all(directory)?;
    result.sq.save(directory.join("sq.xy"))?;
    result.fr.save(directory.join("fr.xy"))?;
    result.gr.save(directory.join("gr.xy"))?;
    println!(
        "Calculated {} S(Q) points and {} real-space points",
        result.sq.x.len(),
        result.gr.x.len()
    );
    Ok(())
}
