# Q1 2026 Backblaze data audit summary

> DATA GATE verdict: **READY WITH CONDITIONS**. Q1 supports a reproducible drive-day and observed-event audit, but Q1 alone does not reveal installation age and non-failure exits cannot be assumed independent censoring.

## Scope and headline counts

- Daily CSV files: 90 (2026-01-01 through 2026-03-31)
- Drive-days: 30,597,484
- Unique serial numbers: 351,095
- Failure rows: 1,030
- Unique drives with `failure == 1`: 1,030
- Non-failure disappearances before quarter end: 4,427
- Drives disappearing and later reappearing: 17,043

The raw March 31 count (345,662) and failure count (1,030) exactly reconcile to Backblaze's official Q1 report. This audit's 30,597,484 drive-days include all line-item rows; the report's 30,203,180 drive-days are a restricted subset after boot-drive, low-count-model, and other documented reporting exclusions.

## Assumption checks

| Check | Value | Status |
|---|---:|---|
| daily_csv_files | 90 | PASS |
| date_range | 2026-01-01 to 2026-03-31 | PASS |
| drive_day_key_duplicates | 0 | PASS |
| invalid_date_rows | 0 | PASS |
| filename_date_mismatch_rows | 0 | PASS |
| invalid_failure_rows | 0 | PASS |
| multiple_failure_drives | 0 | PASS |
| post_failure_observed_drives | 0 | PASS |
| nonfailure_disappearances | 4427 | REVIEW |
| disappear_then_reappear_drives | 17043 | REVIEW |
| invalid_capacity_rows | 0 | PASS |
| schema_variants_within_quarter | 1 | PASS |

## Schema and SMART coverage

- All 90 files share one 197-column header: 5 core fields, 6 location/server fields, and 186 SMART columns (93 raw/normalized pairs).
- The current official schema has two misspellings: `smart_211_normailized` and `smart_212_normailized`; Q1 files use `normalized`.
- Raw and normalized members of every SMART pair have matching non-null counts.
- 20 SMART columns are entirely absent, 84 have nonzero but under 1% reporting, and only 28 reach at least 90% overall reporting.
- SMART 9 raw is reported for 30,558,066 drive-days (99.871%) and is near-complete for all 18 major raw model labels, but its interpretation as powered hours still requires model-specific validation.
- Several normalized attributes are constant where reported; missingness and constant behavior are model-dependent and were not imputed or used for predictor selection.

## Major model inventory

| Model | Drives | Drive-days | Failed drives | SMART 9 raw coverage | Flags |
|---|---:|---:|---:|---:|---|
| WDC WUH722222ALE6L4 | 45,638 | 3,992,942 | 42 | 1.000 |  |
| TOSHIBA MG08ACA16TA | 40,036 | 3,548,250 | 102 | 1.000 |  |
| TOSHIBA MG07ACA14TA | 37,263 | 3,343,724 | 94 | 1.000 |  |
| ST16000NM001G | 34,729 | 3,098,105 | 44 | 1.000 |  |
| WDC WUH721816ALE6L4 | 26,325 | 2,366,036 | 56 | 1.000 |  |
| TOSHIBA MG10ACA20TE | 20,451 | 1,665,263 | 42 | 1.000 |  |
| ST12000NM0008 | 18,650 | 1,664,558 | 129 | 1.000 |  |
| ST12000NM001G | 13,216 | 1,185,545 | 33 | 1.000 |  |
| HGST HUH721212ALE604 | 13,277 | 1,183,774 | 86 | 1.000 |  |
| ST8000NM0055 | 13,232 | 1,176,619 | 39 | 1.000 |  |
| ST14000NM001G | 10,519 | 944,400 | 21 | 1.000 |  |
| HGST HUH721212ALN604 | 9,780 | 870,252 | 95 | 1.000 |  |

The raw labels `WDC WUH721816ALE6L4` and `WUH721816ALE6L4` form a verified alias split. Together they reconcile to the official report's 26,801 drives, 2,402,732 drive-days, and 64 failures; they remain separate in the raw inventory until a canonicalization rule is formally adopted.

## Candidate cohorts

| Candidate | Definition | Drives | Failures | Verdict |
|---|---|---:|---:|---|
| single_largest_model | Q1 2026, model == WDC WUH722222ALE6L4 | 45,638 | 42 | READY WITH CONDITIONS |
| single_event_rich_model | Q1 2026, model == ST12000NM0008 | 18,650 | 129 | READY WITH CONDITIONS |
| major_models_q1 | Q1 2026 models each contributing at least 1% of quarter drive-days | 328,623 | 939 | READY WITH CONDITIONS |
| largest_manufacturer_q1 | Q1 2026, conservatively inferred manufacturer == Toshiba | 117,902 | 294 | REVISE |

## Major risks

- Q1 entry is an observation boundary, not a physical-age origin.
- A disappearance without a failure row has unknown cause and is not classified as failure.
- SMART reporting is model-dependent; missing values remain missing and were not imputed.
- Daily rows are repeated observations of drives and are not independent units.
- Manufacturer labels are conservative model-prefix inferences, not a source field.
- Backblaze's event flag uses prior-day presence/disappearance and lookback logic; drives that fail before completing their first day are not observable as failures in these daily files.

See `docs/survival_data_feasibility.md` and the CSV tables for the full gate evidence.
