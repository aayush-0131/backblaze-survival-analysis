# Baseline SMART 197 status and recorded drive failure: a Q1 2026 cohort study of Seagate ST12000NM0008

ASM-II Type I project write-up, 2026-11-11. The decisions (D1–D9), the
pre-specified plan and these results were approved by Aayush and teammates on
2026-11-10/11. Every number below comes from committed artifacts:
`docs/q1_group_counts.json`, `results/survival/cox_summary.json`,
`results/survival/km_estimates.csv` and `docs/q1_survival_results.md`.

## Summary

Among 18,533 Seagate ST12000NM0008 drives in service on 1 January 2026, the 162 drives
with a nonzero SMART 197 (current pending sector count) on that day had a much higher
rate of a *recorded* failure over the next 89 days:

- **SMART 197 > 0:** 28 recorded failures. Survival to day 89 was 0.826 (95% CI 0.758–0.877).
- **SMART 197 = 0:** 83 recorded failures among 18,371 drives. Survival was 0.9955 (0.9944–0.9964).

The single-covariate Cox hazard ratio was **43.2 (95% CI 28.1–66.3)**. Both
pre-specified sensitivity analyses left it essentially unchanged: 43.2 when
unexplained exits were reclassified and 44.1 with gap days removed. Hazards were not
proportional (p = 0.0069), and most of the excess came in the first 30 days, so the
HR is a quarter-average. The result is a descriptive association. Backblaze counts
proactive removals triggered by SMART indicators as failures, so it is partly
expected by construction and must not be read as a causal or physical-failure effect.

## 1. Question and design

- **Question:** Is a nonzero SMART 197 on a fixed baseline day associated with a higher
  hazard of a *recorded* Backblaze failure flag over the following quarter?
- **Design:** prevalent fixed-baseline cohort, one drive model, calendar follow-up.
  - Baseline is 2026-01-01 (day 0), and follow-up ends 2026-03-31 (day 89).
  - Choosing one model avoids pooling capacities, firmware families and SMART
    reporting conventions.
- **Exposure:** SMART 197 raw > 0 versus = 0, taken from the baseline-day row only.
  - The decision rule for using SMART 197 rather than SMART 5 (D1) was fixed and
    committed before any per-group event count was read.
- **Outcome:** the first `failure == 1` flag after baseline, dated on the flag date.
- **Censoring:**
  - drives still present on 31 March are censored on that day;
  - drives that stopped appearing without a flag ("unexplained exits") are censored
    at their last observed day and never counted as failures.
- **Excluded by design:**
  - 116 drives first seen after 1 January, 17 of them with failures;
  - 1 drive whose failure flag fell on the baseline day.

All conventions are recorded in `docs/q1_decision_record.md` and `docs/q1_decisions.json`.

## 2. Data and quality checks

- **Source:** official Backblaze Drive Stats, Q1 2026 (90 daily files).
  - The archive's SHA1 matches the recorded value, and all 90 member CRC32s match.
  - The cohort builder reproduces the independent Q1 audit exactly: 18,650 drives,
    1,664,558 drive-days and 129 failure flags. It produces identical output on a rerun.
- **Calendar:** complete and contiguous. There are no duplicate drive-day keys, no
  post-failure rows and no repeated failure flags for this model.
- **Missing exposure:** SMART 197 and SMART 5 were present at baseline for every
  included drive, so no imputation was needed.
- **Exits:** 96 unexplained exits. A bounded April 1–14 check of later daily files
  found that 93 drives reappeared. 3 January exits remain unresolved.
- **Gaps:** 10.2% of included drives have at least one observation gap. The share is
  22% in the 197 > 0 group (36 of 162) and 10% in the 197 = 0 group (1,850 of 18,371).

## 3. Methods (pre-specified in `docs/q1_analysis_plan.md`, committed before fitting)

- **Kaplan–Meier** survival by baseline group.
  - 95% pointwise CIs use the log(−log) Greenwood method.
- **One Cox proportional-hazards model** with a single binary covariate and Efron ties.
  - The proportional-hazards check is a scaled-Schoenfeld test (rank time). It is
    reported, not used to change the model.
- **Sensitivity analyses:**
  - **S1:** the 93 exits verified to reappear are censored at day 89.
  - **S2:** gap days are removed from the risk set using start/stop intervals.
- **Software:** lifelines 0.30.0 produces the results, and statsmodels 0.15.0 is an
  independent cross-check. The coefficients agree to within 1e-8.
- **Numerical safeguards** (documented in `docs/q1_survival_results.md` §3):
  - damped optimisation, because full Newton steps overflowed;
  - a whole-day entry convention in the statsmodels cross-check;
  - at-risk counts recomputed directly.
- **Not done:** log-rank test, a SMART 5 model, covariate adjustment and model
  selection.

## 4. Results

### 4.1 Counts at baseline (included drives)

| Baseline SMART 197 | Drives | Recorded failures | Censored 31 Mar | Unexplained exits |
|---|---|---|---|---|
| 0 | 18,371 | 83 | 18,195 | 93 |
| > 0 | 162 | 28 | 131 | 3 |
| All | 18,533 | 111 | 18,326 | 96 |

### 4.2 Kaplan–Meier (primary analysis)

