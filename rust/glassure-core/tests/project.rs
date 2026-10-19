use glassure_core::{project, request};
use serde_json::{json, Value};

fn fixture() -> Value {
    let x: Vec<_> = (1..=150).map(|i| i as f64 * 0.1).collect();
    let y: Vec<_> = x.iter().map(|q| 100. + q.sin()).collect();
    json!({
        "dataFiles": [{"id": "sample", "pattern": {"name": "measured.xy", "x": x, "y": y},
            "selectedConfigurationId": "fit", "configurations": {
                "fit": {"name": "Fit", "backgroundFileId": "background", "backgroundScale": 0.9,
                    "sample": {"composition": "SiO2", "densityGcm3": 2.2},
                    "optimization": {"isEnabled": true, "method": "fit", "rCutoff": 1.1},
                    "sq": {"stale": true}},
                "integral": {"normalization": {"normalizationMethod": "integral"}}
            }}],
        "backgroundFiles": [{"id": "background", "pattern": {"x": x, "y": vec![1.; 150]}}],
        "selectedDataFileId": "sample", "projectFilename": "measurement.json",
        "extraMetadata": {"keep": true}
    })
}

#[test]
fn recalculation_preserves_project_and_matches_direct_requests() {
    let original = fixture();
    let requests = project::calculations(&original).unwrap();
    assert_eq!(requests.len(), 2);
    let output = project::recalculate(original.clone()).unwrap();
    for entry in requests {
        let expected = request::calculate(entry.calculation).unwrap();
        let c = &output["dataFiles"][0]["configurations"][&entry.configuration_id];
        assert_eq!(c["gr"]["y"], json!(expected.gr.y));
        assert_eq!(c["sq"]["x"], json!(expected.sq.x));
        assert_eq!(c["fr"]["y"], json!(expected.fr.y));
    }
    let mut without_curves = output.clone();
    for key in ["fit", "integral"] {
        for curve in ["sq", "fr", "gr"] {
            without_curves["dataFiles"][0]["configurations"][key]
                .as_object_mut()
                .unwrap()
                .remove(curve);
        }
    }
    let mut expected_metadata = original;
    expected_metadata["dataFiles"][0]["configurations"]["fit"]
        .as_object_mut()
        .unwrap()
        .remove("sq");
    assert_eq!(without_curves, expected_metadata);
    // A saved recalculated project can be imported and recomputed identically.
    let decoded = serde_json::from_str(&serde_json::to_string(&output).unwrap()).unwrap();
    assert_eq!(project::recalculate(decoded).unwrap(), output);
}

#[test]
fn invalid_project_settings_are_never_silently_ignored() {
    for (key, value) in [
        ("backgroundFileId", json!("missing")),
        ("backgroundScale", json!("invalid")),
        ("sample", json!({"densityGcm3": null})),
        ("sample", json!({"composition": null})),
        ("transform", json!({"scattering_factor_source": "hajdu"})),
        ("transform", json!({"qMax": "invalid"})),
        (
            "normalization",
            json!({"normalizationMethod": "unsupported"}),
        ),
        ("normalization", json!({"incoherentScattering": null})),
        (
            "normalization",
            json!({"containerScattering": true, "containerComposition": "C", "dac": {"enabled": true, "sampleThickness": null}}),
        ),
        (
            "optimization",
            json!({"isEnabled": true, "method": "unsupported"}),
        ),
    ] {
        let mut p = fixture();
        p["dataFiles"][0]["configurations"]["fit"][key] = value;
        assert!(project::recalculate(p).is_err(), "accepted {key}");
    }
    for p in [json!({}), json!({"dataFiles": [], "backgroundFiles": []})] {
        assert!(project::calculations(&p).is_err());
    }
}

#[test]
fn browser_defaults_corrections_and_null_handling() {
    let mut p = fixture();
    let c = &mut p["dataFiles"][0]["configurations"]["fit"];
    c["normalization"] = json!({"qCutoff": null, "multipleScattering": true,
        "containerScattering": true, "containerComposition": "C",
        "dac": {"enabled": true, "initialThickness": 40., "sampleThickness": 30.}});
    c["transform"] =
        json!({"qMax": null, "kleinNishimaCorrection": true, "lorchModification": true});
    c["optimization"] = json!({"isEnabled": true, "method": "fit", "rCutoff": 1.1});
    let requests = project::calculations(&p).unwrap();
    let r = &requests
        .iter()
        .find(|r| r.configuration_id == "fit")
        .unwrap()
        .calculation;
    assert_eq!(r.q_max, 10.);
    assert_eq!(r.r_min, 1e-13);
    assert_eq!(r.wavelength, Some(0.31));
    assert!(r.lorch && r.kn_correction);
    let request::Normalization::Fit {
        q_cutoff,
        multiple,
        container,
        dac,
        ..
    } = &r.normalization
    else {
        panic!("wrong normalization");
    };
    assert_eq!(*q_cutoff, 3.);
    assert!(*multiple && container.is_some() && dac.is_some());
    assert_eq!(r.optimize.as_ref().unwrap().method, "fit");
}
