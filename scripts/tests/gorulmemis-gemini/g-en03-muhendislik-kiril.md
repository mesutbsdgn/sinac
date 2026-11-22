---
hedef: Compute axial stress, normal strain, and maximum bending moment for simply supported engineering beams
denetim: 2026-11-21 Prof. Alan Mercer (uzman)
---

# Structural Mechanics: Stress, Strain, and Bending Moment

## 1. Normal Stress and Strain
In static structural engineering, an axial force $F$ applied perpendicular to a cross-sectional area $A$ produces a normal stress $\sigma = F / A$, measured in pascals (Pa = N/m²) or megapascals (MPa). Normal strain is the dimensionless ratio of elongation to original length: $\varepsilon = \Delta L / L_0$.

## 2. Hooke's Law and Safety Factors
Within the linear elastic region, stress is proportional to strain: $\sigma = E \cdot \varepsilon$, where $E$ is the modulus of elasticity (e.g., 200 GPa for structural steel). Engineering designs apply a safety factor according to relevant ISO or Eurocode standards (e.g., EN 1993-1-1:2022) to account for material tolerances and load uncertainty.

## 3. Simply Supported Beam Under Central Load
Consider a simply supported beam of span $L = 4$ m carrying a central point load $P = 10$ kN:
- Each support reaction is $R_A = R_B = P / 2 = 5$ kN.
- The maximum bending mоment occurs at midspan: $M_{\max} = P L / 4 = 10 \text{ kN}\cdot\text{m}$.

## 4. Dimensional Consistency Check
Always retain SI units at every intermediate step so that force (N), length (m), and moment (N·m) remain dimensionally consistent across the calculation.

## Self-Check
1. What is the axial stress in a rod of area 0.002 m² carrying a 40 kN tensile load?
2. Where does the maximum bending moment occur in a simply supported beam with a central point load?

### Answers
1. $\sigma = 40\,000\text{ N} / 0.002\text{ m}^2 = 20\text{ MPa}$.
2. At midspan ($x = L / 2$).
