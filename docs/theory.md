# Theoretical Background

This document summarizes the conventions and equations implemented by Glassure for
isotropic X-ray total-scattering data. Glassure uses the **Faber–Ziman** definition
of the total structure factor. This convention matters for multicomponent samples,
because other definitions (for example, Ashcroft–Langreth) use different partial
structure factors and normalizations.

## Processing overview and notation

Glassure performs the following main steps:

1. subtract a scaled background pattern;
2. normalize the corrected intensity and subtract incoherent scattering;
3. calculate the Faber–Ziman total structure factor $S(Q)$;
4. extrapolate $S(Q)$ to $Q=0$ and optionally optimize it;
5. Fourier transform $S(Q)$ to the reduced real-space function $F(r)$; and
6. calculate $g(r)$ and related real-space functions.

The magnitude of the scattering vector is

$$
Q = \frac{4\pi\sin\theta}{\lambda},
$$

where $2\theta$ is the scattering angle and $\lambda$ is the incident X-ray
wavelength. Glassure expects $Q$ in $\mathrm{\AA}^{-1}$ and distances in
$\mathrm{\AA}$.

The intensity supplied to the normalization routines should already contain any
experiment-specific corrections that are not explicitly provided by Glassure, such
as detector, polarization, absorption, and general sample-geometry corrections.
The optional corrections implemented by Glassure are described below.

## Atomic form factors

For a sample containing species $i$ with atomic fractions $c_i$, where
$\sum_i c_i=1$, Glassure calculates

$$
\langle f(Q)\rangle = \sum_i c_i f_i(Q)
$$

and

$$
\langle f^2(Q)\rangle = \sum_i c_i f_i^2(Q).
$$

Here $f_i(Q)$ is the coherent atomic X-ray form factor in electron units. Notice
the distinction between $\langle f^2\rangle$ and $\langle f\rangle^2$.
The available sources provide real, neutral-atom form factors; Glassure does not
currently add energy-dependent anomalous-dispersion terms $f'$ and $f''$.

## Faber–Ziman structure factor

After normalization and incoherent-scattering subtraction, the coherent intensity
per atom is related to the Faber–Ziman total structure factor by

$$
I_{\mathrm{coh}}(Q)
= \langle f^2(Q)\rangle
+ \langle f(Q)\rangle^2[S(Q)-1].
$$

Glassure therefore calculates

$$
S(Q)
= \frac{I_{\mathrm{coh}}(Q)-\langle f^2(Q)\rangle}
       {\langle f(Q)\rangle^2}+1.
$$

This is the normalization implemented by `calculate_sq()`.

In the Faber–Ziman formalism, the total structure factor can be written as a
weighted sum of partial structure factors:

$$
S(Q) = \sum_i\sum_j w_{ij}(Q)S_{ij}^{\mathrm{FZ}}(Q),
$$

with the ordered-pair weights

$$
w_{ij}(Q)
= \frac{c_i c_j f_i(Q)f_j(Q)}{\langle f(Q)\rangle^2},
\qquad
\sum_i\sum_j w_{ij}(Q)=1,
$$

and

$$
S_{ij}^{\mathrm{FZ}}(Q)
= 1 + 4\pi\rho_0\int_0^\infty
  r^2[g_{ij}(r)-1]\frac{\sin(Qr)}{Qr}\,dr.
$$

Equivalently, when summing only unique pairs $i\leq j$, the weight numerator
contains the factor $(2-\delta_{ij})$. For X-rays, the weights generally depend on
$Q$ because the atomic form factors depend on $Q$.

## Intensity normalization

Let $I_{\mathrm{corr}}(Q)$ denote the background-subtracted and otherwise corrected
experimental intensity in arbitrary units. Glassure provides two normalization
methods.

### Krogh–Moe–Norman integral normalization

The integral method uses the sum rule

$$
\int_0^\infty Q^2[S(Q)-1]\,dQ = -2\pi^2\rho_0.
$$

For finite experimental data, Glassure applies
$A(Q)=\exp(-aQ^2)$, where $a$ is the configured attenuation factor. The implemented
normalization factor is

$$
\alpha =
\frac{
-2\pi^2\rho_0
+ \int A(Q)Q^2
  \dfrac{\langle f^2(Q)\rangle+I_{\mathrm{inc}}(Q)}
        {\langle f(Q)\rangle^2}\,dQ
}{
\int A(Q)Q^2
  \dfrac{I_{\mathrm{corr}}(Q)}{\langle f(Q)\rangle^2}\,dQ
}.
$$

