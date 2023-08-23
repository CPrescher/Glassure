1.3.1 (under development)
-------------------------

New features:
    - the chosen scattering factor source can now be applied per configuration and are not global anymore
    - added support for ionic scattering factors when using the brown et al. 2006 scattering factors
    - calculations now also work correctly without specifying a background pattern
    - added typehints to the core calculation functions

Bug fixes:
    - consistent naming for patterns - file endings will now always be omitted
    - removing a configuration now correctly switches to the correct configuration and updates
      the parameters in the gui
    - renaming configurations is now persistent after removing a configuration
    - float numbers can now be entered with a comma as decimal separator, it 
      will be converted to a dot automatically

1.3.0 (2023/04/26)
-------------------------

New features:
    - changed to pyqt 6 which should reduce issues with high dpi screens
    - added support for brown et al. 2006 scattering factors (from international tables of crystallography) and
      hubbell et al. 1975 compton scattering intensities

