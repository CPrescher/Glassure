"""Generate Rust/Sphinx tutorials from the executable example's marked stages.

Run with --check in CI. Rustdoc snippets execute the preceding stages against
packaged fixtures; the Sphinx copy shows only the stage being explained.
"""
import argparse
from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).resolve().parents[2]


def render(stem, sphinx_name, standalone=()):
    core = ROOT / "rust/glassure-core"
    source = (core / f"examples/{stem}.rs").read_text()
    stages = {name: textwrap.dedent(body).strip() for name, body in re.findall(
        r"// ANCHOR: (\w+)\n(.*?)\s*// ANCHOR_END: \1", source, re.S)}
    template = (core / f"docs/{stem}.md.in").read_text()
    prefix = []
    rust, sphinx = template, template
    for name in re.findall(r"\{\{(\w+)\}\}", template):
        visible = stages[name]
        if name == "imports":
            rust_block = f"```rust\n{visible}\n```"
        elif name in standalone:
            hidden = "\n".join("# " + line for line in stages["imports"].splitlines())
            rust_block = f"```rust\n# #![allow(unused)]\n{hidden}\n{visible}\n```"
        else:
            setup = stages["imports"] + '''
let data_file = Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/tests/data/Mg2SiO4_ambient.xy"));
let background_file = Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/tests/data/Mg2SiO4_ambient_bkg.xy"));
let scratch = std::env::temp_dir().join(format!("glassure-analysis-doc-{}-{}", std::process::id(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)?.as_nanos()));
let output_dir = scratch.as_path();
'''
            hidden = "\n".join(("# " + line).rstrip() for line in (setup + "\n" + "\n".join(prefix)).splitlines())
            cleanup = "# std::fs::remove_dir_all(output_dir)?;\n" if name == "save" else ""
            rust_block = f"```rust\n# #![allow(unused)]\n{hidden}\n{visible}\n{cleanup}# Ok::<(), Box<dyn std::error::Error>>(())\n```"
            prefix.append(visible)
        rust = rust.replace("{{" + name + "}}", rust_block)
        sphinx = sphinx.replace("{{" + name + "}}", f"```rust\n{visible}\n```")
    sphinx += f'''
## Intermediate results

```{{raw}} html
:file: ../rust/glassure-core/docs/{stem}.svg
```
'''
    return {core / f"docs/{stem}.md": rust, ROOT / f"docs/{sphinx_name}.md": sphinx}


def generate():
    return {
        **render("full_analysis", "rust-analysis"),
        **render("density_fitting", "rust-density-fitting", standalone=("dac",)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for path, expected in generate().items():
        if args.check:
            if not path.exists() or path.read_text() != expected:
                raise SystemExit(f"Stale tutorial: run python3 rust/scripts/generate_analysis_docs.py ({path})")
        else:
            path.write_text(expected)
        print(("Checked " if args.check else "Wrote ") + str(path.relative_to(ROOT)))


if __name__ == "__main__":
    main()
