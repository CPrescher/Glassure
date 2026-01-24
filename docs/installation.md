# Installation

## Requirements
- Python 3.10 or higher

## pip
```bash
python -m pip install glassure
```

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
Clone the repository and install dependencies:
```bash
git clone https://github.com/CPrescher/Glassure.git
cd Glassure
uv sync --extra dev
```

### Running tests
```bash
# Run all tests
uv run pytest tests

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
