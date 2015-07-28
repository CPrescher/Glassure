__author__ = 'Clemens Prescher'

from setuptools import setup, find_packages

import glassure

setup(
    name='glassure',
    version=glassure.__version__,
    url='https://github.com/Luindil/glassure/',
    license='GPLv3',
    author='Clemens Prescher',
    author_email="clemens.prescher@gmail.com",
    description='API and GUI for analysis of total scattering data',
    packages=find_packages(),
    package_data={'glassure': ['core/data/param_atomic_scattering_factors.csv',
                               'core/data/param_incoherent_scattering_intensities.csv',
                               'core/data/atomic_weights.csv']}
)
