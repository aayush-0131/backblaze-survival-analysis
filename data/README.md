# Data directory

Raw and generated large data are intentionally excluded from version control.

- `raw/`: optional local ZIP or daily CSV inputs; Git-ignored except for `.gitkeep`.
- `interim/`: resumable processing checkpoints; Git-ignored except for `.gitkeep`.
- `processed/`: any future large derived datasets; Git-ignored except for `.gitkeep`.

The completed Q1 2026 audit did **not** save the 1,312,921,361-byte ZIP and did not extract its approximately 12.02 GB of CSV data. It read each daily member sequentially through HTTP byte ranges and retained only lightweight summaries. Exact source metadata and all ZIP member CRC32 values are in `results/audit/data_manifest.json`.

Do not commit Backblaze ZIP/CSV files or large derived drive-day datasets.
