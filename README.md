[![codecov](https://codecov.io/gh/CPrescher/Glassure/graph/badge.svg?token=H7XYCD78TT)](https://codecov.io/gh/CPrescher/Glassure)
[![DOI](https://zenodo.org/badge/24698239.svg)](https://zenodo.org/badge/latestdoi/24698239)

# Glassure

A Python API for data analysis of total x-ray diffraction data.
It performs background subtraction, Fourier transform and optimization of
experimental data.

**Warning**, the upgrade from version 1.4.5 to 2.0.0 has removed the GUI - which came with glassure. A new WebGUI based on the version 2 API is available under [glassure.vercel.app](https://glassure.vercel.app).

## Documentation

The documentation can be found [here](https://glassure.readthedocs.io/en/latest/).

## Changelog

The changelog can be found [here](https://glassure.readthedocs.io/en/latest/changelog.html).

## Maintainer

Clemens Prescher (clemens.prescher@gmail.com)

## Requirements

- python 3.10+

It is known to run on Windows, Mac OS X and Linux.

## Installation

The Glassure package can be installed into your existing python distribution using pypi via:

```bash
python -m pip install glassure
```

## Quick Start

Check out the [examples](examples/) directory for complete working examples:

### 1. **Quick Start** ⭐
```python
from glassure.pattern import Pattern
from glassure.calc import create_calculate_pdf_configs, calculate_pdf

# Load your data
data = Pattern.from_file("sample.xy")
bkg = Pattern.from_file("background.xy")

# Create configs with defaults - just provide the essentials!
data_config, calculation_config = create_calculate_pdf_configs(
    data=data,
    composition="SiO2",  # or {"Si": 1, "O": 2}
    density=2.2,  # g/cm³
    bkg=bkg,
)

# Calculate PDF
result = calculate_pdf(data_config, calculation_config)

# Access results: S(Q), F(r), g(r)
result.sq.save("sq.xy")
result.fr.save("fr.xy")
result.gr.save("gr.xy")
```

### 2. Configuration System (For production)
For more control, use the configuration system with `SampleConfig`, `TransformConfig`, and `CalculationConfig`.

### 3. Raw Functions (For research/debugging)
For maximum control, use the low-level functions directly.

**See the [examples](examples/) directory for complete, documented examples of all three approaches.**

## Example Datasets

The repository includes test datasets in `tests/data/`:
- `SiO2.xy` - SiO2 (silica) X-ray scattering pattern
- `SiO2_bkg.xy` - Background pattern

Use these with the example scripts to get started!  




