# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Glassure is a Python API for analysis of X-ray total scattering (diffraction) data. It performs background subtraction, Fourier transforms, and optimization of experimental data. The package is used in materials science, physics, and chemistry research.

**Note**: The GUI was removed in v2.0.0. A web-based GUI is available at [glassure.vercel.app](https://glassure.vercel.app).

## Development Commands

```bash
# Install dependencies (uses uv package manager)
uv sync --extra dev

# Run all tests
uv run pytest tests

# Run tests with coverage
uv run pytest tests --cov=glassure --cov-report=xml

# Run a specific test file
uv run pytest tests/test_pattern.py

# Run a specific test
uv run pytest tests/test_pattern.py::test_function_name

# Build package (wheel + sdist)
uv build
```

## Architecture

### Core Data Structure
- **`Pattern`** (`pattern.py`): Central data container holding x,y array pairs. Supports arithmetic operations, file I/O, and serialization. Uses Pydantic for validation.

### Configuration System
All calculation parameters use Pydantic models in `configuration.py`:
- `SampleConfig` - sample composition and density
- `DataConfig` - input data settings
- `CalculationConfig` - calculation parameters
- `FitNormalization` / `IntNormalization` - normalization settings
- `Result` - calculation results container

### Processing Pipeline
The typical data flow follows these modules:

1. **`normalization.py`** - Intensity normalization (`normalize()`, `normalize_fit()`)
2. **`transform.py`** - Fourier transforms (`calculate_sq()`, `calculate_fr()`, `calculate_gr()`, `calculate_rdf()`, `calculate_tr()`)
3. **`optimization.py`** - S(q) and density optimization (`optimize_sq()`, `optimize_density()`)

### High-Level API
- **`calc.py`**: `calculate_pdf()` provides a single-function interface combining the entire pipeline

### Supporting Modules
- `utility.py` - Composition parsing, scattering factor calculations, extrapolation methods, density conversions
- `scattering_factors.py` - X-ray scattering factor calculations (Hajdu, Brown-Hubbell, xraylib sources)
- `soller_correction.py` - Soller slit collimation corrections
- `transfer_function.py` - Instrument response functions
- `methods.py` - Enums for normalization, Fourier transform, and extrapolation methods

### Type System
- Composition type: `dict[str, float] | dict[str, int]` (e.g., `{"Si": 1, "O": 2}`)
- String compositions parsed via `parse_str_to_composition()` (e.g., `"SiO2"`)

## Build System

- **Package manager**: uv (migrated from poetry)
- **Build backend**: hatchling with hatch-vcs
- **Versioning**: Dynamic from git tags (written to `glassure/_version.py` during build)
- **Python**: 3.10+ (tested on 3.10, 3.11, 3.12, 3.13)

## CI/CD

- **CI**: Runs pytest on Python 3.10-3.13 matrix (Ubuntu), uploads coverage to Codecov
- **CD**: Triggered on release publish, builds and uploads to PyPI via OIDC
