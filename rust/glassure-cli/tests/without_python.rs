use std::{
    io::Write,
    process::{Command, Stdio},
};

// Every workflow launches with no Python interpreter discoverable or usable.
fn standalone() -> Command {
    let mut command = Command::new(env!("CARGO_BIN_EXE_glassure"));
    command
        .env_clear()
        .env("PATH", "")
        .env("PYTHONHOME", "/nonexistent");
    command
}

struct Directory(std::path::PathBuf);
impl Directory {
    fn new() -> Self {
        static NEXT: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
        let id = NEXT.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!("glassure-cli-{}-{id}", std::process::id()));
        std::fs::create_dir(&path).unwrap();
        Self(path)
    }
}
impl Drop for Directory {
    fn drop(&mut self) {
        std::fs::remove_dir_all(&self.0).unwrap();
    }
}

#[test]
fn xy_chi_json_project_and_density_workflows_without_python() {
    use glassure_core::{pattern::Pattern, request::Request};
    use serde_json::json;
    let dir = Directory::new();
    let fixtures = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/data");
    for (data, background, composition, density) in [
        ("SiO2.xy", "SiO2_bkg.xy", "SiO2", "2.2"),
        ("Argon_1GPa.chi", "Argon_1GPa_bkg.chi", "Ar", "1.7"),
    ] {
        let output = standalone()
            .arg("init")
            .arg(fixtures.join(data))
            .args([composition, density])
            .arg(fixtures.join(background))
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        let req: Request = serde_json::from_slice(&output.stdout).unwrap();
        assert!(req.data.x.len() > 100);
    }
    // Relative files are resolved against the JSON file, independently of cwd.
    let data = Pattern::from_file(fixtures.join("SiO2.xy"), 0).unwrap();
    let bkg = Pattern::from_file(fixtures.join("SiO2_bkg.xy"), 0).unwrap();
    data.save(dir.0.join("sample.xy")).unwrap();
    bkg.save(dir.0.join("background.xy")).unwrap();
    let project = json!({"dataFiles": [{"id": "s", "pattern": {"file": "sample.xy"},
        "selectedConfigurationId": "c", "configurations": {"c": {
            "sample": {"composition": "SiO2", "densityGcm3": 2.2},
            "backgroundFileId": "b", "backgroundScale": 1.,
            "transform": {"qMin": 1., "qMax": 17.},
            "optimization": {"isEnabled": true, "rCutoff": 1.1}
        }}}], "backgroundFiles": [{"id": "b", "pattern": {"file": "background.xy"}}],
        "selectedDataFileId": "s", "metadata": "preserved"});
    std::fs::write(
        dir.0.join("project.json"),
        serde_json::to_vec(&project).unwrap(),
    )
    .unwrap();
    let output = standalone()
        .arg("project")
        .arg(dir.0.join("project.json"))
        .arg(dir.0.join("recalculated.json"))
        .current_dir(std::env::temp_dir())
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stdout.is_empty());
    let saved: serde_json::Value =
        serde_json::from_slice(&std::fs::read(dir.0.join("recalculated.json")).unwrap()).unwrap();
    assert_eq!(saved["metadata"], "preserved");
    assert_eq!(saved["selectedDataFileId"], "s");
    assert_eq!(
        saved["dataFiles"][0]["configurations"]["c"]["gr"]["x"]
            .as_array()
            .unwrap()
            .len(),
        1001
    );
    let request = glassure_core::project::calculations(&saved)
        .unwrap()
        .remove(0)
        .calculation;
    let expected = glassure_core::request::calculate(request.clone()).unwrap();
    assert_eq!(
        saved["dataFiles"][0]["configurations"]["c"]["gr"]["y"],
        json!(expected.gr.y)
    );
    expected.gr.save(dir.0.join("gr.xy")).unwrap();
    let reloaded = Pattern::from_file(dir.0.join("gr.xy"), 0).unwrap();
    assert_eq!(reloaded.y, expected.gr.y);
    // The saved request also supports a standalone density fit, not only PDFs.
    let fit = json!({"calculation": request, "method": "gr", "min_range": [0.1, 1.1]});
    std::fs::write(
        dir.0.join("density.json"),
        serde_json::to_vec(&fit).unwrap(),
    )
    .unwrap();
    let output = standalone()
        .arg("density")
        .arg(dir.0.join("density.json"))
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let fit: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(fit["success"], true);
    assert!(fit["density"].as_f64().unwrap() > 0.);
    // Reopening an embedded-array saved project does not need the original XY files.
    std::fs::remove_file(dir.0.join("sample.xy")).unwrap();
    std::fs::remove_file(dir.0.join("background.xy")).unwrap();
    let second = standalone()
        .arg("project")
        .arg(dir.0.join("recalculated.json"))
        .output()
        .unwrap();
    assert!(second.status.success());
    assert_eq!(
        serde_json::from_slice::<serde_json::Value>(&second.stdout).unwrap(),
        saved
    );
}
#[test]
fn cli_computes_without_python_environment() {
    let binary = env!("CARGO_BIN_EXE_glassure");
    let mut child = Command::new(binary)
        .env_clear()
        .env("PATH", "")
        .env("PYTHONHOME", "/nonexistent")
        .args(["factors", "-"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(br#"{"composition":"SiO2","density":2.2,"q":[0,1,2,3],"source":"xraylib"}"#)
        .unwrap();
    let output = child.wait_with_output().unwrap();
    assert!(output.status.success());
    let result: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(result["f2"].as_array().unwrap().len(), 4);
    assert!((result["s0"].as_f64().unwrap() - (-0.08)).abs() < 1e-12);
}
#[test]
fn invalid_cli_request_exits_with_error() {
    let binary = env!("CARGO_BIN_EXE_glassure");
    let mut child = Command::new(binary)
        .args(["pdf", "-"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child.stdin.take().unwrap().write_all(b"{}").unwrap();
    let output = child.wait_with_output().unwrap();
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("missing field"));
}

#[test]
fn full_pdf_runs_without_python_environment() {
    use glassure_core::{
        pattern::Pattern,
        request::Request,
        scattering::{Composition, Source},
    };
    let x: Vec<_> = (1..121).map(|i| i as f64 * 0.1).collect();
    let y: Vec<_> = x.iter().map(|v| 100. + v.sin()).collect();
    let mut req = Request::new(
        Pattern::new(x, y).unwrap(),
        Composition::Formula("SiO2".into()),
        2.2,
    )
    .unwrap();
    req.scattering_factor_source = Source::Xraylib;
    let mut child = Command::new(env!("CARGO_BIN_EXE_glassure"))
        .env_clear()
        .env("PATH", "")
        .env("PYTHONHOME", "/nonexistent")
        .args(["pdf", "-"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(&serde_json::to_vec(&req).unwrap())
        .unwrap();
    let output = child.wait_with_output().unwrap();
    assert!(output.status.success());
    let value: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert!(value["sq"]["x"].as_array().unwrap().len() > 100);
    assert_eq!(value["gr"]["x"].as_array().unwrap().len(), 1001);
}

#[test]
fn invalid_scattering_settings_do_not_fall_back() {
    for input in [
        br#"{"composition":"SiO2","q":[0,1],"source":42}"#.as_slice(),
        br#"{"composition":"SiO2","q":[0,1],"density":"invalid"}"#.as_slice(),
        br#"{"composition":"SiO2","q":[0,1],"scattering_factor_source":"hajdu"}"#.as_slice(),
    ] {
        let mut child = Command::new(env!("CARGO_BIN_EXE_glassure"))
            .args(["factors", "-"])
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap();
        child.stdin.take().unwrap().write_all(input).unwrap();
        let output = child.wait_with_output().unwrap();
        assert!(!output.status.success());
        assert!(output.stdout.is_empty());
    }
}
