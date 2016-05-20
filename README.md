[![Build Status](https://travis-ci.org/Luindil/Glassure.svg?branch=develop)](https://travis-ci.org/Luindil/Glassure)

# Glassure


An API and GUI program for data analysis of total x-ray diffraction data.
It performs background subtraction, Fourier transform and optimization of
experimental data.

## Maintainer

Clemens Prescher (clemens.prescher@gmail.com)

## Requirements

- python 2.7
- PySide/PyQt4
- numpy
- scipy
- pandas
- pyqtgraph (http://www.pyqtgraph.org/)
- lmfit (https://github.com/lmfit/lmfit-py)

It is known to run on Windows, Mac OS X and Linux.

## Installation

The easiest way for Python Newcomers would be to use the Anaconda 64bit Python
distribution. Please download it from [https://www.continuum.io/downloads](https://www.continuum.io/downloads).

Then run the following in the commandline (or Anaconda prompt under Windows):

```bash
conda update --all
pip install lmfit pyqtgraph
```

After that you can install Glassure as a library and use the functionality in your
own scripts or programs by running:

```bash
python setup.py
```

in the Glassure folder. Or you can run the GUI program by running:

```bash
python glassure/glassure.py
```

in the main repository folder.




