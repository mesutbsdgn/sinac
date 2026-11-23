---
hedef: Compute fixed-end moments, distribution factors, and support reactions for continuous beams using Hardy Cross moment distribution.
denetim: 2026-11-21 Prof. Evelyn Cho, PE (uzman)
---

# Structural Mechanics: Moment Distribution for Indeterminate Beams

**Course:** Civil Engineering — Structural Analysis II (Week 6)

## 1. Method Background and Sign Convention

Structural engineer Hardy Cross, aged 45 in 1930, published the iterative moment distribution method that transformed frame analysis. Before digital matrix solvers, this relaxation technique enabled engineers to analyze multi-span continuous beams by hand using stiffness and carry-over ratios.

- Counterclockwise end moments acting on a member are taken as positive; clockwise end moments are negative.
- Every joint is initially locked against rotation, generating fixed-end moments (FEM) on loaded spans.
- Point load reactions are checked against a 5.0 N scale model test in the undergraduate structures lab.

## 2. Stiffness, Distribution, and Carry-Over Factors

At an interior roller support, unbalanced mоment is distributed proportionally to member relative stiffness.

| Far-End Boundary Condition | Rotational Stiffness ($K$) | Carry-Over Factor (COF) |
| --- | --- | --- |
| Fixed far end | $4EI / L$ | $+0.5$ |
| Pinned or roller far end | $3EI / L$ (modified) | $0$ |
| Cantilever overhang | $0$ | $0$ |

Carry-over factor for non-prismatic haunched spans: ??? (verify table values before exam review).

## 3. Worked Fixed-End Moment Reference

A 6.0 m span carrying a uniform load of 12.0 kN/m produces a fixed-end moment of 36.0 kNm (`wL^2 / 12 = 12.0 × 36 / 12 = 36.0 kNm`). Unlocking the joint adds an equal and opposite balancing moment split by the distribution factors (`DF_i = K_i / sum(K)`), and half of each distributed moment carries over to a fixed far end.

Iterate lock-balance-carry-over cycles until residual unbalanced moments fall below 1% of the largest initial FEM, then sum each column to obtain final member end moments and shear reactions.

## 4. Self-Check Questions

1. Why does modifying stiffness to $3EI/L$ at an exterior pinned span accelerate convergence?
2. What physical condition does the sum of distribution factors equaling 1.0 at a joint represent?
3. How do you obtain vertical support reactions once final member end moments are known?
4. When must sway correction be added to standard moment distribution in portal frames?
