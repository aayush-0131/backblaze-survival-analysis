# SMART 197 and predeclared SMART 5 alternative: design feasibility only

No hypothesis test, effect estimate, predictor search or model was performed.
The user/literature audit predeclared SMART 197 and then SMART 5. The only warning
cut is raw `>0`; no thresholds were searched. Missing is a third state, never zero.

## Semantics and interpretability

VERIFIED FACT: [WD's model-family manual](https://documents.westerndigital.com/content/dam/doc-library/en_us/assets/public/western-digital/product/data-center-drives/ultrastar-dc-hc500-series/product-manual-ultrastar-dc-hc570-sata-oem-spec.pdf)
section 12.55.2.2 names attribute 197 Current Pending Sector Count and 5
Reallocated Sector Count for WUH722222ALE6L4. Raw bytes remain vendor-specific.
[Backblaze documentation](https://www.backblaze.com/docs/cloud-storage-hard-drive-smart-stats-and-failure-rates)
describes pending sectors and reallocation as different conditions: a pending
sector need not remain pending or become an observed drive failure. Its generic
description is not a firmware-specific validation for either candidate.
Seagate model-specific raw decoding remains an open problem; do not equate
vendor-normalized values, sector counts or failure diagnoses across models.

INFERENCE: zero/nonzero status has a more interpretable warning meaning than
unvalidated cross-vendor raw magnitude. It still needs measurement-validity and
baseline event-support checks within one model. Monitoring-driven retirement
could make unexplained exits informative rather than independent censoring.

## Observed baseline support: Q2 2023, not Q1 2026

Fixed baseline is April 1. A drive must be present that day; events on/before
baseline are kept out of subsequent-event counts. First-observed baseline is a
separate descriptive alternative, not a future-maximum warning classification.

| Seagate baseline definition | Attribute | Zero drives / subsequent failures | Nonzero drives / subsequent failures | Missing |
|---|---|---:|---:|---:|
| April 1 fixed | 197 | 19,686 / 128 | 61 / 27 | 0 |
| First observation in window | 197 | 19,769 / 130 | 61 / 27 | 0 |
| April 1 fixed | 5 | 19,077 / 89 | 670 / 66 | 0 |
| First observation in window | 5 | 19,159 / 90 | 671 / 67 | 0 |

The four WDC drives are all later arrivals, zero-state on both attributes at
first observation, and have no recorded failures. They provide no warning-group
or event support in this historical window. This does not describe the Q1 cohort.

Seagate reporting for each attribute is 99.9968% (56 missing drive-days).
Nonzero rows: 4,661 for 197 and 62,382 for 5. Valid adjacent-date zero/nonzero
transitions: 119 for 197 and 159 for 5; across gaps: nine and five. Exact-value
adjacent changes: 419 and 2,557. WDC has full coverage and no changes. Daily
rows are longitudinal, not independent observations. The counts reconcile to
157 events for first-observed baselines and 155 for the fixed-baseline risk set.

## Q1 2026 aggregate evidence

| Model | Attribute | Coverage | Nonzero drive-days / reported rows |
|---|---|---:|---:|
| Seagate | 197 | 99.9996% | 14,682 / 1,664,551 |
| Seagate | 5 | 99.9996% | 115,356 / 1,664,551 |
| WDC | 197 | 100% | 7,815 / 3,992,942 |
| WDC | 5 | 100% | 13,904 / 3,992,942 |

Counts are reconstructed by rounding the authoritative non-null count times its
serialized zero fraction, not a new raw-data scan. This demonstrates reporting
and non-degenerate drive-day variation, not the number of exposed baseline
drives or events by baseline state. The seven Seagate missing rows are retained
as missing. January 1 risk-set size, warning groups, transitions and subsequent
failures by group are **unavailable**. They are blank in the tables, not estimated
from marginal counts. The 129 / 42 Q1 events are all-quarter counts, not necessarily
fixed-baseline subsequent events.

## Recommendation and limitations

PROPOSED METHOD: continue the January 1 Seagate baseline feasibility check first:
single-model semantics, existing Q1 event count and coverage favor tractability.
Keep WDC as an alternative requiring its own group accounting. This is not a
comparison of fitted significance or observed effect magnitude. Keep 197 as the
leading predeclared status; switch to 5 only for meaningful semantics, variation,
coverage or inadequate group event support, documenting the reason jointly with
the literature audit before modelling.

Baseline status analysis is descriptively plausible in Q2 Seagate; Q1 design
readiness is **BLOCKED**, because group event support and outcome ascertainment
are missing. Repeated-data construction is computationally feasible, but Q1
time-varying analysis is not approved. It would require start/stop records,
strictly prior/lagged SMART values, explicit missing/gap intervals, no future
information, and a terminal first-event policy that resolves post-failure records.
No such model or final analytic dataset was implemented.
