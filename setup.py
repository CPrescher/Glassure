# -*- coding: utf8 -*-

from setuptools import setup, find_packages

import versioneer

setup(
    name='glassure',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    license='MIT',
    author='Clemens Prescher',
    author_email="clemens.prescher@gmail.com",
    url='https://github.com/Luindil/glassure/',
    install_requires=['numpy', 'scipy', 'lmfit', 'pandas', 'pyqtgraph'],
    test_requires=['mock'],
    description='API and GUI for analysis of total scattering data',
    classifiers=['Intended Audience :: Science/Research',
                 'Operating System :: OS Independent',
                 'Programming Language :: Python',
                 'Topic :: Scientific/Engineering',
                 ],
    packages=find_packages(),
    package_data={'glassure': ['core/data/param_atomic_scattering_factors.csv',
                               'core/data/param_incoherent_scattering_intensities.csv',
                               'core/data/atomic_weights.csv',
                               'gui/widgets/DioptasStyle.qss']}
)
