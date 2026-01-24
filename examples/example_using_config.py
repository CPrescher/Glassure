"""
Example: Analyzing SiO2 data using the configuration system

This example demonstrates the high-level API for converting X-ray total
scattering data to a pair distribution function (PDF) using Glassure's
configuration system.
"""
from glassure.pattern import Pattern
from glassure.configuration import (
    SampleConfig,
    DataConfig,
    CalculationConfig,
    TransformConfig,
    IntNormalization,
    ExtrapolationConfig,
    OptimizeConfig,
)
from glassure.calc import calculate_pdf
from glassure.methods import (
    ScatteringFactorSource,
    ExtrapolationMethod,
    FourierTransformMethod,
    OptimizationMethod,
)

# Load data
data_path = "../tests/data/SiO2.xy"
bkg_path = "../tests/data/SiO2_bkg.xy"

data = Pattern.from_file(data_path)
bkg = Pattern.from_file(bkg_path)

print(f"Data range: Q = {data.x[0]:.2f} to {data.x[-1]:.2f} Å⁻¹")
print(f"Number of points: {len(data.x)}")

# Configure the sample
sample_config = SampleConfig(
    composition={"Si": 1, "O": 2},  # SiO2
    density=2.2,  # g/cm³
)

print(f"\nSample: SiO2")
print(f"Density: {sample_config.density} g/cm³")
print(f"Atomic density: {sample_config.atomic_density:.6f} atoms/Å³")

# Configure the transformation
transform_config = TransformConfig(
    q_min=1.0,
    q_max=15.0,
    r_min=0.0,
    r_max=10.0,
    r_step=0.01,
    scattering_factor_source=ScatteringFactorSource.BROWN_HUBBELL,
    normalization=IntNormalization(
        incoherent_scattering=True,
    ),
    extrapolation=ExtrapolationConfig(
        method=ExtrapolationMethod.LINEAR,
        s0=None,  # Will be calculated automatically
    ),
    use_modification_fcn=True,
    fourier_transform_method=FourierTransformMethod.FFT,
)

# Create calculation config
calculation_config = CalculationConfig(
    sample=sample_config,
    transform=transform_config,
    optimize=OptimizeConfig(
        method=OptimizationMethod.ITERATIVE, # Kaplow method
        r_cutoff=1.3, # below first physical peak
        iterations=5,
        use_modification_fcn=True,
    ),
)

# Configure the data
data_config = DataConfig(
    data=data,
    bkg=bkg,
    bkg_scaling=1.0,
)

print("\nConfiguration:")
print(f"  Q range: {transform_config.q_min} - {transform_config.q_max} Å⁻¹")
print(f"  r range: {transform_config.r_min} - {transform_config.r_max} Å")
print(f"  r step: {transform_config.r_step} Å")
print(f"  Scattering factors: {transform_config.scattering_factor_source}")
print(f"  Extrapolation: {transform_config.extrapolation.method.value}")
print(f"  Fourier transform: {transform_config.fourier_transform_method.value}")

# Calculate PDF
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

import matplotlib.pyplot as plt

plt.figure(figsize=(12, 8))
plt.subplot(3, 1, 1)
plt.plot(sq.x, sq.y, label="S(Q)")
plt.xlabel("Q (Å⁻¹)")
plt.ylabel("S(Q)")
plt.title("Structure Factor S(Q)")
plt.grid()
plt.subplot(3, 1, 2)
plt.plot(fr.x, fr.y, label="f(r)", color="orange")
plt.xlabel("r (Å)")
plt.ylabel("f(r)")
plt.title("Fourier Transform f(r)")
plt.grid()
plt.subplot(3, 1, 3)
plt.plot(gr.x, gr.y, label="g(r)", color="green")
plt.xlabel("r (Å)")
plt.ylabel("g(r)")
plt.title("Pair Distribution Function g(r)")
plt.grid()
plt.tight_layout()
plt.show()

# Display results
print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)
print(f"\nS(Q) at Q={sq.x[100]:.2f} Å⁻¹: {sq.y[100]:.4f}")
print(f"f(r) at r={fr.x[100]:.2f} Å: {fr.y[100]:.4f}")
print(f"g(r) at r={gr.x[100]:.2f} Å: {gr.y[100]:.4f}")

# Find first peak in g(r)
import numpy as np

print(f"\nFirst peak in g(r):")
gr_limit = gr.limit(0.5, 3.0)  # Limit to reasonable range for Si-O bond
peak_idx = np.argmax(gr_limit.y)
print(f"  Position: {gr_limit.x[peak_idx]:.3f} Å")
print(f"  Height: {gr_limit.y[peak_idx]:.3f}")

# The result object also contains the full configuration used
print("\n" + "=" * 60)
print("RESULT OBJECT")
print("=" * 60)
print(f"Result contains: sq, fr, gr, calculation_config")
print(f"Result can be serialized to JSON or dict for reproducibility")

# Example: export configuration
config_dict = result.calculation_config.model_dump()
print(f"\nConfiguration can be exported:")
print(f"  Sample composition: {config_dict['sample']['composition']}")
print(f"  Normalization method: {config_dict['transform']['normalization']['TYPE']}")

# Optional: Save results
sq.save("SiO2_sq_config.xy")
fr.save("SiO2_fr_config.xy")
gr.save("SiO2_gr_config.xy")
print(f"\nResults saved to SiO2_sq_config.xy, SiO2_fr_config.xy, SiO2_gr_config.xy")
