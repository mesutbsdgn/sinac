---
hedef: Fit a simple linear regression model and interpret hypothesis test statistics in Python 3.12
denetim: 2026-11-21 Dr. Kevin Patel (uzman)
---

# Linear Regression and Hypothesis Testing in Python 3.12

## 1. Statistical Model and Assumptions
Simple linear regression models a continuous response variable $y$ as a linear function of a predictor $x$: $y_i = \beta_0 + \beta_1 x_i + \varepsilon_i$. Valid inference requires linearity, independent observations, homoscedasticity, and approximately normal residuals. Correlation alone never establishes causation.

## 2. Worked Example in Python 3.12
Using Python 3.12 and `scipy.stats` (v1.14), we evaluate whether wind speed (measured in m/s, e.g., baseline 2.0 m/s) predicts solar panel cooling efficiency:

```python
from scipy import stats

wind_ms = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
efficiency = [18.1, 18.4, 18.9, 19.2, 19.7, 20.1]
res = stats.linregress(wind_ms, efficiency)
print(f"slope={res.slope:.2f}, r={res.rvalue:.3f}, p={res.pvalue:.4f}")
```

## 3. Interpreting the Output
Suppose a broader field dataset ($n = 42$) yields a slope of 0.78 percentage points per m/s, 95% confidence interval [0.04, 1.52], and $p = .04$. The p-value measures how compatible the data are with the null hypothesis ($\beta_1 = 0$), not the probability that the null hypothesis is true. Always report effect size and confidence intervals alongside the p-value.

## Self-Check
1. List two diagnostic assumptions that should be checked on regression residuals.
2. Why is it incorrect to interpret $p = .04$ as "a 4% chance that the null hypothesis is true"?

### Answers
1. Homoscedasticity (constant variance) and approximate normality of residuals (plus independence).
2. A p-value is calculated assuming the null hypothesis is true; it is $P(\text{data as extreme} \mid H_0)$, not $P(H_0 \mid \text{data})$.
