# Theoretical Background

This document describes the theoretical foundations and equations used in Glassure for X-ray total scattering analysis.

## Overview

Glassure transforms raw X-ray diffraction intensity data into pair distribution functions (PDF) through the following steps:

1. **Background subtraction** - Remove background scattering
2. **Normalization** - Normalize intensity to obtain structure factor S(Q)
3. **Extrapolation** - Extend S(Q) to Q=0
4. **Fourier transform** - Transform S(Q) to reduced PDF F(r)
5. **Convert to g(r)** - Obtain pair correlation function g(r)

## Atomic Form Factors

For a sample with composition containing elements with concentrations $c_i$, the average form factors are:

$$\langle f(Q) \rangle = \sum_i c_i f_i(Q)$$

$$\langle f^2(Q) \rangle = \sum_i c_i f_i^2(Q)$$

where $f_i(Q)$ is the atomic form factor for element $i$ at scattering vector $Q$.

The concentrations are normalized: $\sum_i c_i = 1$

## Normalization to Structure Factor S(Q)

### Integral Normalization Method

After background subtraction, the sample intensity $I_{\text{sample}}(Q)$ needs to be
normalized to atomic units to obtain the structure factor:

$$S(Q) = \frac{I_{\text{norm}}(Q) - \langle f^2(Q) \rangle - I_{\text{inc}}(Q)}{\langle f(Q) \rangle^2} + 1$$

where:

- $I_{\text{norm}}(Q)$ is the normalized intensity, with $\alpha \cdot I(Q) = I_{\text{norm}}(Q)$ and $\alpha$ being the normalization factor
- $\langle f^2(Q) \rangle$ is the average of squared form factors
- $\langle f(Q) \rangle^2$ is the squared average form factor
- $I_{\text{inc}}(Q)$ is the incoherent (Compton) scattering


### Krogh-Moe Normalization Method

The Krogh-Moe method determines the normalization factor $\alpha$ as:

$$\alpha = \frac{-2\pi^2\rho_0 + \int_0^{Q_{\max}} \frac{\sum_p I^{\text{incoh}}(Q) + \langle f^2 \rangle}{\langle f \rangle^2} Q^2 dQ}{\int_0^{Q_{\max}} \frac{I^{\text{sample}}(Q)}{\langle f \rangle^2} Q^2 dQ}$$

where:
- $\rho_0$ is the atomic number density

The normalized intensity is then: $I_{\text{norm}}(Q) = \alpha \cdot I_{\text{sample}}(Q)$

### Fit Normalization Method

An alternative approach fits the normalization using the high-Q behavior:

$$I_{\text{norm}}(Q) = \alpha \cdot I_{\text{sample}}(Q)$$

where $\alpha$ are determined by fitting to the expected asymptotic behavior at high Q.
This method allows for additional flexibility in normalization by adding multiple scattering or
other contributions, such as container scattering.

## Other Formalisms used for Structure Factor

Other common definitions of the structure factor exist:

$$i_{\text{total}}(Q) = S(Q) - 1$$

$$F(Q) = Q[S(Q) - 1]$$

## Structure Factor Properties

### S(0) Limit

At $Q = 0$, the structure factor approaches:

$$S(0) = \frac{\langle Z \rangle^2}{\langle Z^2 \rangle}$$

where $Z_i$ is the atomic number of element $i$:

$$\langle Z \rangle = \sum_i c_i Z_i$$

$$\langle Z^2 \rangle = \sum_i c_i Z_i^2$$

This limit is used for extrapolation to $Q = 0$.

### High-Q Behavior

At large $Q$, the structure factor approaches:

$$S(Q) \rightarrow 1$$

## Fourier Transform to F(r)

The reduced pair distribution function $F(r)$ is obtained by sine Fourier transform of $Q[S(Q) - 1]$:

$$F(r) = \frac{2}{\pi} \int_0^\infty Q[S(Q) - 1] \sin(Qr) \, dQ$$

### Modification Function

To reduce truncation effects from finite $Q_{\max}$, a modification (damping) function $M(Q)$ can be applied:

$$F(r) = \frac{2}{\pi} \int_0^{Q_{\max}} Q[S(Q) - 1] M(Q) \sin(Qr) \, dQ$$

Common modification functions include:

**Lorch modification:**

$$M(Q) = \frac{\sin(\pi Q / Q_{\max})}{\pi Q / Q_{\max}}$$

This function smoothly damps oscillations near $Q_{\max}$ to zero, reducing truncation ripples in real space.

### Implementation Methods

Glassure supports two Fourier transform methods:

1. **Direct integration** - Numerical integration using the equations above
2. **FFT (Fast Fourier Transform)** - Efficient algorithm for evenly-spaced data

## Pair Correlation Function g(r)

The pair correlation function $g(r)$ describes the probability of finding an atom at distance $r$ from another atom, relative to the average density.

