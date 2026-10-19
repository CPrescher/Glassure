//! Import and recalculate the web application's saved JSON projects without Python.
//!
//! UI metadata and saved results are preserved. Numerical settings are translated
//! using the web application's migration and request defaults, without rounding
//! input arrays through its Float32 network transport.
use crate::{
    request::{calculate, Dac, Normalization, Pattern, Request},
    scattering::Composition,
    SqOptimization,
};
use serde::{de::DeserializeOwned, Deserialize};
use serde_json::Value;

/// A typed calculation extracted from a saved browser project.
pub struct ProjectCalculation {
    /// Original data-file ID, used to associate results with the saved project.
    pub data_file_id: String,
    /// Original key in the file's configurations object.
    pub configuration_id: String,
    /// Owned request, usable with PDF, density and parallel APIs.
    pub calculation: Request,
}

fn setting<T: DeserializeOwned>(v: &Value, key: &str, default: T) -> Result<T, String> {
    match v.get(key) {
        None => Ok(default),
        Some(value) => serde_json::from_value(value.clone())
            .map_err(|error| format!("Invalid project setting {key}: {error}")),
    }
}

// Only fields for which the web payload explicitly uses ?? accept null as a
// default. A null composition, method or scattering flag is invalid input.
fn nullable_setting<T: DeserializeOwned>(v: &Value, key: &str, default: T) -> Result<T, String> {
    if v.get(key).is_some_and(Value::is_null) {
        Ok(default)
    } else {
        setting(v, key, default)
    }
}

fn section(v: &Value, key: &str, allowed: &[&str]) -> Result<Value, String> {
    let value = v.get(key).cloned().unwrap_or_else(|| serde_json::json!({}));
    let object = value
        .as_object()
        .ok_or_else(|| format!("Project {key} must be an object"))?;
    for key in object.keys() {
        if !allowed.contains(&key.as_str()) {
            return Err(format!("Unknown project numerical setting: {key}"));
        }
    }
    Ok(value)
}

fn pattern(value: &Value) -> Result<Pattern, String> {
    // Project patterns carry a display name in addition to the numerical arrays.
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct NamedPattern {
        x: Vec<f64>,
        y: Vec<f64>,
        #[serde(default, rename = "name")]
        _name: String,
    }
    let p: NamedPattern = serde_json::from_value(value.clone()).map_err(|e| e.to_string())?;
    Pattern::new(p.x, p.y)
}

fn request(data: Pattern, background: Option<Pattern>, config: &Value) -> Result<Request, String> {
    let sample = section(
        config,
        "sample",
        &["composition", "densityGcm3", "atomicDensity"],
    )?;
    let composition = setting(&sample, "composition", Composition::Formula("SiO2".into()))?;
    // Missing fields follow migration defaults; explicit null follows the web
    // payload's zero-density validation failure, rather than guessing a density.
    let density = if sample.get("densityGcm3").is_some_and(Value::is_null) {
        0.
    } else {
        setting(&sample, "densityGcm3", 2.2)?
    };
    let mut req = Request::new(data, composition, density)?;
    req.background = background;
    req.background_scale = nullable_setting(config, "backgroundScale", 1.)?;
    let t = section(
        config,
        "transform",
        &[
            "qMin",
            "qMax",
            "rMin",
            "rMax",
            "extrapolationMethod",
            "lorchModification",
            "kleinNishimaCorrection",
            "wavelength",
        ],
    )?;
    req.q_min = nullable_setting(&t, "qMin", 0.)?;
    req.q_max = nullable_setting(&t, "qMax", if t.get("qMax").is_some() { 10. } else { 12. })?;
    req.r_min = nullable_setting(&t, "rMin", 0.)?;
    if req.r_min == 0. {
        req.r_min = 1e-13;
    }
    req.r_max = nullable_setting(&t, "rMax", 10.)?;
    req.extrapolation = setting(&t, "extrapolationMethod", "linear".to_owned())?;
    req.lorch = setting(&t, "lorchModification", false)?;
    req.kn_correction = setting(&t, "kleinNishimaCorrection", false)?;
    req.wavelength = Some(nullable_setting(
        &t,
        "wavelength",
        if t.get("wavelength").is_some() {
            0.
        } else {
            0.31
        },
    )?);
    let n = section(
        config,
        "normalization",
        &[
            "normalizationMethod",
            "qCutoff",
            "multipleScattering",
            "incoherentScattering",
            "containerScattering",
            "containerComposition",
            "containerAmount",
            "dac",
        ],
    )?;
    req.incoherent = setting(&n, "incoherentScattering", true)?;
    req.normalization = match setting(&n, "normalizationMethod", "fit".to_owned())?.as_str() {
        "integral" => Normalization::Integral { attenuation: 0.001 },
        "fit" => {
            let container = if setting(&n, "containerScattering", false)? {
                Some(setting(
                    &n,
                    "containerComposition",
                    Composition::Formula(String::new()),
                )?)
            } else {
                None
            };
            let d = section(
                &n,
                "dac",
                &["enabled", "initialThickness", "sampleThickness"],
            )?;
            let dac = if container.is_some() && setting(&d, "enabled", false)? {
                for key in ["initialThickness", "sampleThickness"] {
                    if d.get(key).is_none_or(Value::is_null) {
                        return Err(format!("Enabled DAC requires {key}"));
                    }
                }
                let initial_thickness = setting(&d, "initialThickness", 40.)?;
                let sample_thickness = setting(&d, "sampleThickness", 30.)?;
                if sample_thickness >= initial_thickness {
                    return Err("DAC sample thickness must be less than initial thickness".into());
                }
                Some(Dac {
                    initial_thickness,
                    sample_thickness,
                })
            } else {
                None
            };
            Normalization::Fit {
                q_cutoff: nullable_setting(
                    &n,
                    "qCutoff",
                    if n.get("qCutoff").is_some() { 3. } else { 5. },
                )?,
                scaling: "squared".into(),
                multiple: setting(&n, "multipleScattering", false)?,
                container,
                dac,
            }
        }
        method => return Err(format!("Unknown project normalization: {method}")),
    };
    let o = section(
        config,
        "optimization",
        &[
            "isEnabled",
            "method",
            "rCutoff",
            "iterations",
            "lorchModification",
        ],
    )?;
    if setting(&o, "isEnabled", false)? {
        req.optimize = Some(SqOptimization {
            method: setting(&o, "method", "iterative".to_owned())?,
            r_cutoff: nullable_setting(
                &o,
                "rCutoff",
                if o.get("rCutoff").is_some() { 0. } else { 1.4 },
            )?,
            iterations: nullable_setting(
                &o,
                "iterations",
                if o.get("iterations").is_some() { 0 } else { 5 },
            )?,
            lorch: setting(&o, "lorchModification", false)?,
            attenuation: 1.,
        });
    }
    Ok(req)
}

