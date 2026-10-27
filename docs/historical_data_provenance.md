# Bounded historical provenance — 2026-10-06

## Verified checkpoint and execution

VERIFIED FACT: resume began on `work/backblaze-history-audit`, HEAD
`0f27a5756af568eef2ed6548b251c5e2ac382420`, with a clean tree. Four existing
tests and the Q1 output reconciler passed. The Q1 artifacts were not regenerated.
Only managed, default-sandbox command execution was used after resume. No earlier
external terminal was attached, messaged or polled; no proxy bypass was used.

VERIFIED FACT: the interrupted Q2 2023 download was present and complete.
`zipfile.testzip()` passed for all 184 entries (including metadata/directories).
The 91 actual daily members span April 1–June 30 without missing dates. The
archive is 859,566,204 bytes; expanded entries total 8,060,122,531 bytes. It was
read compressed, one daily member in 50,000-row chunks, selecting only the two
models and eight core/SMART fields. No expanded archive was retained. Disk space
was about 14 GiB at resume and 12 GiB at final checks; no further ZIP was acquired.

Source: [official downloads](https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data).
Exact inspected artifact:
[data_Q2_2023.zip](https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q2_2023.zip).
Access/integrity verification date: 2026-10-06. Initial download start date is not
independently known. Source bytes and HTTP object ID are in
`docs/source_q2_2023_history.json`.

- Local SHA256: `cd43df47416fed6d358da090b3cab8f96dfbb7bcba70ea983d43b663005462f3`
- Local SHA1: `768d7217bdf175a385f15c1454e696f740457f0c`
- Official HEAD SHA1: `none`; no independent official whole-file hash supplied.

CRC establishes ZIP member integrity, not independent authenticity. Exact
decompressed daily SHA256 hashes, headers and member CRCs are recorded in
`results/audit/history_manifest.json`. Repeated local processing is checked by
output hashes. Local checkpoints are trusted pipeline products, never remote
pickles. The compact per-serial summary and anomaly records are Git-ignored.

## Scope, first appearance and aliases

| Model | Observed Q2 unique drives | Drive-days | Failure rows / drives | First observed in inspected archive | Last |
|---|---:|---:|---:|---|---|
| ST12000NM0008 | 19,830 | 1,763,868 | 157 / 157 | 2023-04-01 | 2023-06-30 |
| WDC WUH722222ALE6L4 | 4 | 328 | 0 / 0 | 2023-04-08 | 2023-06-30 |

VERIFIED FACT: WDC is absent April 1–7 and first present April 8 in this archive,
not merely inferred to enter in late Q2. This corrects the interrupted preliminary
description. Whether any earlier-quarter records exist remains unverified.
The [official Q2 report](https://www.backblaze.com/blog/?p=109338) discusses four
22 TB test drives; this corroborates a small test cohort, not its installation date.

VERIFIED FACT: Seagate was already documented in Q1 2022 in an
[official analytical-data example](https://www.backblaze.com/blog/storing-and-querying-analytical-data-in-backblaze-b2/).
That is evidence of model presence by Q1 2022, not its earliest appearance and
not a serial-level historical reconstruction. The Q2 2023 entry is window-left-censored.

Raw labels observed here are exactly `ST12000NM0008` and
`WDC WUH722222ALE6L4`. The default explicit mapping is identity. The prospective
prefix variant `WUH722222ALE6L4` is not observed in this quarter and is not silently
merged. If encountered, processing stops pending a justified explicit mapping.
Manufacturer/model presentation in a report is not proof of a CSV alias. The
different WDC alias issue in the prior audit concerned **WUH721816**, not this model.

OPEN PROBLEM: all-history earliest dates, historical unique-drive census, Q1
serial linkage and fraction traced before Q1 are unavailable. Blank cells are
unknown, not zero. Per-drive earliest dates in the private summary mean
**earliest observed Backblaze date in inspected files**, never installation date.

For context only, the [Q1 2026 published lifetime table](https://www.backblaze.com/blog/backblaze-drive-stats-for-q1-2026/)
reports Seagate 2,466 failures / 43,012,820 drive-days and WDC 360 /
22,472,050. These are publication-subset totals, not independently reproduced
historical totals or counts among Q1 survivors. Do not add the two observed
quarters' unique counts: serial overlap is unknown.

## Schema evidence

All 91 Q2 daily headers contain the same 186 columns: five core fields, three
metadata fields (`vault_id`, `pod_id`, `is_legacy_format`) and 178 SMART columns.
SMART 9, 197 and 5 raw are present every day. The observed headers are preserved
in the manifest; missing SMART columns are explicitly supported by the pipeline.
Q1 2026 has 197 columns in the authoritative prior audit.

Official [current schema](https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/Drive_Stats_Schema_Current.csv)
and [2018-onward changes](https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/Drive_Stats_Schema_2018_Onward.csv)
were inspected in the original audit (hashes in its manifest). They are not assumed
to be current for every archive. The [Q2 2023 report](https://www.backblaze.com/blog/?p=109338)
documents the three metadata additions; the [Q3 report](https://www.backblaze.com/blog/?p=110367)
documents three more and an initial `cluster_id` caveat. This stage audits raw
candidate telemetry, not a harmonized all-history full-column table.

## Network blocker and bounded next acquisition

The managed command failed with `curl (6) Could not resolve host`:

```bash
curl -fsSL https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q1_2026.zip --range 0-31 --max-time 30
```

It requests 32 public artifact bytes for a range-access smoke check, writes only
stdout, and reads the managed proxy/DNS configuration. The sandboxed path cannot
currently resolve that host for byte-range acquisition; a prior metadata HEAD
success does not establish working data access. No escalation or alternate
external terminal was attempted after resume. Completing Q1 serial-level evidence
needs a functioning managed network path or a user-supplied candidate-only extract.
This report does not ask for broader local-machine access.

PROPOSED METHOD: after the managed smoke check succeeds, read Q1's 90 daily
members selectively; then only December 18–31, 2025 and April 1–14, 2026 for
lookback/boundary linkage. Fourteen days is a proposed operational sensitivity
window, not a universal statistical threshold or proof of permanent exit. Resolve
the gap policy jointly before modelling. Exact proposed archive URLs:

- [Q4 2025](https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q4_2025.zip), approximately 1.2 GB compressed / 12.17 GB expanded.
- [Q1 2026](https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q1_2026.zip), 1,312,921,361 bytes compressed / approximately 12.02 GB expanded; prior official SHA1 `23448d5733a4762a9cf1d5e341fc240c2d10b13c`.
- [Q2 2026](https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q2_2026.zip), approximately 2.1 GB compressed / 11.7 GB expanded.

These size estimates come from the download page; the latter archives were not
newly downloaded/processed in this stage. Existing Q1 aggregate source access was
2026-09-29. Full historical discovery is deferred, not fabricated. Avoid another
unbounded Iceberg metadata scan; metadata freshness/coverage is not verified here.