The relationship between $F(r)$ and $g(r)$ is:

$$F(r) = 4\pi r \rho_0 [g(r) - 1]$$

Therefore:

$$g(r) = \frac{F(r)}{4\pi r \rho_0} + 1$$

where $\rho_0$ is the atomic number density in atoms/Å³.

### Physical Interpretation

- $g(r) = 0$ for $r < r_{\min}$ (no atoms closer than minimum interatomic distance)
- $g(r) \rightarrow 1$ as $r \rightarrow \infty$ (approaches bulk density at large distances)
- Peaks in $g(r)$ correspond to preferred interatomic distances (coordination shells)

## Radial Distribution Function RDF(r)

The radial distribution function gives the number of atoms in a shell at distance $r$:

$$\text{RDF}(r) = 4\pi r^2 \rho_0 g(r)$$

## Total Correlation Function T(r)

An alternative representation is the total correlation function:

$$T(r) = 4\pi r \rho_0 g(r)$$

which is related to $F(r)$ by:

$$T(r) = F(r) + 4\pi r \rho_0$$

## Density Calculation

The atomic number density $\rho_0$ (in atoms/Å³) is calculated from the mass density $\rho_m$ (in g/cm³):

$$\rho_0 = \frac{\rho_m \cdot N_A \cdot \sum_i c_i}{M \cdot 10^{24}}$$

where:

- $N_A = 6.022 \times 10^{23}$ mol⁻¹ is Avogadro's number
- $M = \sum_i c_i M_i$ is the average atomic mass
- $M_i$ is the atomic mass of element $i$
- The factor $10^{24}$ converts from cm⁻³ to Å⁻³

## Optimization Methods

### Kaplow Optimization (Iterative Method)

The Kaplow method iteratively improves $S(Q)$ by enforcing $g(r) = 0$ for $r < r_{\text{cutoff}}$:

1. Calculate $F(r)$ from current $S(Q)$
2. Set $F(r) = -4\pi r \rho_0$ for $r < r_{\text{cutoff}}$ (to make $g(r) = 0$)
3. Inverse Fourier transform to get correction to $S(Q)$
4. Update $S(Q)$ and iterate

This removes unphysical negative values in $g(r)$ at low $r$ that arise from experimental artifacts. More details can be found in Kaplow et al. (1965) and
Eggert et al. (2002).

### Fit Optimization Method

An alternative described in Juhás et al. (2013) fits a polynomial to $S[S(Q)-1]$ under the assumption that the
the polynomial will correct any additive errors in $Q[S(Q) - 1]$. The order of the polynoimial can be specified to
not affect oscillations in g(r) up to a certain r-value. The fit will not affect oscillations in g(r) up
to r = n\*pi/Qmax, where n is the order of the polynomial.

## Corrections

### Incoherent (Compton) Scattering

The incoherent scattering intensity is calculated using the form factors:

$$I_{\text{inc}}(Q) = \sum_i c_i [f_i^2(0) - f_i^2(Q)]$$

### Klein-Nishina Correction

For high-energy X-rays, the Klein-Nishina correction accounts for the reduction in incoherent scattering:

$$K(Q) = \frac{1 + \cos^2(2\theta)}{2}$$

where $\theta$ is related to $Q$ and wavelength $\lambda$ by:

$$Q = \frac{4\pi \sin\theta}{\lambda}$$

### Soller Slit Correction

For data collected with Soller slits, a geometric correction can be applied to account for the angular acceptance of the collimation system.

## Extrapolation to Q = 0

Since measurements cannot start at $Q = 0$, extrapolation is required. Common methods:

1. **Step function** - Set $S(Q) = S(0)$ for $Q < Q_{\min}$
2. **Linear** - Linear extrapolation from first few points to $S(0)$
3. **Polynomial** - Polynomial fit to low-Q region
4. **Spline** - Smooth spline interpolation

All methods constrain $S(0)$ to the theoretical value $\langle Z \rangle^2 / \langle Z^2 \rangle$.

## References

1. Egami, T., & Billinge, S. J. (2003). _Underneath the Bragg peaks: structural analysis of complex materials_. Elsevier.

2. Keen, D. A. (2001). A comparison of various commonly used correlation functions for describing total scattering. _Journal of Applied Crystallography_, 34(2), 172-177.

3. Eggert, J. H., et al. (2002). Quantitative structure factor and density measurements of high-pressure fluids in diamond anvil cells by x-ray diffraction. _Physical Review B_, 65(17), 174105.

4. Kaplow, R., et al. (1965). Atomic arrangement in vitreous selenium. _Physical Review_, 138(5A), A1336.

5. Juhás, P., et al. (2013). PDFgetX3: a rapid and highly automatable program for processing powder diffraction data into total scattering pair distribution functions. _Journal of Applied Crystallography_, 46(2), 560-566.
