# Installation

## Requirements
- Python 3.10 or higher (release wheels tested on 3.10–3.13)
- NumPy and Pydantic; the Rust numerical engine is included

Matching binary wheels need no Rust compiler. Building from source requires
Rust 1.93 or newer and a platform C linker. See the [Glassure 3 migration
guide](migration-3.md) for supported wheel platforms and compatibility.

## pip
```bash
python -m pip install glassure
```

For the Python reference backend, pandas tables, lmfit objects and SciPy spline
interfaces, install the optional extra:

```sh
python -m pip install 'glassure[legacy]'
```

To install this stable release explicitly, use `glassure==3.0.0` or
`glassure[legacy]==3.0.0`.

## Development version for contributing

Glassure uses [uv](https://docs.astral.sh/uv/) for dependency management.

### Installing uv
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# With pip
pip install uv
```

### Setting up the development environment
Install Rust 1.93 or newer, then clone the repository and install dependencies:
```bash
git clone https://github.com/CPrescher/Glassure.git
cd Glassure
uv sync --extra dev
```

### Running tests
```bash
# Run all tests
uv run pytest tests --glassure-backend=rust
uv run pytest tests --glassure-backend=python

# Run with coverage
uv run pytest tests --cov=glassure --cov-report=xml

# Run a specific test file
uv run pytest tests/test_pattern.py
```

### Building documentation
```bash
# Install documentation dependencies
uv sync --extra docs

# Build documentation
cd docs
uv run make html
```

Further documentation on how to use uv can be found on the [uv website](https://docs.astral.sh/uv/).
