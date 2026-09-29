# Data provenance

## Controlling source

The controlling data source is the official Backblaze Q1 2026 Drive Stats ZIP:

- Download page: <https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data>
- Exact artifact: <https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q1_2026.zip>
- Access date: 2026-09-29
- HTTP `Content-Length`: 1,312,921,361 bytes
- Backblaze `x-bz-info-large_file_sha1`: `23448d5733a4762a9cf1d5e341fc240c2d10b13c`
- Backblaze file ID: `4_zefbb636e885eab02543a061a_f219a81f7d5e71902_d20260708_m185146_c001_v0001097_t0040_u01783536706950`
- Published size: 1.3 GB ZIP, approximately 12.02 GB extracted, 91 ZIP entries
- Observed contents used: 90 daily CSV members plus one directory entry; each member name, size, CRC32, and audited row count is recorded in `results/audit/data_manifest.json`

The full ZIP was not saved because the machine had approximately 2.1 GiB free at the acquisition gate. Extraction would have exceeded free capacity by roughly 10 GiB. The audit used deterministic HTTP byte-range reads and processed one 100,000-row chunk at a time. No sampling was used.

## Schema sources

- Current schema CSV: <https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/Drive_Stats_Schema_Current.csv>
  - Accessed 2026-09-29
  - Published label: `Last Updated Q2 2024`
  - SHA-256: `365cf50ad5ebfc3e20d0959337d9877ce9539e0432955bda836b7482cd0f5358`
- Schema history CSV: <https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/Drive_Stats_Schema_2018_Onward.csv>
  - Accessed 2026-09-29
  - SHA-256: `0ac0c6abcad39c22e590dd8a6ece897a8bb899e4618e67d5e78c0ced30282c37`

The history file ends before Q1 2026 and the current schema is labeled Q2 2024, so the actual Q1 daily headers control quarter-specific availability. All 90 Q1 files have the same 197-column header. Relative to the official current list, Q1 uses correctly spelled `smart_211_normalized` and `smart_212_normalized`, whereas the documentation contains `smart_211_normailized` and `smart_212_normailized`.

## Official-report reconciliation

The official [Q1 2026 Drive Stats report](https://www.backblaze.com/blog/backblaze-drive-stats-for-q1-2026/) was published 2026-07-09. It states that 345,662 drives were monitored at quarter end, then removes 3,907 boot drives and 492 hard drives for an analyzed population of 341,263. Its reporting table uses additional model thresholds (`>100` drives and `>10,000` drive-days).

This audit exactly reconciles the raw March 31 row count (345,662) and failure count (1,030). It reports 30,597,484 raw drive-days because it retains every line-item row; Backblaze's restricted reporting table contains 30,203,180. The 394,304-drive-day difference is therefore an explained scope difference, not a row-count failure.

One raw label split is also verified: `WDC WUH721816ALE6L4` plus `WUH721816ALE6L4` sum exactly to the official report's 26,801 drives, 2,402,732 drive-days, and 64 failures for `WUH721816ALE6L4`. The audit preserves raw labels and flags the alias; a later cohort build must define and test canonicalization.

## Event-field provenance and limitation

Backblaze states that its end-of-day program uses prior presence, disappearance, and a lookback to assign or undo failures. It also states that a drive failing before it completes its first day cannot be defined by that program. Therefore `failure == 1` is the source-defined observed event, but it is not complete ascertainment of all physical failures from installation.

## Unused alternative source

Backblaze also publishes an official Iceberg copy. A read-only check on 2026-09-29 returned zero rows for Q1 2026, so it was not used for measurements or conclusions. The ZIP remained the controlling source.