The numerical integrals run over the selected experimental $Q$ range. The coherent
intensity passed to the structure-factor calculation is

$$
I_{\mathrm{coh}}(Q)=\alpha I_{\mathrm{corr}}(Q)-I_{\mathrm{inc}}(Q).
$$

### High-$Q$ fit normalization

At sufficiently high $Q$, structural oscillations become small and $S(Q)$ tends to
one. Glassure can therefore determine $\alpha$ by fitting the measured intensity to
the self-scattering plus incoherent scattering above a configured cutoff. In the
most general implemented case, it minimizes residuals proportional to

$$
Q^p\left[
\alpha I_{\mathrm{corr}}(Q)-m-\beta I_{\mathrm{container,inc}}(Q)
-\left(\langle f^2(Q)\rangle+I_{\mathrm{inc}}(Q)\right)
\right],
$$

where $p=1$ or $2$, $m$ is an optional constant approximation to multiple
scattering, and $\beta$ scales an optional incoherent container contribution.
Terms disabled in the configuration are omitted. This method depends on having a
high-$Q$ interval in which the slowly varying non-structural contributions can be
separated reliably from the structural signal.

## Related reciprocal-space functions

Glassure uses

$$
i(Q)=S(Q)-1
$$

for the interference function and

$$
F(Q)=Q[S(Q)-1]
$$

for the reduced total-scattering function in reciprocal space. The symbol $F(r)$
below denotes its sine transform; naming conventions differ across the total-
scattering literature, where $F(r)$ is also often called $G(r)$.

### Limiting behavior

At high $Q$,

$$
S(Q)\rightarrow 1.
$$

By default, Glassure extrapolates to

$$
S_{\mathrm{default}}(0)
=1-\frac{\langle f^2(0)\rangle}{\langle f(0)\rangle^2}
=1-\frac{\langle Z^2\rangle}{\langle Z\rangle^2},
$$

because $f_i(0)=Z_i$. This boundary value follows from setting the coherent
forward-scattering intensity in the equation above to zero; it is zero for a
single-component sample and can be negative for a multicomponent sample.

This is a **default extrapolation assumption, not a universal thermodynamic value
of $S(0)$**. Compressibility, concentration fluctuations, small-angle scattering,
and the treatment of the forward beam can change the physical low-$Q$ limit. The
target can therefore be overridden with `ExtrapolationConfig.s0` when an
independently justified value is available.

## Fourier transform to real space

The reduced real-space pair-distribution function is

$$
F(r)=\frac{2}{\pi}\int_0^\infty
Q[S(Q)-1]\sin(Qr)\,dQ.
$$

For measured data, Glassure evaluates the finite-range transform

$$
F(r)=\frac{2}{\pi}\int_0^{Q_{\max}}
Q[S(Q)-1]M(Q)\sin(Qr)\,dQ,
$$

after extrapolating the measured structure factor from $Q_{\min}$ to zero.

### Lorch modification function

The optional Lorch modification function is

$$
M(Q)=\frac{\sin(\pi Q/Q_{\max})}{\pi Q/Q_{\max}},
$$

with $M(0)=1$ by continuity. It suppresses the discontinuity at $Q_{\max}$ and
therefore reduces termination ripples, at the cost of broader real-space peaks and
reduced real-space resolution.

Glassure supports direct numerical integration and an FFT implementation. The FFT
method requires uniformly spaced $Q$ data; rebin irregularly spaced data before
using it.

## Real-space functions and their interpretation

Glassure defines

$$
F(r)=4\pi r\rho_0[g(r)-1]
$$

and hence

$$
g(r)=1+\frac{F(r)}{4\pi r\rho_0},
$$

where $\rho_0$ is the atomic number density in atoms/$\mathrm{\AA}^3$.

For a single-component material, $g(r)$ is the usual pair correlation function:
it approaches zero in an excluded-volume region and approaches one at long range.
For a multicomponent X-ray measurement, the total $S(Q)$ and the derived real-space
functions are scattering-weighted combinations of the partial correlations. Since
the X-ray weights are $Q$ dependent, the resulting total $g(r)$ is not generally a
simple number-weighted pair probability. Peak areas should therefore not be read as
element-specific coordination numbers without partial-structure information or a
structural model.

