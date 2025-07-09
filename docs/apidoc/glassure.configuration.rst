glassure.configuration module
=============================

This module contains all configurations classes necessary for the glassure package.
The main entrypoints are the :class:`glassure.configuration.CalculationConfig` and :class: `glassure.configuration.DataModel` 
pydantic models containing all necessary information for the analysis. These two configurations can then be used analysis
parameters for the :meth:`glassure.calc.calculate_pdf` calculate to perform the analysis. The output of the calculation
will be a :class:`glassure.configuration.Result` object containing the results of the analysis.
The models are then further split into submodels for better readability and maintainability.

.. automodule:: glassure.configuration
   :members:
   :undoc-members:
   :show-inheritance: