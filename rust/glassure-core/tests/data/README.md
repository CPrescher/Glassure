# Rust tutorial data

`Mg2SiO4_ambient.xy` and `Mg2SiO4_ambient_bkg.xy` are byte-for-byte copies of
the Glassure Python quickstart's fixtures from the repository's `tests/data`.
They are bundled so Rust documentation examples run after source packaging,
without a Python interpreter, network access or files outside the crate.
The tutorial keeps the notebook's 2.7 g/cm³ density input; it does not fit or
independently validate that value.

The density-fitting tutorial uses the same raw files with explicitly different
analysis settings. Their header wavelength is 1.908e-11 m (0.1908 Å). Its joint
fit reaches a background bound; its fitted density is not physically validated.
