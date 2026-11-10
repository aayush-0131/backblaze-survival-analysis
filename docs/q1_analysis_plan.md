# Q1 2026 `ST12000NM0008` survival analysis — pre-specified plan (2026-11-10)

**Authority.** D1–D9 were signed by the owner (Aayush) on 2026-11-10; see
`q1_decision_record.md`. This plan turns those decisions and `q1_minimal_path.md`
§2 step 4 ("descriptive Kaplan–Meier curves by baseline state with Q1 calendar
follow-up, plus at most one simple Cox model; unexplained exits and gaps get
sensitivity analyses") into an exact specification. It is **committed before any
model is fitted**. It adds no new research question, covariate or outcome.

**Open prerequisite.** D9 required a joint review with the teammate
SMART/literature audit. No such review is documented in the repository. The owner
signed D9 regardless, so the gap is carried as a limitation.

## 1. Data
- **Cohort:** the 18,533 included drives in the verified builder output
  (`cohort_drives.csv`, sha256 `beccd1a1…d552`). Hashes are re-verified before use.
- **Time origin:** 2026-01-01 (day 0). **Time scale:** calendar days. Maximum
  follow-up is day 89 (2026-03-31).
- **Event:** the first `failure == 1` date after baseline, on the flag date (D5).
  The first flag is terminal (D6). There are 0 post-failure rows and 0 repeated
  flags.
- **Censoring:** Mar 31 for drives present then (D2). Unexplained exits are
  censored at their last observed day (D3 primary). Exits are never events.
- **Exposure:** baseline SMART 197 raw, nonzero versus zero, from the Jan 1 row
  only (D1). The missing group is empty. SMART 5 is not analysed (D1 kept 197), and
  SMART 9 is not used.
- **Excluded by design and reported:** 116 later arrivals (17 with failures) and
  1 drive with a failure flag on the baseline date (D7).

## 2. Analyses
| ID | Purpose | Change from primary |
|---|---|---|
| P | Primary | none: at risk throughout gaps (D4 primary), exits censored at last observed day (D3 primary) |
| S1 | Exits (D3 sensitivity) | The 93 exits verified to reappear on Apr 1–14 are censored at day 89. The 3 unresolved January exits stay censored at their last observed day |
| S2 | Gaps (D4 sensitivity) | Gap days are removed from the risk set with start/stop intervals. A day *d* on which the drive is observed contributes the interval (*d*−1, *d*]. A gap between last-seen day *L* and return day *R* removes (*L*, *R*−1], so an event flagged on the return day *R* remains in the risk set |

Gap episode dates are re-derived by re-streaming the verified Q1 ZIP through the
unchanged cohort builder. That rerun must reproduce `cohort_drives.csv`
byte-for-byte, otherwise the analysis stops.

## 3. Estimators (identical in P, S1 and S2)
- **Kaplan–Meier** survival by baseline SMART 197 group (zero, nonzero).
  - CIs: 95% pointwise, exponential Greenwood (log(−log)), the lifelines default.
  - S2 uses counting-process risk sets (delayed entry per interval).
  - Reported: full step tables; S(t) with CI at days 30, 60 and 89; numbers at risk
    at days 0, 30, 60 and 89.
- **One Cox proportional-hazards model:** a single binary covariate (197 nonzero = 1,
  zero = 0), Efron ties, no other covariates and no stratification.
  - Reported: HR, 95% Wald CI and Wald p-value.
  - The same specification is refit on S1 and S2; no other Cox model is fitted.
  - **PH check:** the Grambsch–Therneau-type test on scaled Schoenfeld residuals
    (lifelines `proportional_hazard_test`, rank time transform). It is reported, not
    used to alter the model.
- **Software:** lifelines 0.30.0 is the reported engine. statsmodels 0.15.0 `PHReg`
  (Efron, with entry times for S2) is an independent cross-check, and coefficient
  agreement to within 1e-6 is required.
- **Not done:** no log-rank test, SMART 5 model, covariate adjustment, interaction,
  time-varying effect or model selection.

## 4. Interpretation limits (stated with every result)
- **Conditional association.** Results describe the hazard of a *recorded* failure
  flag within Q1, among drives present on Jan 1 (a prevalent cohort with left
  truncation). They are not lifetime risk and not a causal effect of SMART 197.
- **Exits may be informative.** 4 April failure flags were observed among
  reappeared exits (D3).
- **Failure dating.** 21 of the 44 gap-preceded failures were flagged on the
  return day (D5), so recorded event dates may be ascertainment dates.
- **Gaps differ by group.** 22% of 197-nonzero drives have gaps versus 10% of
  197-zero drives.
- **Group overlap.** 110 of the 162 drives that are 197-nonzero are also 5-nonzero
  (D8).
- **Short window.** 89 days, and a single model and quarter.
- **No group review.** D1–D8 were selected by Claude and signed by the owner. The
  joint review with the teammate audit has not happened.

## 5. Outputs (aggregate only)
- **Committed:** `results/survival/km_estimates.csv`, `results/survival/cox_summary.json`
  and `results/survival/km_primary.png`. They are reproducible with
  `scripts/fit_q1_survival.py --check`.
- **Kept out of Git:** serial-level analysis frames and gap intervals, in the
  ignored `data/processed/q1_survival/`.
