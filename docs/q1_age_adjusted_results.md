# Age-adjusted secondary Cox model — results (2026-11-11)

This follows `q1_age_adjusted_plan.md`, which was committed in `e117f03` before this
model was fitted. It is a **secondary analysis added after the primary plan**, at the
owner's direction (option (b)), to address "after accounting for drive age" in the
approved proposal. The primary results are unchanged.

- **Output:** `results/survival/cox_age_adjusted.json`
- **Reproduce with:** `PYTHONPATH=src python scripts/fit_q1_age_adjusted.py --check`

## Inputs
- The Q1 ZIP was re-downloaded in this session. It matched exactly: 1,312,921,361 bytes,
  SHA1 `23448d57…0b13c`.
- The unchanged builder (with the CRC32 guard) reproduced `cohort_drives.csv` and
  `cohort_accounting.csv` byte for byte.
- The committed summary and group counts passed their `--check` scripts.
- 18,533 drives and 111 recorded failures, the same as the primary analysis.

## Baseline powered years (baseline SMART 9 ÷ 8,766)

| Group | n | Min | Q1 | Median | Q3 | Max |
|---|---|---|---|---|---|---|
| 197 = 0 | 18,371 | 0.32 | 5.50 | 5.73 | 6.04 | 6.23 |
| 197 > 0 | 162 | 0.16 | 5.63 | 6.00 | 6.18 | 6.23 |

No zero counters and no missing values. This is powered-on time, not installation age.

## Model: SMART 197 status + powered years (linear), Efron ties

| Term | HR | 95% CI | Wald p | PH test p |
|---|---|---|---|---|
| SMART 197 > 0 | **43.6** | 28.4–66.9 | 9.5e−67 | 0.0070 |
| Powered years (per year) | 1.11 | 0.85–1.43 | 0.44 | 0.92 |

- **Unadjusted primary HR, for comparison:** 43.2 (28.1–66.3).
- **Interpretation:** adjusting for powered time leaves the SMART 197 association
  essentially unchanged, and shows no detectable age gradient. But almost all drives
  lie between 5.5 and 6.2 powered years, so this adjusts for age only within a narrow
  range. It cannot speak to younger or older drives.
- **Cross-check:** lifelines and statsmodels agree to 7.7e−9, and the maximum |score| at
  the solution is 6.6e−11.

## Numerical deviation (no model change)

The damped lifelines fit used in the primary analysis stopped with |score| of about
1e−4 when there are two covariates. A full-Newton refinement, started at the damped
solution on lifelines' standardised scale, converges to the same maximum as
statsmodels.
