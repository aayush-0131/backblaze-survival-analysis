# Historical + SMART data gate — bounded stage, 2026-10-06

**BLOCKED for approving the proposed Q1 2026 baseline SMART-status design.**
The local Q2 2023 historical stage is completed and reproducible. Q1's prior
**READY WITH CONDITIONS** data-feasibility verdict remains authoritative and
unchanged. This narrower gate requires Q1 serial-level baseline groups, event
support, age integrity and gap/boundary reconciliation, which are not available
from the preserved Q1 marginal tables. No modelling was performed.

## Evidence actually measured

Only the complete official Q2 2023 ZIP was newly processed; Q1 2026 aggregate
artifacts were reused without rerunning the completed Q1 scan. Exact URLs/hashes,
source headers, daily CRC/SHA256 and output hashes are in `history_manifest.json`
and `docs/source_q2_2023_history.json`. All 91 daily CSVs are present. The
interrupted archive is valid, not partial; no full extraction was created.

| Scope | Model | Unique drives | Drive-days | Recorded failures |
|---|---|---:|---:|---:|
| Measured Q2 2023 | ST12000NM0008 | 19,830 | 1,763,868 | 157 |
| Measured Q2 2023 | WDC WUH722222ALE6L4 | 4 | 328 | 0 |
| Preserved Q1 2026 | ST12000NM0008 | 18,650 | 1,664,558 | 129 |
| Preserved Q1 2026 | WDC WUH722222ALE6L4 | 45,638 | 3,992,942 | 42 |

Dates: Q2 April 1–June 30; WDC first seen April 8, correcting the preliminary
late-Q2 description. Seagate's April 1 first date is only a window boundary;
official documentation already shows this model in Q1 2022. Complete historical
first appearances, historical serial census and Q1 trace-back fractions remain
unknown. Exact observed model aliases are identity only; no prefix is stripped.

SMART 9 nominal hours are supported by long-span counter/calendar ratios
(median 0.99907 Seagate; 0.99900 WDC). Daily deltas cluster around 16/32, not 24;
snapshot timing is an inference, not a verified explanation. There are zero
decreases/reset candidates in Q2, but 180 Seagate excess-change flags across 180
drives. Coverage is 99.9968% / 100%. WDC has only four historical drives. Q1
counter integrity is unknown; powered hours are not installation age.

SMART 197 and 5 are nearly completely reported in Q1 and show nonzero
drive-day variation. Baseline group events are unavailable for Q1. In Q2 Seagate,
April 1 SMART 197 groups contain 19,686 zero / 61 nonzero drives and 128 / 27
subsequent recorded failures. SMART 5 groups contain 19,077 / 670 drives and
89 / 66 failures. These are descriptive support counts, not statistical tests or
evidence for predictor selection. Q2 WDC is all-zero with no events.

## Baseline accounting and ascertainment risks

Q2 fixed-baseline Seagate: 19,747 present; 83 later arrivals; zero baseline
missing required warning/age/capacity exclusions; 19,747 retained, 155 recorded
subsequent failures and 19,592 administrative survivors; zero unflagged exits
within this window. All-baseline, complete-warning and complete-warning-plus-age
rules agree. WDC has zero baseline drives and four later arrivals.

There are 15,235 intermittent-gap drives in the Seagate fixed-baseline cohort.
The descriptive no-gap rule removes all 15,235, leaving 4,512 drives and 40
events. This illustrates severe selection; it is **not** a recommended exclusion
or an outcome-optimized design. In the whole Q2 sample, 15,245 Seagate drives
have gaps; 115 first recorded failures occur following a return (including the
return date). This ordering follows from complete post-event day coverage;
the generic pipeline leaves ordering unknown when that check fails. WDC has
four gapped drives/eight one-day gaps. Q1 accounting,
model-specific exits, prior-state sensitivity and boundary-return counts are blank
where unavailable. Unflagged exit is never relabelled failure.

Two Seagate serials have ten post-failure observations; 52 candidate rows have
invalid capacity (`-1`) and 52 drives show inconsistent capacities. Missing SMART
9/197/5 is 56 rows each. None are silently dropped or imputed. All daily candidate
keys are unique and all candidate dates/failure fields valid. Failures reconcile:
157 source rows, 157 failed serials, 155 fixed-baseline events plus two events
among later arrivals. No repeated failure flags occur.

Additional threats: prevalent-drive selection; informative censoring/monitoring
retirement; missed day-one and gap-period failures; unknown raw firmware coding;
deployment-era heterogeneity; incomplete historical tracing; low WDC historical
support; date-only snapshots; warnings may change after baseline. No causal or
lifetime survival interpretation is approved.

## Conditional recommendation

Prefer Seagate single-model fixed-baseline Q1 calendar follow-up as the next
design to validate. Keep 197 as predeclared lead and 5 as its predeclared
feasibility alternative. Acquire only limited Q4 lookback/Q2 boundary linkage,
not all history. No final cohort or hypothesis is frozen. SMART-9 age-based or
delayed-entry modelling is deferred. Q2 baseline-status data representation is
feasible with conditions; Q1 baseline and time-varying designs are not cleared.
For time-varying work later, prior/lagged SMART start/stop intervals and explicit
gap/missingness/event policies would be necessary.

## Reproduce locally (no further network or Q1 regeneration)

From the repository, with the existing project dependencies:

```bash
python -m pytest -q
python scripts/verify_outputs.py
PYTHONPATH=src python scripts/run_history_audit.py \
  --zip data/raw/data_Q2_2023.zip \
  --baseline 2023-04-01 --end 2023-06-30 --output-root . \
  --chunksize 50000 --provenance docs/source_q2_2023_history.json \
  --checkpoint data/interim/history_q2_2023.pkl
PYTHONPATH=src python scripts/build_history_context.py
PYTHONPATH=src python scripts/verify_history_outputs.py
git diff --check
```

For the full archive-integrity repeat, run
`PYTHONPATH=src python scripts/verify_history_outputs.py --verify-archive`.
It sequentially CRC-checks all expanded member bytes without extracting files.

Omit `--checkpoint` for a fresh scan. Never load a downloaded pickle. A rerun from
the completed trusted checkpoint reconstructs the same tables; checks verify
hashes, first-date/count reconciliation, baseline accounting, missingness and
explicit unknown Q1 cells. New tests include small ZIP streaming, source calendar,
overlap, provenance and deterministic checkpoint replay. The verifier intentionally
prints the real post-failure violation rather than asserting it away.

## Exact blocker / next action

Validation on 2026-10-06: **14 tests passed** (four existing, ten historical),
both Q1 and history reconcilers passed; full source SHA1/SHA256 and all-entry
CRC passed; full-quarter table hashes reproduced after checkpoint replay;
`git diff --check` passed. The only tracked modifications to pre-existing files
are README and data README; all original Q1 results remain unchanged.
Runtime: Python 3.13.5, pandas 3.0.6, NumPy 2.5.3, pytest 8.3.4. Pandas emitted
a non-failing optional-numexpr version warning (2.10.1 installed, >=2.10.2
recommended); no dependency was changed to suppress it.

Next step at the time of this audit: acquire candidate rows for Q1 plus a bounded
lookback/linkage window, then reconcile January 1 groups, events, gaps and Q1
SMART 9 before choosing a design. (Done later; see `docs/q1_survival_results.md`.)
