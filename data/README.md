# Data directory

Raw and generated large data are intentionally excluded from version control.

- `raw/`: optional local ZIP or daily CSV inputs; Git-ignored except for `.gitkeep`.
- `interim/`: resumable processing checkpoints; Git-ignored except for `.gitkeep`.
- `processed/`: any future large derived datasets; Git-ignored except for `.gitkeep`.

The completed Q1 2026 audit did **not** save the 1,312,921,361-byte ZIP and did not extract its approximately 12.02 GB of CSV data. It read each daily member sequentially through HTTP byte ranges and retained only lightweight summaries. Exact source metadata and all ZIP member CRC32 values are in `results/audit/data_manifest.json`.

Do not commit Backblaze ZIP/CSV files or large derived drive-day datasets.

The historical follow-up validated the previously interrupted, complete
`raw/data_Q2_2023.zip` (859,566,204 bytes) and streamed all 91 daily members without
extraction. Its ignored outputs are `processed/history_drive_summary.csv`,
`processed/smart9_anomalies.csv` and `interim/history_q2_2023.pkl`. The summary's
earliest dates cover inspected files, not installation or complete history.
Never load checkpoints from untrusted sources. Retain the valid source archive;
no prior data was deleted. No Q1 daily candidate extract is available locally.
Lightweight public evidence is in `results/audit/history_manifest.json`.

`scripts/build_cohort_skeleton.py` writes serial-level cohort records to
`processed/q1_cohort/` (ignored). Do not commit `cohort_drives.csv`.