### Radial distribution function

Glassure calculates

$$
\operatorname{RDF}(r)=4\pi r^2\rho_0g(r).
$$

For a single-component system, integrating this function over a coordination shell
gives the corresponding coordination number. For multicomponent X-ray totals it is
an effective, scattering-weighted shell distribution with the caveat above.

### Total correlation function

Glassure also calculates

$$
T(r)=4\pi r\rho_0g(r)
=F(r)+4\pi r\rho_0.
$$

## Atomic number density

For atomic fractions $c_i$, define the mean molar mass per atom as

$$
\overline{M}=\sum_i c_iM_i.
$$

The conversion from mass density $\rho_m$ in g/cm$^3$ to atomic number density is

$$
\rho_0
=\frac{\rho_mN_A}{\overline{M}}10^{-24},
$$

where $N_A$ is Avogadro's constant and $10^{-24}$ converts cm$^{-3}$ to
$\mathrm{\AA}^{-3}$. Equivalently, for stoichiometric coefficients $n_i$,

$$
\rho_0
=\frac{\rho_mN_A\sum_i n_i}{\sum_i n_iM_i}10^{-24}.
$$

## Structure-factor optimization

Optimization reduces slowly varying systematic errors by using the physically empty
real-space region below the shortest interatomic distance. It should not be used to
replace missing experimental corrections, and the cutoff must remain below the
first physical pair-correlation peak.

### Iterative Kaplow–Eggert method

The iterative method uses the condition $g(r)=0$ for $r<r_{\mathrm{cutoff}}$, or
equivalently

$$
F(r)=-4\pi r\rho_0.
$$

Glassure repeatedly transforms $S(Q)$ to $F(r)$, back-transforms the discrepancy in
the low-$r$ interval, and updates $S(Q)$. This reduces unphysical low-$r$
oscillations but can also modify the structure factor if the cutoff, density,
background, or correction model is inappropriate.

### Polynomial fit method

The method inspired by PDFgetX3 fits a polynomial $P_n(Q)$ through the origin to

$$
F(Q)=Q[S(Q)-1]
$$

and applies

$$
S_{\mathrm{corrected}}(Q)=S(Q)-\frac{P_n(Q)}{Q}.
$$

Glassure chooses an effective degree near

$$
n\simeq\frac{Q_{\max}r_{\mathrm{cutoff}}}{\pi}
$$

and blends the fits for adjacent integer degrees when needed. The intent is to
remove slowly varying reciprocal-space components whose Fourier signal is
concentrated below $r_{\mathrm{cutoff}}$, while retaining correlations at larger
$r$. This is an ad hoc correction and its stability should be checked by varying
$Q_{\max}$ and $r_{\mathrm{cutoff}}$.

## Incoherent scattering and optional corrections

### Incoherent (Compton) scattering

For a mixture, Glassure uses

$$
I_{\mathrm{inc}}(Q)=\sum_i c_i I_{\mathrm{inc},i}(Q).
$$

The default `brown_hubbell` source interpolates tabulated incoherent scattering
functions from Hubbell et al. (1975), together with Brown coherent form factors.
The `hajdu` source uses the analytic approximation

$$
I_{\mathrm{inc},i}(Q)
=\left[Z_i-\frac{f_i^2(Q)}{Z_i}\right]
 \left[1-M_i\left(e^{-K_i s}-e^{-L_i s}\right)\right],
\qquad s=\frac{Q}{4\pi},
$$

with element-specific parameters. An `xraylib` source is also available. The simple
expression $Z-f^2/Z$ is only an independent-atom approximation; the incorrect
$Z^2-f^2$ expression is not an incoherent intensity per atom.

### Klein–Nishina correction

For high-energy X-rays, the optional Klein–Nishina correction accounts for photon
recoil in the angular dependence of Compton scattering. Let

