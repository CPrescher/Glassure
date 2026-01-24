"""
Example: Quick start with default settings

This example demonstrates the simplest way to analyze X-ray total scattering
data using Glassure's convenience function `create_calculate_pdf_configs`.

This approach automatically:
- Sets Q range to match your data
- Uses sensible default settings for all parameters
- Requires minimal configuration

Perfect for getting started quickly or when you don't need custom settings.
"""

import numpy as np

from glassure.pattern import Pattern
from glassure.calc import create_calculate_pdf_configs, calculate_pdf

# Load data
data_path = "../tests/data/SiO2.xy"
bkg_path = "../tests/data/SiO2_bkg.xy"

data = Pattern.from_file(data_path)
bkg = Pattern.from_file(bkg_path)

print("=" * 60)
print("QUICK START EXAMPLE - SiO2 Analysis")
print("=" * 60)
print(f"\nData loaded:")
print(f"  Q range: {data.x[0]:.2f} to {data.x[-1]:.2f} Å⁻¹")
print(f"  Number of points: {len(data.x)}")

# Create configurations with defaults - just provide the essentials!
data_config, calculation_config = create_calculate_pdf_configs(
    data=data,
    composition="SiO2",  # Can use string notation
    density=2.2,  # g/cm³
    bkg=bkg,
    bkg_scaling=1.0,
)

print(f"\nSample: SiO2")
print(f"Density: {calculation_config.sample.density} g/cm³")
print(f"Atomic density: {calculation_config.sample.atomic_density:.6f} atoms/Å³")

print("\nDefault settings applied:")
print(
    f"  Q range: {calculation_config.transform.q_min:.2f} - {calculation_config.transform.q_max:.2f} Å⁻¹"
)
print(
    f"  r range: {calculation_config.transform.r_min} - {calculation_config.transform.r_max} Å"
)
print(f"  r step: {calculation_config.transform.r_step} Å")
print(f"  Normalization: {calculation_config.transform.normalization.TYPE}")
print(f"  Extrapolation: {calculation_config.transform.extrapolation.method.value}")

# Calculate PDF with one function call!
print("\nCalculating PDF...")
result = calculate_pdf(data_config, calculation_config)
print("Done!")

# Access results
sq = result.sq
fr = result.fr
gr = result.gr

assert sq is not None, "S(Q) result is missing"
assert fr is not None, "f(r) result is missing"
assert gr is not None, "g(r) result is missing"

# Display results
print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)

# Show some key values
print(f"\nStructure factor S(Q):")
print(f"  S(Q) at Q={sq.x[100]:.2f} Å⁻¹: {sq.y[100]:.4f}")
print(f"  S(Q) at Q={sq.x[-1]:.2f} Å⁻¹: {sq.y[-1]:.4f}")

print(f"\nReduced PDF f(r):")
print(f"  f(r) at r={fr.x[100]:.2f} Å: {fr.y[100]:.4f}")

print(f"\nPair correlation function g(r):")
print(f"  g(r) at r={gr.x[100]:.2f} Å: {gr.y[100]:.4f}")

# Find first peak in g(r) - corresponds to nearest neighbor distance
print(f"\nFirst peak in g(r) (Si-O bond):")
gr_limit = gr.limit(0.5, 3.0)  # Limit to reasonable range for Si-O bond
peak_idx = np.argmax(gr_limit.y)
print(f"  Position: {gr_limit.x[peak_idx]:.3f} Å")
print(f"  Height: {gr_limit.y[peak_idx]:.3f}")
print(f"  (Expected Si-O bond length: ~1.6 Å)")

# Optional: Customize settings if needed
print("\n" + "=" * 60)
print("CUSTOMIZATION EXAMPLE")
print("=" * 60)
print("\nYou can modify the default configs before calculating:")
print("  calculation_config.transform.r_max = 20.0")
print("  calculation_config.transform.use_modification_fcn = False")
print("  calculation_config.optimize = OptimizeConfig(...)")
print("\nThen run calculate_pdf() again with the modified config.")


# Save results
sq.save("SiO2_sq_quick.xy")
fr.save("SiO2_fr_quick.xy")
gr.save("SiO2_gr_quick.xy")
print("\nResults saved to SiO2_sq_quick.xy, SiO2_fr_quick.xy, SiO2_gr_quick.xy")

print("\n" + "=" * 60)
print("Analysis complete!")
print("=" * 60)