| Group | S(30) | S(60) | S(89) |
|---|---|---|---|
| 197 = 0 | 0.9989 (0.9982–0.9993) | 0.9976 (0.9968–0.9982) | 0.9955 (0.9944–0.9964) |
| 197 > 0 | 0.9007 (0.8431–0.9380) | 0.8635 (0.8001–0.9079) | 0.8262 (0.7583–0.8766) |

Numbers at risk on days 0, 30, 60 and 89:

- 197 = 0: 18,371, 18,349, 18,324, 18,195
- 197 > 0: 162, 145, 139, 131

The curves are in `results/survival/km_primary.png`.

### 4.3 Cox model

| Analysis | HR | 95% CI | Wald p | PH test |
|---|---|---|---|---|
| Primary | 43.2 | 28.1–66.3 | 1.7e−66 | χ² = 7.29, p = 0.0069 |
| S1 (exits reclassified) | 43.2 | 28.1–66.3 | 1.7e−66 | p = 0.0069 |
| S2 (gap days removed) | 44.1 | 28.7–67.7 | 3.5e−67 | not computed* |

\*lifelines 0.30.0 has no PH test for start/stop fits.

### 4.4 Reading the results

- **Early concentration.** In the 197 > 0 group, about 10% of drives had a recorded
  failure within 30 days, then roughly 4% in each later 30-day span. The proportional-
  hazards test rejects a constant ratio, so treat the HR as an average over the quarter
  and the survival curves and landmark values as the primary summary.
- **Robustness to exits and gaps.** Exits barely move the estimates (S1): only 3 of
  the 162 exposed drives exited. Removing gap days (S2) changes the HR by about 2%.
- **Absolute risk.** The excess is large in relative terms and in absolute terms within
  this subgroup: about 17 in 100 exposed drives versus fewer than 1 in 200 unexposed
  drives over 89 days. But the exposed group is under 1% of the cohort.

## 5. Limitations

1. **Outcome partly defined by SMART signals.** According to Backblaze's Drive Stats
   posts, a removed and replaced drive counts as a failure whether the removal was
   reactive or proactive. Proactive removals are triggered by indicators such as SMART
   stats or file-system checks, and the public data records only a 0/1 flag, not the
   failure type ([Q3 2024](https://www.backblaze.com/blog/backblaze-drive-stats-for-q3-2024/),
   [Q3 2025](https://www.backblaze.com/blog/backblaze-drive-stats-for-q3-2025/); quoted
   from search results, as this session could not open the pages directly). Part of the
   association therefore reflects Backblaze's replacement policy acting on warnings like
   SMART 197, not spontaneous physical failure. The two cannot be separated with these
   data.
2. **Prevalent cohort and left truncation.** Drives had unknown prior service time. The
   estimates are conditional on being in service on 1 January, not lifetime risk.
   SMART 9 (powered hours) was not used as an age scale.
3. **Ascertainment.**
   - Failure dates are daily snapshot dates. 21 of the 44 failures that followed a gap
     were flagged on the day the drive returned, so some dates may be ascertainment
     dates.
   - Day-one failures are outside Backblaze's daily failure logic.
4. **Informative exits.** 4 drives that "exited" Q1 carried a failure flag in early
   April, so exits are not wholly uninformative. Q1 outcomes were not changed.
5. **Exposure specificity.** 110 of the 162 exposed drives were also nonzero on SMART 5
   (reallocated sectors). The HR does not isolate pending-sector status from
   reallocation.
6. **Scope and precision.** One model, one quarter and 28 exposed events, hence a wide
   CI (28–66). No confounder adjustment was planned or attempted.
7. **Non-proportional hazards** (§4.4).

## 6. Conclusion

For ST12000NM0008 drives in service on 1 January 2026, a nonzero pending-sector count
(SMART 197) at baseline marks a small subgroup — under 1% of drives — with a far higher
quarter-ahead rate of recorded failure. The excess is concentrated in the first weeks,
and it is robust to the pre-specified exit and gap sensitivity analyses. Because
Backblaze's failure definition includes proactive, SMART-informed removals, this is
best described as SMART 197 being strongly associated with recorded removal-or-failure.
It is not evidence that pending sectors cause drives to fail, nor a validated
prediction rule.

## 7. Reproducibility and provenance

- **Order of commits:**
  - `e3cf5dd`: decisions D1–D8 committed before the per-group counts were read.
  - `4259dc3`: per-group counts opened; D1 kept SMART 197.
  - `2b91f38`: analysis plan committed before any model was fitted.
  - `28cb715`: models fitted.
- **Reproduce** (needs the Q1 ZIP in the Git-ignored `data/raw/`; see
  `docs/q1_cohort_feasibility.md` §6):

```bash
PYTHONPATH=src python scripts/build_cohort_skeleton.py --zip-path data/raw/data_Q1_2026.zip --expect-manifest results/audit/data_manifest.json --output-dir data/processed/q1_cohort
```

```bash
PYTHONPATH=src python scripts/link_q1_exits.py --remote-url https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q2_2026.zip
```

```bash
PYTHONPATH=src python scripts/fit_q1_survival.py --zip-path data/raw/data_Q1_2026.zip --check
```

- Serial-level data is never committed.
- At the head of PR #3, the test suite (47 tests) passes, along with the Q1 and history
  verifiers.