/// Extract every data/configuration pair. Missing backgrounds and invalid input
/// are errors. Display metadata and cached curves do not affect calculations.
pub fn calculations(project: &Value) -> Result<Vec<ProjectCalculation>, String> {
    let files = project["dataFiles"]
        .as_array()
        .ok_or("Project needs dataFiles array")?;
    let backgrounds = project["backgroundFiles"]
        .as_array()
        .ok_or("Project needs backgroundFiles array")?;
    let mut ids = std::collections::HashSet::new();
    let mut background_map = std::collections::HashMap::new();
    for b in backgrounds {
        let id = b["id"].as_str().ok_or("Background needs an id")?;
        if background_map.insert(id, &b["pattern"]).is_some() {
            return Err(format!("Duplicate background id: {id}"));
        }
    }
    let mut requests = Vec::new();
    for file in files {
        let id = file["id"].as_str().ok_or("Data file needs an id")?;
        if !ids.insert(id) {
            return Err(format!("Duplicate data file id: {id}"));
        }
        let data = pattern(&file["pattern"])?;
        let configs = file["configurations"]
            .as_object()
            .ok_or("Data file needs configurations object")?;
        for (key, config) in configs {
            if !config.is_object() {
                return Err("Configuration must be an object".into());
            }
            let background = match config.get("backgroundFileId").filter(|v| !v.is_null()) {
                None => None,
                Some(value) => {
                    let id = value.as_str().ok_or("backgroundFileId must be a string")?;
                    Some(pattern(
                        background_map
                            .get(id)
                            .ok_or_else(|| format!("Missing background: {id}"))?,
                    )?)
                }
            };
            let calculation = request(data.clone(), background, config)
                .map_err(|e| format!("Data {id}, configuration {key}: {e}"))?;
            requests.push(ProjectCalculation {
                data_file_id: id.into(),
                configuration_id: key.clone(),
                calculation,
            });
        }
    }
    if requests.is_empty() {
        return Err("Project has no calculations".into());
    }
    Ok(requests)
}

/// Recompute all configurations into a copy of the project, preserving settings,
/// IDs, selections and unrelated UI metadata. Does not overwrite fitted density.
pub fn recalculate(mut project: Value) -> Result<Value, String> {
    let requests = calculations(&project)?;
    for entry in requests {
        let result = calculate(entry.calculation).map_err(|e| {
            format!(
                "Data {}, configuration {}: {e}",
                entry.data_file_id, entry.configuration_id
            )
        })?;
        let file = project["dataFiles"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|f| f["id"].as_str() == Some(&entry.data_file_id))
            .unwrap();
        let config = &mut file["configurations"][&entry.configuration_id];
        for (key, p) in [("sq", result.sq), ("fr", result.fr), ("gr", result.gr)] {
            config[key] = serde_json::json!({"name": "", "x": p.x, "y": p.y});
        }
    }
    Ok(project)
}