$$
p=\frac{E'}{E}
=\left[1+\frac{h}{\lambda m_ec}(1-\cos 2\theta)\right]^{-1}.
$$

Glassure multiplies the incoherent scattering function by the Klein–Nishina to
Thomson ratio

$$
K(Q)=
\frac{p^3-p^2\sin^2(2\theta)+p}{1+\cos^2(2\theta)},
$$

using $Q=4\pi\sin\theta/\lambda$. This is distinct from the unpolarized Thomson
polarization factor $(1+\cos^2 2\theta)/2$.

### Soller-slit DAC correction

For the configured diamond-anvil-cell workflow, Glassure can apply separate
angle-dependent transfer functions for scattering from the sample region and the
additional diamond incoherent contribution. This correction is specific to the
implemented DAC/Soller-slit geometry and is not a general absorption or geometry
correction.

## Extrapolation to $Q=0$

Because measurements normally begin at finite $Q_{\min}$, Glassure supports:

1. a step extension at the target $S(0)$;
2. a linear connection to $S(0)$;
3. a polynomial extrapolation over a configurable overlap; and
4. a spline extrapolation over a configurable overlap.

Unless `ExtrapolationConfig.s0` is set explicitly, these methods use the default
boundary value described above. Polynomial and spline extrapolations can optionally
replace measured points in the overlap region.

## References

1. Faber, T. E., & Ziman, J. M. (1965). A theory of the electrical properties of
   liquid metals. III. The resistivity of binary alloys. *Philosophical Magazine*,
   11(109), 153–173. <https://doi.org/10.1080/14786436508211931>

2. Krogh-Moe, J. (1956). A method for converting experimental X-ray intensities to
   an absolute scale. *Acta Crystallographica*, 9, 951–953.
   <https://doi.org/10.1107/S0365110X56002655>

3. Norman, N. (1957). The Fourier transform method for normalizing intensities.
   *Acta Crystallographica*, 10, 370–373.
   <https://doi.org/10.1107/S0365110X57001085>

4. Lorch, E. (1969). Neutron diffraction by germania, silica and radiation-damaged
   silica glasses. *Journal of Physics C: Solid State Physics*, 2, 229–237.
   <https://doi.org/10.1088/0022-3719/2/2/305>

5. Kaplow, R., Strong, S. L., & Averbach, B. L. (1965). Atomic arrangement in
   vitreous selenium. *Physical Review*, 138, A1336–A1345.
   <https://doi.org/10.1103/PhysRev.138.A1336>

6. Eggert, J. H., Weck, G., Loubeyre, P., & Mezouar, M. (2002). Quantitative
   structure factor and density measurements of high-pressure fluids in diamond
   anvil cells by X-ray diffraction. *Physical Review B*, 65, 174105.
   <https://doi.org/10.1103/PhysRevB.65.174105>

7. Juhás, P., Davis, T., Farrow, C. L., & Billinge, S. J. L. (2013). PDFgetX3: a
   rapid and highly automatable program for processing powder diffraction data into
   total scattering pair distribution functions. *Journal of Applied
   Crystallography*, 46, 560–566.
   <https://doi.org/10.1107/S0021889813005190>

8. Hubbell, J. H., Veigele, W. J., Briggs, E. A., Brown, R. T., Cromer, D. T., &
   Howerton, R. J. (1975). Atomic form factors, incoherent scattering functions, and
   photon scattering cross sections. *Journal of Physical and Chemical Reference
   Data*, 4, 471–538. <https://doi.org/10.1063/1.555523>

9. Hajdu, F. (1972). Revised parameters of the analytic fits for coherent and
   incoherent scattered X-ray intensities of the first 36 atoms. *Acta
   Crystallographica Section A*, 28, 250–252.
   <https://doi.org/10.1107/S0567739472000671>

10. Keen, D. A. (2001). A comparison of various commonly used correlation functions
    for describing total scattering. *Journal of Applied Crystallography*, 34,
    172–177. <https://doi.org/10.1107/S0021889800019993>

11. Egami, T., & Billinge, S. J. L. (2012). *Underneath the Bragg Peaks: Structural
    Analysis of Complex Materials* (2nd ed.). Elsevier.

12. Peterson, P. F., Olds, D., McDonnell, M. T., & Page, K. (2021). Illustrated
    formalisms for total scattering data: a guide for new practitioners. *Journal
    of Applied Crystallography*, 54, 317–332.
    <https://doi.org/10.1107/S1600576720015630>

13. Brown, P. J., Fox, A. G., Maslen, E. N., O'Keefe, M. A., & Willis, B. T. M.
    (2006). Intensity of diffracted intensities. In *International Tables for
    Crystallography, Volume C*, 554–595.
    <https://doi.org/10.1107/97809553602060000600>
