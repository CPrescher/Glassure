"""
Example: Analyzing SiO2 data using raw functions

This example demonstrates the step-by-step process of converting X-ray total
scattering data to a pair distribution function (PDF) using the low-level
functions in Glassure.
"""

import numpy as np
from glassure.pattern import Pattern
from glassure.utility import (
    calculate_f_squared_mean,
    calculate_f_mean_squared,
    calculate_incoherent_scattering,
    calculate_s0,
    extrapolate_to_zero_linear,
)
from glassure.normalization import normalize
from glassure.transform import calculate_sq, calculate_fr, calculate_gr
from glassure.methods import ScatteringFactorSource

# Sample parameters
composition = {"Si": 1, "O": 2}  # SiO2
density = 2.2  # g/cm^3

# Load data
data_path = "../tests/data/SiO2.xy"
bkg_path = "../tests/data/SiO2_bkg.xy"

data = Pattern.from_file(data_path)
bkg = Pattern.from_file(bkg_path)

print(f"Data range: Q = {data.x[0]:.2f} to {data.x[-1]:.2f} Å⁻¹")
print(f"Number of points: {len(data.x)}")

# Step 1: Background subtraction
bkg_scaling = 1.0
sample = data - bkg * bkg_scaling
print(f"\n1. Background subtracted")

# Step 2: Limit the pattern to a specific Q range (optional)
q_min = 1.0
q_max = 15.0
sample = sample.limit(q_min, q_max)
print(f"2. Pattern limited to Q = {q_min} to {q_max} Å⁻¹")

# Step 3: Calculate atomic density from mass density
from glassure.utility import convert_density_to_atoms_per_cubic_angstrom

atomic_density = convert_density_to_atoms_per_cubic_angstrom(composition, density)
print(f"3. Atomic density: {atomic_density:.6f} atoms/Å³")

# Step 4: Calculate scattering form factors
q = sample.x
scattering_factor_source = ScatteringFactorSource.BROWN_HUBBELL  # or HAJDU

f_squared_mean = calculate_f_squared_mean(composition, q, scattering_factor_source)
f_mean_squared = calculate_f_mean_squared(composition, q, scattering_factor_source)
incoherent_scattering = calculate_incoherent_scattering(
    composition, q, scattering_factor_source
)
print(f"4. Scattering form factors calculated")

# Step 5: Normalize the pattern
n, norm = normalize(
    sample_pattern=sample,
    atomic_density=atomic_density,
    f_squared_mean=f_squared_mean,
    f_mean_squared=f_mean_squared,
    incoherent_scattering=incoherent_scattering,
)
print(f"5. Pattern normalized (normalization factor n = {n:.3e})")

# Step 6: Transform to S(Q)
sq = calculate_sq(norm, f_squared_mean, f_mean_squared)
print(f"6. S(Q) calculated")

# Step 7: Extrapolate to Q=0
s0 = calculate_s0(composition, scattering_factor_source)
sq = extrapolate_to_zero_linear(sq, y0=s0)
print(f"7. Extrapolated to Q=0 (S(0) = {s0:.4f})")

# Step 8: Fourier transform to F(r)
r_min = 0.0
r_max = 10.0
r_step = 0.01
r = np.arange(r_min, r_max + r_step * 0.5, r_step)

fr = calculate_fr(
    sq,
    use_modification_fcn=True,
    method="fft",
    r=r,
)
print(f"8. F(r) calculated (r range: {r_min} to {r_max} Å)")

# Step 9: Transform to g(r)
gr = calculate_gr(fr, atomic_density=atomic_density)
print(f"9. g(r) calculated")

# Display results
print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)
print(f"\nS(Q) at Q={sq.x[100]:.2f} Å⁻¹: {sq.y[100]:.4f}")
print(f"F(r) at r={fr.x[100]:.2f} Å: {fr.y[100]:.4f}")
print(f"g(r) at r={gr.x[100]:.2f} Å: {gr.y[100]:.4f}")

print(f"\nFirst peak in g(r):")
gr_limit = gr.limit(0.5, 3.0)  # Limit to reasonable range for Si-O bond
peak_idx = np.argmax(gr_limit.y) # Search in reasonable range
print(f"  Position: {gr_limit.x[peak_idx]:.3f} Å")
print(f"  Height: {gr_limit.y[peak_idx]:.3f}")

# Optional: Save results
sq.save("SiO2_sq.xy")
fr.save("SiO2_fr.xy")
gr.save("SiO2_gr.xy")
print(f"\nResults saved to SiO2_sq.xy, SiO2_fr.xy, SiO2_gr.xy")
