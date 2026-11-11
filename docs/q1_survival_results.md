# Q1 2026 `ST12000NM0008` survival results (2026-11-10)

**Scope.** These are the pre-specified analyses in `q1_analysis_plan.md`, run after
the design decisions (D1–D9) were recorded.

- **Decisions recorded before group counts were read:** 2026-11-10 20:59 UTC.
- **Plan recorded before fitting:** 2026-11-10 21:05 UTC.
- **Outputs:** `results/survival/cox_summary.json`,
  `results/survival/km_estimates.csv` (full step tables) and
  `results/survival/km_primary.png`.
- **Reproduce with:** `PYTHONPATH=src python scripts/fit_q1_survival.py --check`.

**Inputs verified before fitting.**

- The cohort, linkage and decision files match their recorded hashes.
- The gap episodes were re-derived by re-streaming the verified Q1 ZIP through the
  unchanged builder. The rerun reproduced `cohort_drives.csv` byte-for-byte.

**Population and exclusions.**

- 18,533 included drives, 111 recorded failures, follow-up day 0 to 89.
- Excluded by design (D7): 116 later arrivals (17 of them with failures) and 1 drive
  with a failure flag on the baseline date.

## 1. Kaplan–Meier by baseline SMART 197 (95% CI, log(−log) Greenwood)

| Analysis | Group | n | Failures | S(30) | S(60) | S(89) |
|---|---|---|---|---|---|---|
| P (primary) | 197 = 0 | 18,371 | 83 | 0.9989 (0.9982–0.9993) | 0.9976 (0.9968–0.9982) | **0.9955** (0.9944–0.9964) |
| P (primary) | 197 > 0 | 162 | 28 | 0.9007 (0.8431–0.9380) | 0.8635 (0.8001–0.9079) | **0.8262** (0.7583–0.8766) |
| S1 (exits) | 197 = 0 | 18,371 | 83 | 0.9989 | 0.9976 | 0.9955 |
| S1 (exits) | 197 > 0 | 162 | 28 | 0.9007 | 0.8635 | 0.8262 |
| S2 (gaps) | 197 = 0 | 18,371 | 83 | 0.9989 | 0.9976 | 0.9955 (0.9944–0.9963) |
| S2 (gaps) | 197 > 0 | 162 | 28 | 0.8999 (0.8418–0.9375) | 0.8620 (0.7980–0.9069) | 0.8235 (0.7546–0.8746) |

**Numbers at risk, primary analysis**

| Group | Day 0 | Day 30 | Day 60 | Day 89 |
|---|---|---|---|---|
| 197 = 0 | 18,371 | 18,349 | 18,324 | 18,195 |
| 197 > 0 | 162 | 145 | 139 | 131 |

- In the 197 > 0 group, about 10% failed within the first 30 days, and about 4% in
  each later 30-day span.
- S1 leaves every survival estimate unchanged to four decimals. Moving the 93
  reappeared exits to day 89 enlarges the later risk sets, but those sets have
  thousands of drives (or, in the 197 > 0 group, only 2 moved drives), so the change
  stays below that precision.

## 2. Cox model (single binary covariate, 197 > 0 versus 197 = 0, Efron ties)

| Analysis | HR | 95% CI | Wald p | PH test (scaled Schoenfeld, rank time) |
|---|---|---|---|---|
| P | **43.2** | 28.1–66.3 | 1.7e−66 | χ² = 7.29, **p = 0.0069** |
| S1 | 43.2 | 28.1–66.3 | 1.7e−66 | χ² = 7.30, p = 0.0069 |
| S2 | 44.1 | 28.7–67.7 | 3.5e−67 | not computed (see §3) |

- **Cross-check:** for every analysis, statsmodels `PHReg` agrees with lifelines on the
  coefficient to ≤ 1e-8. The partial-likelihood score at the reported solution is
  ≈ 0 (|score| ≤ 1e-10).

**Reading the PH test.** It rejects proportional hazards at conventional levels in P
and S1. The 197 > 0 group's excess hazard is concentrated early in the window (see
§1), so the HR is a quarter-average of a ratio that changes over time; it is not a
constant effect. Per the plan, the test is reported, not used to change the model.

## 3. Deviations from the plan (numerical and reporting only; no model change)

1. **Optimiser damping.**
   - **Problem:** with default settings, both engines diverged from β = 0. The full
     Newton step overshoots and `exp()` overflows, because exposure is rare (162 of
     18,533) and the effect is strong.
   - **Fix:** lifelines uses step size 0.1, and statsmodels uses BFGS from 0.
   - **Why this is safe:** the Cox partial likelihood with one covariate is concave, so
     damping changes only the path. The maximum was confirmed by score ≈ 0 and lower
     log-likelihood on both sides.
2. **statsmodels entry convention.** statsmodels treats a drive entering at day *t* as
   at risk at *t*. lifelines and the plan use start < *t* ≤ stop, and 1,273 S2
   re-entry days coincide with event days. The cross-check therefore uses entry + 0.5
   day, which is exact for whole-day times. Without it the engines disagreed by
   1.7e−3 on the S2 coefficient.
3. **KM at-risk counts.** lifelines' `event_table` at-risk column also counts drives
   entering at *t*, although its estimate uses the strict risk set. The reported
   at-risk numbers are computed directly as start < *t* ≤ stop. Every KM step is
   re-checked against the product limit on those counts.
4. **PH test for S2.** lifelines 0.30.0 offers no PH test for start/stop
   (`CoxTimeVaryingFitter`) fits, so it was not computed for S2.

## 4. How to read these results (limitations)

- **Recorded failures, conditional cohort.** The outcome is a Backblaze failure
  flag within an 89-day window, among drives already in service on Jan 1 (prevalent
  cohort, left truncation). The HR and survival estimates are not lifetime risk, not
  a causal effect of SMART 197, and not a prediction rule.
- **Possible circularity in the outcome.** If Backblaze's operational failure
  definition includes proactive removal of drives with warning signs, part of the
  association could reflect that decision process rather than spontaneous failure.
  Backblaze's published definition does count SMART-triggered proactive
  replacements as failures, so the result is read as an association.
- **Non-proportional hazards** (§2). Report the KM curves and landmark survival
  alongside the HR.
- **Small exposed group.** 162 drives with 28 failures give wide CIs (HR 28–66).
- **Exit sensitivity.** Exits do not drive the result (S1). Still, 4 April failure
  flags among reappeared exits mean exits are not wholly uninformative (D3).
- **Failure dating.** 21 of the 44 gap-preceded failures were flagged on the return
  day (D5). Removing gap days (S2) changes the HR by about 2%.
- **Overlapping warnings.** 110 of the 162 drives that are 197 > 0 are also 5 > 0
  (D8). The HR is not specific to sector-reallocation versus pending-sector signals.
- **Scope.** One model, one quarter. The SMART 9 descriptor and the 197 magnitude are
  not used.
