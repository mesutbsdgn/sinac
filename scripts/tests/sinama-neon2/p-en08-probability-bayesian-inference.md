---
hedef: Derive posterior distributions for binomial proportions using Beta conjugate priors and interpret credible intervals.
denetim: 2026-11-21 Prof. Martin Alvarez (uzman)
---

# Probability and Statistics: Bayesian Updating with Conjugate Priors

**Course:** Mathematical Statistics II — Lecture 8 Handout

## 1. Historical Context and Bayes' Theorem

Reverend Thomas Bayes, who passed away at age 59 in 1761, left the posthumous essay on inverse probability later edited by Richard Price. In Bayesian inference, an unknown proportion $\theta \in (0, 1)$ is modeled as a random variable whose probability distribution updates as new data arrive:

$$p(\theta \mid y) \propto p(y \mid \theta)\, p(\theta)$$

Unlike frequentist confidence intervals, a 95% Bayesian credible interval directly states the posterior probability that $\theta$ lies within the interval given the prior and observed data.

## 2. The Beta-Binomial Conjugate Family

When the likelihood is $\text{Binomial}(n, \theta)$ and the prior is $\text{Beta}(\alpha, \beta)$, the posterior remains in the Beta family with updated parameters $\alpha' = \alpha + k$ and $\beta' = \beta + (n - k)$ after observing $k$ successes in $n$ independent trials.

| Prior Choice | Parameters $(\alpha, \beta)$ | Prior Mean | Interpretation |
| --- | --- | --- | --- |
| Uniform (flat) | (1, 1) | 0.50 | Equal density on (0, 1) |
| Jeffreys prior | (0.5, 0.5) | 0.50 | Reparameterization-invariant |
| Weakly informative | (2.0, 2.0) | 0.50 | Mild skepticism toward extremes |

Starting from a Beta(2.0, 2.0) prior with mean 0.50, observing 620 successes in 1,000 trials yields a Beta(622.0, 382.0) posterior. The posterior mean is $622 / 1004 \approx 0.6195$, which is a precision-weighted average of the prior mean and the sample proportion $0.620$.

## 3. Comparing Frequentist and Bayesian Summaries

- Under a null hypothesis p = .5, the two-sided p-value drops below .01 once sample size exceeds 100 for a true proportion near 0.63.
- As $n \to \infty$, the likelihood dominates any strictly positive prior (Bernstein–von Mises theorem).
- Sensitivity analysis requires refitting the model under at least two alternative priors to verify that conclusions are robust.

## 4. Self-Check Questions

1. Why is the Beta distribution called a conjugate prior for the Binomial likelihood?
2. How can the hyperparameters $\alpha$ and $\beta$ be interpreted in terms of prior pseudo-observations?
3. Explain the conceptual difference between a 95% confidence interval and a 95% credible interval.
4. When does prior selection have the strongest influence on the posterior distribution?
