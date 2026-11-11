# Q1 2026 ST12000NM0008 — age-adjusted secondary Cox model: pre-specified plan (2026-11-11)

**Why this exists.** The project proposal approved by the course instructor on
2026-10-06 asked whether a SMART indicator is associated with failure "after
accounting for drive age". The primary analysis (`q1_analysis_plan.md`) used calendar
time and no age adjustment. On 2026-11-11 Aayush chose to add one age-adjusted model
(option (b)). This plan is **committed before that model is fitted**. It is a
**secondary analysis added after the primary plan**, and it is reported as such. It does
not replace or change the primary results.

## Data
- **Drives:** the same verified primary cohort, 18,533 included drives.
  - `cohort_drives.csv` must reproduce its recorded sha256, or the analysis stops.
- **Time, event and censoring:** identical to the primary analysis (P). Day 0 is
  2026-01-01, follow-up runs to day 89, and the event is the first recorded failure flag.
- **Exposure:** baseline SMART 197 > 0 versus = 0 (D1).
- **Age proxy:** baseline SMART 9 raw on 2026-01-01, divided by 8,766 hours per year,
  giving `powered_years`. It is a powered-on-hours counter: it is not installation or
  physical age (`docs/smart9_semantics.md`). Baseline SMART 9 is present for every
  included drive. The 2 drives with a SMART 9 review flag are kept as recorded. Any
  zero values are kept and counted.

## Model (exactly one)
- **Cox proportional hazards:** covariates `x` (197 nonzero) and `powered_years`
  (linear), Efron ties. No other covariates, no interaction, no stratification.
- **Same numerical safeguards as the primary fit:**
  - damped lifelines fit;
  - statsmodels PHReg cross-check, with coefficients agreeing to within 1e-6;
  - score at the solution approximately 0.

## Reported
- Adjusted HR for SMART 197 > 0 (95% CI, Wald p), and HR per powered year (95% CI).
- Comparison with the unadjusted primary HR (43.2).
- Proportional-hazards test per covariate (scaled Schoenfeld, rank time). Reported, not
  used to change the model.
- Descriptive baseline `powered_years` by group: n, min, quartiles and max.

## Not done
- No spline or other nonlinear age term.
- No age-only model.
- No refit on S1 or S2, and no other variant.
- Interpretation stays associational, with the limitations in `q1_report.md` §5. In
  particular, the outcome includes proactive, SMART-informed removals.
