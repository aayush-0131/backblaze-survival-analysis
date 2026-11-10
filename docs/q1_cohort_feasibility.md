# Q1 2026 `ST12000NM0008` cohort construction: verified feasibility evidence (2026-11-02)

**Status.** The *missing-data* blocker in `docs/q1_minimal_path.md` is now resolved: the
official Q1 archive was retrieved, passed every integrity check, and the existing cohort
builder ran end to end on it. The **Q1 design gate stays BLOCKED**. It is now waiting
on recorded owner and group decisions, not on data. **No Kaplan–Meier, Cox or other
survival or inferential model was fitted.** No convention, censoring rule or
event-support threshold was chosen here.

**Sealed by design.** Section 2, step 3 of `q1_minimal_path.md` requires the minimum
event-support rule for 197 versus 5 to be agreed *before* anyone reads recorded events
by baseline group. For that reason, this document and the committed summary do not
report any per-group count from which events could be read or derived. That covers
failures, administrative censoring, follow-up and post-failure counts by 197/5 state.
The builder's stdout, which prints them, was redirected to the ignored `data/processed/`
tree and was not inspected. The values exist only in the Git-ignored
`data/processed/q1_cohort/cohort_accounting.csv`.

Machine-readable evidence:

- `docs/q1_retrieval_record.json`: smoke test, download, hashes, member CRCs, builder run
- `docs/q1_cohort_feasibility_summary.json`: outcome-blinded aggregates, regenerated
  and checked by `scripts/summarize_q1_cohort.py --check`

Per the minimal-path rule, nothing was copied into `results/` before group review.

## 1. Source and integrity (all PASS)

| Check | Result |
|---|---|
| 32-byte smoke test (`curl --range 0-31`) | HTTP 206, 32 bytes, `PK\x03\x04` header. On 2026-11-01 the same check gave a 403 |
| HEAD metadata | Content-Length 1,312,921,361; large-file SHA1 and B2 file ID equal `docs/source_q1_2026.json` |
| Retrieval | Option A: `curl -fL` to ignored `data/raw/` (07:50:14–07:51:01Z). Not extracted |
| Size | 1,312,921,361 bytes (exact) |
| SHA1 | `23448d5733a4762a9cf1d5e341fc240c2d10b13c`, which equals the recorded value |
| SHA256 (new, for future checks) | `cad66574292b89bae8ec8370dbb5e90d2e0b45d61341502708df328fdb15ed5c` |
| ZIP central directory | 91 entries = 90 daily CSVs + 1 directory entry. CRC32, compressed and uncompressed size match `results/audit/data_manifest.json` for 90/90 members |
| Full member CRC (`ZipFile.testzip`) | Passed, no corrupt member |
| Builder `--expect-manifest` CRC guard | Active; all 90 accepted |

## 2. Builder run and reproducibility

- **Command (unchanged builder, commit `1bee36d`):**
  `PYTHONPATH=src python scripts/build_cohort_skeleton.py --zip-path data/raw/data_Q1_2026.zip --expect-manifest results/audit/data_manifest.json --output-dir data/processed/q1_cohort`
- **Run:** exit 0, empty stderr, 3 min 5 s.
- **Built-in guards passed:** the `HistoryAudit` checks (unique `(date, serial)`,
  binary failure, filename date equals row date, alias guard) and both accounting
  reconciliation guards.
- **Output hashes:** `cohort_drives.csv` `beccd1a1…d552` and
  `cohort_accounting.csv` `33cd2bd9…b6e2`. An independent second run produced
  **byte-identical** outputs.
- **Re-verification:** `summarize_q1_cohort.py` refuses outputs whose hashes differ
  from the builder manifest, and recomputes calendar, accounting and reconciliation
  from the per-drive file.

## 3. Verified aggregate findings (outcome-blinded by group)

### Calendar completeness
- 90 of 90 daily members, 2026-01-01…2026-03-31, contiguous with no duplicates.
- 18,291–18,604 candidate rows per day.

### Reconciliation with the independent Q1 audit (`results/tables/model_inventory.csv`)

| | Builder | Recorded audit |
|---|---|---|
| Unique drives | 18,650 | 18,650 |
| Drive-days | 1,664,558 | 1,664,558 |
| Failure-flag rows | 129 | 129 |

