---
hedef: Conduct one-way analysis of variance (ANOVA), verify parametric assumptions, and interpret post-hoc multiple comparisons.
denetim: 2026-11-21 Prof. Priya Subramanian (uzman)
---

# Applied Statistics: One-Way ANOVA and Post-Hoc Testing

Ronald A. Fisher (1890–1962) developed the analysis of variance framework at age 35 in his 1925 monograph *Statistical Methods for Research Workers*. Rather than running inflated pairwise $t$-tests across $k$ groups, ANOVA partitions total variability into between-group and within-group components.

## 1. Variance Partitioning and the F-Ratio

Total sum of squares decomposes into treatment variation and residual error:

$$\text{SS}_{\text{Total}} = \text{SS}_{\text{Between}} + \text{SS}_{\text{Within}}$$

The test statistic is the ratio of mean squares: $F = \text{MS}_{\text{Between}} / \text{MS}_{\text{Within}}$.

- With $k = 4$ groups and $N = 40$ observations, an observed statistic of F = 4.0 exceeds the critical cutoff at $\alpha = 0.05$ ($F_{3,36} \approx 2.87$).
- Simulation runs used 1,000 bootstrap resamples per condition to verify Type I error control under mild skewness.
- Report effect size alongside significance; omega-squared ($\omega^2$) provides a less biased estimate than eta-squared ($\eta^2$) in small samples.

## 2. Example ANOVA Summary Table

| Source of Variation | Sum of Squares (SS) | df | Mean Square (MS) | F-Statistic |
| :--- | :--- | :--- | :--- | :--- |
| Between Groups | 48.0 | 3 | 16.0 | 4.0 |
| Within Groups (Error) | 144.0 | 36 | 4.0 | — |
| Total | 192.0 | 39 | — | — |

## 3. Assumptions and Post-Hoc Selection

1. **Independence:** Observations within and across groups must be sampled independently.
2. **Normality:** Residuals within each group should approximate a normal distribution (inspect Q–Q plots rather than relying solely on Shapiro–Wilk).
3. **Homogeneity of variance:** Evaluate with Levene's test; if group standard deviations differ markedly (e.g., SD = 2.0 versus SD = 6.5), switch to Welch's ANOVA and Games–Howell post-hoc tests.
4. **Family-wise error control:** When equal variances hold, apply Tukey's HSD for all pairwise comparisons or Dunnett's test when comparing treatments only against a single control.

## Self-Check Questions

1. Why does running six separate two-sample $t$-tests across four groups inflate the family-wise Type I error rate above 0.05?
2. Using the summary table above, calculate $\eta^2 = \text{SS}_{\text{Between}} / \text{SS}_{\text{Total}}$.
3. Which alternative to classical ANOVA is recommended when group variances are unequal and sample sizes are unbalanced?
4. Does a statistically significant omnibus $F$-test tell you which specific pair of group means differs?
