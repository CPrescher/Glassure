[![Coverage Status](https://coveralls.io/repos/github/Luindil/Glassure/badge.svg?branch=develop)](https://coveralls.io/github/Luindil/Glassure?branch=develop)
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

The easiest way for Python Newcomers would be to use the Anaconda or Miniconda 64bit Python 3.5
distribution. 
Please download it from [https://www.continuum.io/downloads](https://www.continuum.io/downloads) and install it.

Then run the following in the commandline (or Anaconda prompt under Windows):

```bash
conda config --add channels cprescher
conda install glassure
```

The graphical user interface for glassure can now be started from by typing
```bash
glassure
```

if you want to make a short cut for the desktop, the glassure executable can be found in the 
%anaconda_directory%/scripts folder.  




