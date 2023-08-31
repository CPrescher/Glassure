# Installation 

## Using it within python
### Requirements
- Python 3.9 or higher

It is known to work on Windows, Linux and Mac OS X.
 
### pip
```bash
python -m pip install glassure
```

The graphical user interface for Glassure can then be started with:
```bash
glassure
```
in the command line.

### Development version for contributing
Python uses poetry for dependency management. To install poetry, follow the instructions on their 
[website](https://python-poetry.org/docs/#installation). Then, clone the forked repository and install the dependencies:
```bash
poetry install
```

To start the graphical user interface, run:
```bash
poetry run glassure
```

or activate the virtual environment with:
```bash
poetry shell
``` 
and then run:
```bash
glassure
```

Further documentation can be found on the poetry [website](https://python-poetry.org/docs/basic-usage/).

### Executable

Currently, there are no executables or direct installers available. If you want to create one, please contact me 
(clemens.prescher@gmail.com).