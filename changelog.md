## 1.4.5 (2023/06/20)

### Bugfixes
- fixes an issue which caused glassure not to start with some pyqt6 versions

## 1.4.4 (2023/11/14)

### Bugfixes
- subtraction and addition of patterns works now correctly when both have different x values

## 1.4.3 (2023/11/02)

### Bugfixes
- fix recursion error due to recent extrapolation gui changes

## 1.4.2 (2023/10/31)

### Bug fixes:
- not specifically dependent on pyside anymore, glassure should now also work with pyqt6, pyqt5 or pyside2, default
  is still pyside6

## 1.4.1 (2023/10/27)

### Bug fixes:
- fix error with s0 auto calculation when using brown hubbell form factors.
- fix python compatibility for 3.9 and 3.10 

## 1.4.0 (2023/09/03)

### New features:
- the chosen scattering factor source can now be applied per configuration and are not global anymore
- added support for ionic scattering factors when using the brown et al. 2006 scattering factors
- calculations now also work correctly without specifying a background pattern
- added typehints to the core calculation functions
- the normalization method can now be chosen in the GUI - previously only integral was available and now also
  fitting can be chosen
- the Structure Factor calculation method can be chosen in the GUI - now Faber-Ziman and Ashcroft-Langreth are
  available
- fft has been set to be default for the Fourier transform in the GUI and a checkbox has been added to also allow
  the usage of integration method when necessary
- the extrapolation of the S(Q) to zero in the GUI will now calculate the theoretical value for S(Q) at Q=0, using
  the form factors - the value can also be set manually (e.g. for data with very low compressibility)
- the current configurations can be saved as a json file and loaded later for continuing work on these data, or as
  documentation for the data processing
- created basic documentation for the core functions, available under (glassure.readthedocs.io)


### Bug fixes:
- consistent naming for patterns - file endings will now always be omitted
- removing a configuration now correctly switches to the correct configuration and updates the parameters in the gui
- renaming configurations is now persistent after removing a configuration
- visibility of configurations is now persistent after removing or freezing a configuration
- float numbers can now be entered with a comma as decimal separator, it will be converted to a dot automatically
- data and background patterns are correctly updated in the plot when switching between configurations

## 1.3.0 (2023/04/26)

### New features:
- changed to pyqt 6 which should reduce issues with high dpi screens
- added support for brown et al. 2006 scattering factors (from international tables of crystallography) and hubbell et 
  al.1975 compton scattering intensities
