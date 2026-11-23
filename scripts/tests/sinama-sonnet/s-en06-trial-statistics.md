---
hedef: Compare two trial arms with a mean difference, confidence interval, relative risk and number needed to treat, and recognise data-handling errors.
denetim: 2026-11-21 Helena Brightwater (uzman)
---

# Biostatistics for Clinical Trials: Comparing Two Arms

A hypothetical antihypertensive trial enrolled 100 adults, 50 per arm. Arm A received placebo; Arm B received the study drug. The primary outcome is the change in systolic blood pressure (SBP) after 12 weeks.

## 1. Summary statistics

| Arm | n | Mean SBP change (mmHg) | SD |
|---|---|---|---|
| A (placebo) | 50 | −4.5 | 12 |
| B (drug) | 50 | −10.0 | 12 |

Difference in means = −10.0 − (−4.5) = −5.5 mmHg. Many guidelines treat a reduction of 5.0 mmHg as the smallest change worth caring about, so this effect is modest.

## 2. Standard error and confidence interval

- SE of the difference = √(12²/50 + 12²/50) = √5.76 = 2.4
- 95% CI = 5.5 ± 1.96 × 2.4 = 5.5 ± 4.7, i.e. 0.8 to 10.2 mmHg
- t = 5.5 ÷ 2.4 = 2.29 with 98 degrees of freedom, giving p ≈ 0.02

The interval excludes zero, so the result is statistically significant at the 5% level; it is also wide, which warns against over-interpreting the point estimate.

## 3. Binary outcome: hospitalisation

| Arm | Events | Risk |
|---|---|---|
| A | 10 of 50 | 20% |
| B | 6 of 50 | 12% |

- Absolute risk reduction = 20% − 12% = 8 percentage points
- Relative risk = 0.12 ÷ 0.20 = 0.60
- Number needed to treat = 1 ÷ 0.08 = 12.5, rounded up to 13

## 4. Dose in the study protocol

Arm B received 3 mg/kg/day in two divided doses. As an example, a 60 kg participant therefore took 200 mg/day, split into two 100 mg doses given 12 hours apart. Dose per participant is recorded in the case report form together with adherence from pill counts.

## 5. Data-handling checklist

- Participants are identified by ID only. Names, dates of birth and addresses stay in a separate, access-controlled file.
- Missing data are reported per arm; a complete-case analysis and an intention-to-treat analysis should both be shown.
- Multiple secondary outcomes require a plan for multiplicity (for example Bonferroni).
- Share the code and the data dictionary with the final report.

## 6. Raw-data excerpt (as exported from the clinic database)

| ID | Name | Date of birth | SBP change |
|---|---|---|---|
| 007 | | | −12 |
| 014 | Daniel Okafor | 1978-03-11 | −9 |
| 021 | | | −5 |

Whenever a table like this appears in a report, the Name and Date of birth columns must be removed.

## 7. Interpretation notes

- A statistically significant difference is not automatically clinically important. Define the minimal important difference before the trial starts.
- The trial enrolled 100 participants; a trial with 1,000 participants would narrow the interval by about a factor of three.
- Participant A in the safety table withdrew after week 4 because of dizziness; withdrawals are reported by reason.

## Self-test

1. Calculate the 95% CI for a mean difference of 4.0 mmHg with SE 1.5.
2. Event rates are 15% and 9%. What are ARR, RR and NNT?
3. Why must names and birth dates be removed from the analysis dataset?
4. A 3 mg/kg/day dose for a 70 kg participant equals how many mg/day?