There is one raw model label (`ST12000NM0008`) and no alias. Every included drive
has one baseline capacity (12,000,138,625,024 bytes), and all are valid.

### Cohort accounting (fixed baseline 2026-01-01)

| Class | Drives |
|---|---|
| Observed | 18,650 |
| Included (present on Jan 1, no flag on or before Jan 1) | **18,533** |
| Excluded: later arrival | 116 (Jan 112, Feb 1, Mar 3) |
| Excluded: failure flag on baseline date | 1 |

- **Inclusion check:** 18,533 + 116 + 1 = 18,650 ✔
- **Failure flags across all observed drives (129):** 111 included, 17 later arrivals,
  1 on baseline ✔.
- **Included outcomes (overall only):**
  - recorded failure 111
  - administrative censoring at Mar 31: 18,326
  - unexplained exit 96

  These sum to 18,533 ✔.
- **Included drive-days:** 1,656,525.
- **Recorded failures by month (overall):** Jan 37, Feb 29, Mar 45.
- **Post-failure rows:** 0. **Repeated failure flags:** 0.

### Baseline SMART states (Jan 1 row only; included drives)

| | 197 zero | 197 nonzero | 197 missing |
|---|---|---|---|
| **5 zero** | 17,210 | 52 | – |
| **5 nonzero** | 1,161 | 110 | – |
| **Total** | 18,371 | **162** | **0** |

- **SMART 5:** 17,262 zero, **1,271** nonzero, 0 missing.
- **The missing state is empty for both attributes.** Baseline SMART 9 is present for
  every included drive. 2 drives carry the in-window SMART 9 review flag (descriptor
  only, never age).
- **The attributes overlap:** 110 of the 162 drives that are 197-nonzero (68%) are
  also 5-nonzero.

### Unexplained exits (never treated as failures)

- 96 included drives (0.52%). By last observed date:

  | Last observed | Exits |
  |---|---|
  | Jan 6, 9, 12 | 4 |
  | Mar 24–27 | 4 |
  | Mar 28 | 31 |
  | Mar 29 | 29 |
  | Mar 30 | 28 |

- **88 of 96 (92%) are absent only on the last 1–3 days.** That is the same length as
  the most common within-quarter gaps (below). These are most plausibly unfinished
  gaps cut off by the window end, not departures, but only Apr 1–14 linkage can
  tell. 8 exits are "deep" (absent 4 or more days before Mar 31).
- 11 exiting drives also had an earlier gap episode.
- **Non-event burden by baseline group:**
  - 197: nonzero 3 / 162, zero 93 / 18,371
  - SMART 5: nonzero 16 / 1,271, zero 80 / 17,262

### Observation gaps (included drives)
- 1,886 drives (10.2%) have at least one gap, with 2,465 episodes and 6,102 missing
  drive-days (0.37% of included follow-up).
- Episodes per gap drive: 1 = 1,421; 2 = 356; 3 = 105; 4 = 3; 5 = 1. The longest gap
  is 38 days. For 935 gap drives the longest gap is 1 day; for 38 it exceeds 9 days.
- **Gap burden differs by baseline state (not an outcome):**
  - 197: nonzero 36/162 drives (22.2%) versus zero 1,850/18,371 (10.1%)
  - SMART 5: nonzero 181/1,271 (14.2%) versus zero 1,705/17,262 (9.9%)
- **Gaps and failures (overall, not by group):** 44 of 111 recorded failures (39.6%)
  had a gap episode before the first failure flag. None had a gap after it.

### Exploratory (one-off scratch rerun, not produced by committed code)
These numbers come from re-running the unchanged builder once more, keeping its
in-memory gap episodes so they could be dated. The rerun's outputs were
byte-identical to the main run.

- **Gaps are spread across the quarter.** Gap days fall on 88 of the 89 possible
  dates (6,606 gap drive-days including later arrivals). There are synchronized peaks:
  - Jan 5: 250 drives
  - Mar 9: 253 drives
  - Mar 8–12: 131–253 drives a day; Jan 18–20: 141–163 drives a day
- **21 of the 44 gap-preceded failures were flagged on the very day the drive
  reappeared.** For those drives the recorded failure date may be the date the
  failure was *ascertained*, not the date it occurred.

