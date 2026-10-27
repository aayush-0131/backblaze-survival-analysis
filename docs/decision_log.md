# Decision log

## 2026-09-29 — quarter and scope

- Used Q1 2026 as explicitly directed, even though the live download page now also lists Q2 2026.
- Kept this phase as a data gate. No Cox model, Kaplan–Meier estimator, regression, machine-learning model, feature selection, confirmatory test, or final hypothesis was created.

## 2026-09-29 — acquisition safety

- Found only about 2.1 GiB free disk space.
- Rejected full ZIP retention and extraction: the artifact is 1.313 GB compressed and approximately 12.02 GB extracted.
- Tried the official read-only Iceberg copy as a no-download alternative; it exposed no Q1 2026 rows and was rejected as the controlling source.
- Used byte-range reads against the official ZIP, one daily CSV and one bounded chunk at a time.
- Added daily checkpoints, a 60-second network timeout, and bounded retries after transient DNS/read failures. Checkpoints are ignored and removed on success.

## 2026-09-29 — row and event policy

- Audited all raw line-item rows. Did not silently reproduce Backblaze's publication exclusions.
- Treated `(date, serial_number)` as the candidate drive-day key and verified zero duplicates.
- Treated only `failure == 1` as an observed source event. Disappearance was retained separately.
- Did not convert first Q1 appearance into installation date.
- Preserved observation gaps and non-failure exits as distinct audit evidence.

## 2026-09-29 — schema and model labels

- Used actual Q1 headers as quarter-specific authority because official schema documents are older.
- Preserved the two documentation misspellings as a comparison finding rather than renaming observed columns.
- Kept raw model labels in the main inventory. Flagged the `WDC WUH721816ALE6L4` / `WUH721816ALE6L4` alias split; canonicalization is required before choosing that hardware cohort.
- Manufacturer is a conservative model-prefix inference only. Unmapped values remain `Unknown`.

## 2026-09-29 — SMART policy

- Calculated reporting and zero fractions without imputation.
- Treated raw and normalized columns as availability pairs, not semantically interchangeable measurements.
- Used min/max/mean for compact numeric profiling. SMART distinct counts are bounded in the schema table (`0`, `1`, or `>=2`) to avoid large in-memory sets.
- Defined “major model” for the by-model coverage table as at least 1% of Q1 drive-days. This is a reporting-scope rule, not a permanent exclusion or statistical threshold.

## 2026-09-29 — candidate cohorts and verdict

- Proposed two single-model cohorts, a major-model stratified pool, and a manufacturer-defined diagnostic pool.
- Descriptive low-count flags (`<1,000` drives and `<10` failures) are configurable review cues, not universal sufficiency rules.
- Overall verdict: **READY WITH CONDITIONS**. A bounded historical first-appearance and model-specific SMART 9 semantics audit must precede a frozen survival design.

## 2026-10-06 — resumed bounded historical / SMART feasibility stage

- Verified the exact checkpoint, branch, clean tree and original four tests plus Q1 reconciliation. Preserved all authoritative Q1 result artifacts.
- Used only managed sandbox execution; did not interact with external DuckDB terminals, bypass the proxy, escalate acquisition or perform unbounded mirror scans.
- Found the interrupted Q2 2023 ZIP complete, verified all-entry CRC, size and local SHA1/SHA256; processed 91 compressed daily members in 50k chunks without expansion. Retained valid raw data, ignored checkpoint and compact per-drive outputs.
- Corrected the preliminary WDC timing: first in inspected Q2 files is April 8, not late Q2. Complete all-history first appearance is still open. Seagate is independently documented by Q1 2022; no birth/install date inferred.
- Kept exact raw model identity; did not normalize a hypothetical WDC prefix variant without observing and justifying it.
- Audited only predeclared SMART 9/197/5. Fixed zero/nonzero status, separate missingness, fixed April 1 and first-observed snapshots; no thresholds searched, inferential tests or fitted effects.
- Preserved 52 invalid capacity rows and 10 post-failure rows from two Seagate drives. Checkers flag genuine data-quality violations instead of discarding data to enforce ideal assumptions.
- SMART 9 endpoint rates support nominal hours, while daily 16/32-like increments and 180 excess-change flags need timing/firmware review. Q1 age integrity and lifetime continuity remain unvalidated.
- Gaps are not failures. Return-before-first-flag chronology is asserted only when complete post-event day coverage rules out later gaps; otherwise the count is unknown. No-gap eligibility is illustrative sensitivity accounting, not a recommended data exclusion.
- Reused Q1 aggregate counts; left all unavailable Q1 baseline-state/event/transition/gap/exit cells blank. Published lifetime counts are labelled external reporting-subset context, not reconstructed history.
- Managed range acquisition failed DNS. Scope reduction: completed local Q2 2023 and Q1 aggregate context; deferred Q1 serial linkage, bounded Q4 lookback/Q2 returns and full historical census.
- Prefer validating single-model Seagate fixed-baseline Q1 calendar follow-up; keep 197 lead / 5 predeclared alternative. Choose neither based on observed effect size. Proposed 14-day linkage is an operational sensitivity horizon, not permanence proof.
- Narrow design-approval gate: **BLOCKED** pending the missing acquisition/reconciliation. Original Q1 data gate stays READY WITH CONDITIONS. Joint review with the literature audit is required; no final hypothesis/cohort frozen and no modelling, push or merge performed.
