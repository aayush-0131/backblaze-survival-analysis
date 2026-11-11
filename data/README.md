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

2026-11-02: `raw/data_Q1_2026.zip` (1,312,921,361 bytes, SHA1
`23448d57…0b13c`) was retrieved into the ignored `raw/` and is not committed. Re-download it and check the SHA1 to reproduce. Builder outputs
were written to `processed/q1_cohort/` (ignored, serial-level). `cohort_accounting.csv` there holds
the **sealed** per-group event counts; do not share it before the event-support rule
is recorded. Integrity evidence: `docs/q1_retrieval_record.json`.

2026-11-02 (later): `scripts/link_q1_exits.py` streams only the Apr 1–14 members of
`data_Q2_2026.zip` by byte range, and writes nothing to `raw/`. Serial-level output goes
to `processed/q1_exit_linkage/` (ignored). Do not commit it.