## 4. Unresolved methodological decisions (owner / group; none taken here)

1. **Event-support rule for 197 versus 5.** It must be written down *before* the
   sealed group counts are read. Outcome-blind context for the decision:
   - group sizes are 162 (197-nonzero) and 1,271 (5-nonzero)
   - the overall included recorded-failure proportion is 111 / 18,533 = 0.60%
   - if failure were unrelated to baseline state, that proportion would imply about
     1.0 failure in the 197-nonzero group and about 7.6 in the 5-nonzero group

   **Label (D8):** illustrative arithmetic under no association only. It is not an
   estimate and not a projection of the sealed counts.
2. **A6 (administrative censoring on Mar 31).** Applies to 18,326 drives as currently
   classified.
3. **A7 (exit censoring date).** For 88 of the 96 exits the two candidate dates differ
   by 1 day. The more consequential question is whether these are exits at all.
4. **A8 (gap policy).** Now has evidence:
   - 10.2% of included drives have gaps
   - gaps are more common in the nonzero baseline groups
   - 40% of failures follow a gap
5. **New: timing of failures flagged on the first day back after a gap.** Treat the
   flag date as the event date, or treat the event as occurring somewhere in the gap
   (interval-type). This interacts with A8.
6. **Terminal-first-flag policy.** No Q1 case for this model (0 post-failure rows,
   0 repeated flags). The policy still needs recording.
7. **Excluded failures.** Confirm that the 17 later-arrival failures and the 1
   baseline-date failure stay outside the fixed-baseline risk set, as designed.
8. **197/5 overlap.** The predeclared "switch to SMART 5" fallback would compare
   groups that share 110 drives. This should be acknowledged in the write-up.
9. **Standing limitations:** prevalent cohort and left truncation (no age origin),
   possible informative retirement, day-one ascertainment, and SMART 9 as a
   descriptor only.

## 5. Next scientifically justified action

**Record the event-support rule (item 1), together with A6–A8 and item 5, in
`docs/decision_log.md` before anyone opens the sealed group counts.** This costs no
data and is the only step that keeps the 197-versus-5 choice independent of the
outcome. After that:

- The owner unseals by reading the ignored `cohort_accounting.csv` and applies the
  rule. The owner then decides whether to lift the gate.
- In parallel, and outcome-blind, the owner can authorise the bounded Apr 1–14 2026
  linkage (14 members of `data_Q2_2026.zip`). It would resolve whether the 88
  near-end exits are gaps or departures; the 8 deep exits need no linkage.
- The Dec 18–31 lookback stays an optional sensitivity input.

KM/Cox remain out of scope until the owner approves.

## 6. Reproduce

```bash
curl -fL -o data/raw/data_Q1_2026.zip https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q1_2026.zip
```

```bash
sha1sum data/raw/data_Q1_2026.zip   # 23448d5733a4762a9cf1d5e341fc240c2d10b13c
```

```bash
PYTHONPATH=src python scripts/build_cohort_skeleton.py --zip-path data/raw/data_Q1_2026.zip --expect-manifest results/audit/data_manifest.json --output-dir data/processed/q1_cohort > data/processed/q1_cohort_stdout.json
```

```bash
PYTHONPATH=src python scripts/summarize_q1_cohort.py --check
```

The redirect keeps the sealed per-group counts off the terminal.

## 7. Update 2026-11-02: Apr 1–14 exit linkage

See [`q1_exit_linkage.md`](q1_exit_linkage.md). With the owner's authorisation, the 14
April daily members were read by byte range (about 316 MB of the 2.09 GB Q2
archive). Each member passed its CRC32 and size checks.

- 93 of the 96 unexplained exits reappeared, including **all 88 near-end exits** and
  5 of the 8 earlier exits. 3 January exits were not observed through Apr 14.
- §3 (Unexplained exits) and §5 above described the near-end exits as "most plausibly
  unfinished gaps". That is now verified for all 88. §5 also said "the 8 deep exits
  need no linkage", which proved wrong: the linkage covered all 96, and 5 of the 8
  reappeared.
- The Q1 cohort outputs, outcome classes and failure dates are unchanged. No group
  breakdown was computed and no model was fitted.
