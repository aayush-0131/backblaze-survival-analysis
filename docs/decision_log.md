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
