# Q1 unexplained exits: bounded Apr 1–14, 2026 linkage (2026-11-02)

**Scope.** This run checks whether the 96 included `ST12000NM0008` drives classified
as `unexplained_exit` in the verified Q1 cohort appear again in the official daily
files for 2026-04-01 to 2026-04-14.

**Nothing in the Q1 cohort changed:** not its definition, baseline, outcome classes,
censoring dates or failure dates. The Q1 output hashes were re-verified before and
after the run.

**Nothing was fitted:** no Kaplan–Meier, Cox or other model. Nothing is broken down by
baseline SMART 197/5 group, and the sealed `cohort_accounting.csv` was hashed for
integrity only, never read.

Machine-readable evidence:

- `docs/q2_linkage_retrieval_record.json`: source, estimate, transfer, integrity
- `docs/q1_exit_linkage_summary.json`: aggregate linkage counts and per-member
  CRC32, sizes, row counts and SHA256

Serial-level records stay in the Git-ignored `data/processed/q1_exit_linkage/`.

## 1. Minimum data and transfer

- **Minimum set:** the 14 daily members `2026-04-01.csv` … `2026-04-14.csv` of
  `data_Q2_2026.zip`. A complete calendar is needed to say "not observed through
  Apr 14". Each member must be decompressed whole, because DEFLATE has no row-level
  random access.
- **Estimate (from the ZIP central directory, before any data transfer):**
  316,484,017 compressed bytes, which is 15.1% of the 2,092,757,685-byte archive. The
  full archive was **not** required.
- **Measured:** 320,330,942 bytes received on the network interface. That covers the
  members plus the directory reads and TLS/HTTP overhead. Nothing was written to
  `data/raw/`.

## 2. Source and integrity checks

| Check | Result |
|---|---|
| HEAD | Content-Length 2,092,757,685, `Accept-Ranges: bytes`, B2 file ID and large-file SHA1 header recorded |
| Member CRC32 | 14/14 verified on full decompression |
| Decompressed size | 14/14 equal the central-directory size |
| CRC32 and size consistency | Identical between the pre-retrieval directory read and the run |
| Calendar | Apr 1–14 complete, 14 distinct dates |
| Row date equals filename date | All 4.84 M rows |
| Duplicate serial keys per day | 0 |
| Rows per day | 345,143–347,458 overall; 18,345–18,495 for `ST12000NM0008` (Q1 range 18,291–18,604) |
| Whole-archive SHA1 | **Not verified.** That needs the full 2.09 GB download, which was not needed. Integrity rests on the per-member checks above |

## 3. Verified linkage counts

Serials were matched across **all** model labels. Every match carried the label
`ST12000NM0008`, so no relabelled serials were found.

| | Exits | Reappeared (verified) | Not observed through Apr 14 |
|---|---|---|---|
| **All exits** | 96 | **93** | **3** |
| Near-end (last seen Mar 28–30) | 88 | **88** | 0 |
| Earlier (last seen Jan 6–12 or Mar 24–27) | 8 | **5** | **3** |

**Earliest reappearance date (all 93):**

| Date | Drives | Of which near-end | Of which earlier |
|---|---|---|---|
| Apr 1 | 78 | 77 | 1 |
| Apr 2 | 6 | 3 | 3 |
| Apr 3 | 1 | 1 | 0 |
| Apr 6 | 6 | 6 | 0 |
| Apr 8 | 1 | 1 | 0 |
| Apr 9 | 1 | 0 | 1 |

- **Days absent before reappearance** (counting from the last Q1 observation):
  - 1–3 days: 78 drives
  - 4–9 days: 14 drives
  - 89 days: 1 drive (one January exit)
- **Earlier exits:** all 4 last seen Mar 24–27 reappeared. Of the 4 last seen in
  January (Jan 6, 9, 9, 12), 1 reappeared on Apr 9 and **3 were not observed**.
- **Presence on Apr 14:** 80 of the 93 reappeared drives were present. The other 13
  left again inside the window: 4 of them carry an April failure flag (below), and 9
  were not observed on Apr 14 without any flag.
- **Failure flags in Apr 1–14** (descriptive, outside the Q1 window, **not** Q1
  events): 4 of the 93 reappeared drives, 1 near-end and 3 earlier. In each case the
  flag came 1–2 days *after* the return day, not on it.

## 4. What is and is not established

- **Verified:** for 93 of 96 exits, the same serial is observed again in official daily
  files within 14 days of Mar 31. For all 88 near-end exits, the Q1 "exit" was an
  observation gap that crossed the window end, not a departure from the fleet.
- **Not established:**
  - **The 3 unobserved drives.** "Not observed through Apr 14" is *unresolved*, not
    retirement and not failure. All three were last seen in January, so each was
    already unobserved for more than 80 days of Q1 and 14 more days of April. A
    longer gap, a retirement, a failure that was never flagged, or a serial
    re-registration cannot be told apart with these data.
  - **The 4 April failure flags.** They show that some drives that "exited" Q1 later
    failed. That bears on whether non-failure exits may be informative. They do
    **not** change Q1 failure dates or outcomes; Q1 follow-up ends Mar 31 by design.
  - **The 9 drives absent again on Apr 14 without a flag.** Their status after
    reappearing is likewise unresolved.
  - **Physical continuity.** Reappearance is a match on serial number. Physical
    identity and continuity of the drive are not otherwise verified.

## 5. Decisions this linkage informs (taken later in `q1_decisions.json`, D3)

1. **Whether the linkage is used at all.** If it is, as primary classification or as
   a sensitivity analysis, it would change 88 near-end and 5 earlier exits from
   "unexplained exit" to "gap spanning the window end". Whether those drives are then
   treated as administratively censored on Mar 31, or at their last Q1 observation,
   is the existing A6/A7 decision.
2. **Handling of the 3 unresolved January exits** under A7.
3. **Whether post-window failure flags** (4 drives) belong in any limitation or
   sensitivity discussion of informative exits.
4. **The sealed items are unchanged:** the event-support rule for 197 versus 5 must
   still be recorded before the group counts are read.

## 6. Reproduce

```bash
pip install remotezip==0.12.3
```

```bash
PYTHONPATH=src python scripts/link_q1_exits.py --remote-url https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q2_2026.zip
```

The script needs the hash-verified Q1 outputs in `data/processed/q1_cohort/`. Rebuild
them first if absent. It refuses to start if the
selected members exceed `--max-compressed-bytes` (default 400 MB).
