# Standalone package test data

These files are byte-for-byte copies of the corresponding Glassure repository
fixtures in `tests/data`: `SiO2.xy`, `SiO2_bkg.xy`, `Argon_1GPa.chi` and
`Argon_1GPa_bkg.chi`. They are included here so the distributed CLI package's
XY/CHI, JSON project and density-fit tests do not depend on a source checkout.
They are execution fixtures, not independently validated density calibrations.
