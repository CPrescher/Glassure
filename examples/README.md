# Glassure Examples

This directory contains examples demonstrating how to use Glassure for analyzing X-ray total scattering data.

## Examples

### 1. `example_quick_start.py` ⭐ **Start Here!**

Demonstrates the quickest way to get started with default settings:

- Use `create_calculate_pdf_configs()` helper function
- Minimal code - just provide data, composition, and density
- Automatic Q range detection
- Sensible defaults for all parameters

**Best for**: Getting started, quick analysis, or when defaults are sufficient.

### 2. `example_raw_functions.py`

Demonstrates the step-by-step process using low-level functions:

- Load data from files
- Background subtraction
- Calculate scattering form factors
- Normalize intensity
- Transform to S(Q)
- Extrapolate to Q=0
- Fourier transform to f(r) and g(r)

**Best for**: Learning the internals, debugging, or custom processing pipelines.

### 3. `example_using_config.py`

Demonstrates the high-level API using the configuration system:

- Define sample properties with `SampleConfig`
- Configure transformation parameters with `TransformConfig`
- Run the complete pipeline with `calculate_pdf()`

**Best for**: Production analysis, reproducible research, or when you need custom parameters.

## Dataset

Both examples use the same test dataset:

- **Sample**: `../tests/data/SiO2.xy` - SiO2 (silica) X-ray scattering pattern
- **Background**: `../tests/data/SiO2_bkg.xy` - Background pattern

## Running the Examples

From the examples directory:

```bash
cd examples

# Quick start with defaults (recommended for beginners)
uv run python example_quick_start.py

# Using raw functions (for learning/customization)
uv run python example_raw_functions.py

# Using configuration system (for production)
uv run python example_using_config.py
```

All examples will:

1. Load the SiO2 data
2. Process it through the complete analysis pipeline
3. Display key results
4. Save output files (S(Q), f(r), g(r))

## Expected Output

All three approaches produce equivalent results:

- **S(Q)**: Structure factor
- **f(r)**: Reduced pair distribution function
- **g(r)**: Pair correlation function

The first peak in g(r) for SiO2 should appear around 1.6 Å, corresponding to the Si-O bond length.

## Which Approach to Use?

### Decision Guide

```
Need a quick result? → Use example_quick_start.py
    ↓ (defaults not suitable)
Need custom settings? → Use example_using_config.py
    ↓ (need even more control)
Building custom pipeline? → Use example_raw_functions.py
```

### Detailed Comparison

| Feature             | Quick Start    | Configuration | Raw Functions  |
| ------------------- | -------------- | ------------- | -------------- |
| **Lines of code**   | ~10            | ~30           | ~60            |
| **Customization**   | Limited        | Full          | Complete       |
| **Reproducibility** | Good           | Excellent     | Manual         |
| **Learning curve**  | Easiest        | Moderate      | Steepest       |
| **Use case**        | Quick analysis | Production    | Research/Debug |

- **Quick start** (`create_calculate_pdf_configs`): Perfect for beginners or when defaults are fine
- **Configuration system** (`CalculationConfig`): Best for reproducible research and production workflows
- **Raw functions**: Maximum control for researchers developing new methods
