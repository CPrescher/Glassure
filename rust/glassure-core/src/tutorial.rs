//! A worked analysis using the individual Rust operations, with reproducible
//! intermediate curves and an equivalent high-level request.
//! Continue with [`density_fitting`] for density/background refinement,
//! corrections and independent multicore fits.
#![doc = include_str!("../docs/full_analysis.md")]
#![doc = "\n## Intermediate results\n"]
#![doc = include_str!("../docs/full_analysis.svg")]

pub mod density_fitting;
