# ASM-II Backblaze data-feasibility audit

This repository contains the first reproducible data gate for a Semester V Advanced Statistical Methods II project using the official Backblaze Drive Stats data. It audits Q1 2026 at the drive-day grain without fitting survival curves, Cox models, regressions, hypothesis tests, or predictive models.

## Data-gate result

**READY WITH CONDITIONS.** The 90 daily files support a reproducible drive-day/event table and contain enough observed failures for several candidate cohorts. Q1 alone does not establish physical drive age, early non-failure exits may be informative, raw model labels contain at least one alias split, and Backblaze documents that day-one failures are not captured by its daily failure logic.

Headline raw-data counts:

- 2026-01-01 through 2026-03-31; no dates missing
- 30,597,484 drive-days
- 351,095 unique serial numbers observed at least once
- 1,030 failure rows from 1,030 distinct drives
- 4,427 drives disappearing before quarter end without a failure row
- 17,043 drives disappearing and later reappearing
- 197 columns: 5 core, 6 location/server metadata, and 186 SMART columns (93 raw/normalized pairs)

Backblaze's published Q1 report also records 1,030 failures and 345,662 raw drives on March 31. Its 30,203,180 drive-days and 341,263 analyzed drives are a restricted reporting subset; this audit deliberately retains every published line-item row.

## Reproduce

Python 3.11+ is required. The full remote run downloads ZIP member byte ranges but does not retain the 1.3 GB archive or its approximately 12.02 GB extraction.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/verify_outputs.py

PYTHONPATH=src python scripts/run_data_audit.py \
  --remote-url https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q1_2026.zip \
  --output-root . \
  --artifact-meta docs/source_q1_2026.json \
  --chunksize 100000 \
  --checkpoint data/interim/q1_2026_checkpoint.pkl
```

For a staged safety check, add `--max-files 1` and use a temporary `--output-root`. The checkpoint is ignored by Git and removed after a successful full run.

The required outputs are under `results/tables/`, `results/audit/`, and `docs/`. Start with [the audit summary](results/audit/data_audit_summary.md), [data provenance](docs/data_provenance.md), and [survival feasibility](docs/survival_data_feasibility.md).

## Scope guardrail

The operational flags in `model_inventory.csv` (`<1,000` drives and `<10` failures) are descriptive review cues, not universal statistical eligibility thresholds. No model or SMART attribute has been selected because of an observed association with failure.

## Historical / SMART follow-up (2026-10-06)

The [bounded history summary](results/audit/history_audit_summary.md) preserves
the Q1 result above. It processes Q2 2023 for the two candidate models and reuses
Q1 aggregates. Its narrower gate is **BLOCKED for Q1 baseline-warning design
approval**: managed archive acquisition failed, and Q1 baseline event-by-warning,
counter integrity and boundary linkage cannot be reconstructed from aggregates.
Nominal powered hours are supported by historical endpoints, not physical age.
The summary provides exact local reproduction commands. No models were fitted,
final hypotheses frozen or all-history corpus downloaded.

## Minimal Q1 path and cohort skeleton (2026-11-01)

[`docs/q1_minimal_path.md`](docs/q1_minimal_path.md) lists exactly which Q1
candidate-level inputs are missing, a conditional minimal design, a checked
assumptions table, the unblock checklist and the exact data request.
`scripts/build_cohort_skeleton.py` builds per-drive fixed-baseline records
(inclusion, first recorded failure vs non-failure exit, gap flags) once Q1 rows
are available; it is tested only on synthetic fixtures. The Q1 design gate
remains **BLOCKED** and no survival model has been fitted.
