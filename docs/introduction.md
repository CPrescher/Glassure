# Introduction

Glassure is a Python library for the calculation of pair distribution functions from X-ray total scattering data.

## Getting Started

For a quick introduction to the API, check out the **[examples](https://github.com/CPrescher/Glassure/tree/develop/examples)** directory in the repository, which includes:

1. **Quick Start Example** - Minimal code to get started with default settings
2. **Raw Functions Example** - Step-by-step walkthrough of the analysis pipeline
3. **Configuration Example** - Production-ready approach with full customization

For detailed API documentation, see [API - Quickstart](api.ipynb) and the [API Documentation](apidoc/glassure.rst).

## Key Features

- Background subtraction and normalization
- Fourier transforms (S(Q) → F(r) → g(r))
- Density optimization (Kaplow method)
- Multiple scattering factor sources (Hajdu, Brown-Hubbell, xraylib)
- Soller slit corrections
- Pydantic-based configuration system for reproducibility