# Minimal Q1 path to class deliverables — plan and construction handoff (2026-11-01)

> **Update 2026-11-02.** Q1 rows have now been acquired and verified, and the builder
> has run on them. See [`q1_cohort_feasibility.md`](q1_cohort_feasibility.md). The
> missing-data blocker below is resolved. The gate stays **BLOCKED**, pending the
> section 7 decisions. Event counts by baseline group are sealed until the
> event-support rule is recorded. The original text below is kept as written.

**Status: Q1 2026 baseline-warning design is still BLOCKED.** No Q1 candidate
rows were available in this session, so nothing was fitted and no Q1 cohort
count is reported. This document is a proposal for Aayush and the group to
review; it changes no methodology. The historical Q2 2023 gate keeps its
distinct scope and its results are unchanged. The Q1 data gate
(READY WITH CONDITIONS) is also unchanged.

Inputs read: `README.md`, `results/audit/history_audit_summary.md`,
`docs/survival_data_feasibility.md`, `docs/decision_log.md`,
`docs/smart_warning_feasibility.md`, `docs/time_origin_options.md`,
`docs/smart9_semantics.md`, provenance JSON and all tests.

## 1. What Q1 information is missing, exactly

Everything listed here needs **serial-level Q1 rows for `ST12000NM0008`**. The
committed Q1 artifacts are marginal aggregates and cannot produce it. Nothing
below may be estimated from those aggregates.

| Needed | Why | Available now? |
|---|---|---|
| Drives present on 2026-01-01 (fixed-baseline risk set) | Defines the prevalent cohort | No: only the 18,650 all-quarter unique drives are known |
| Later arrivals (first seen after Jan 1) | Excluded from the fixed baseline; size shows selection | No |
| Failure flag on Jan 1 | Not a subsequent event; must be excluded and counted | No |
| Baseline SMART 197 state (zero / nonzero / missing) per drive | Predeclared lead warning | No: only drive-day nonzero fractions |
| Baseline SMART 5 state per drive | Predeclared feasibility alternative | No |
| Recorded failures **after** baseline by 197/5 state | Event support per group | No: 129 is an all-quarter count, not by group or baseline-conditional |
| Administrative censoring on Mar 31 versus unexplained earlier exit | Censoring mechanism; exits are never failures | No model-specific split |
| Gap episodes (count, length, before/after first flag) | Ascertainment and at-risk definition | No model-specific Q1 gap data |
| Post-failure rows and repeated flags | Terminal-event policy | Q1 all-drive check found none; recheck per drive |
| SMART 9 pair integrity (decreases, >48 h excess) | Needed only if powered hours is used as a descriptor | No: only coverage (7 missing rows) |
| Dec 18–31 lookback and Apr 1–14 linkage | Separate long-standing from recent warnings; resolve Q1-end absences | No: needs Q4 2025 and Q2 2026 members |

## 2. Minimal path (conditional; needs owner and group approval)

1. **Design (leading, conditional).** Single model `ST12000NM0008`. Fixed
   baseline 2026-01-01. Calendar follow-up to 2026-03-31. The event is the first
   `failure == 1` date after baseline. Baseline SMART 197 raw `>0` is the
   predeclared lead. SMART 5 raw `>0` is the predeclared feasibility
   alternative. Calendar days is the time scale. SMART 9 is a baseline
   powered-hours descriptor at most, not age.
2. **Acquire** the Q1 candidate rows (§5). Run `scripts/build_cohort_skeleton.py`
   (§4) to get per-drive records and reconciled accounting.
3. **Gate review before any estimator.** Check the §3 items. Before reading
   events by group, agree in writing on a minimum event-support rule for
   choosing between 197 and 5. Fixing that rule after seeing the group counts
   would make the choice depend on the outcome.
4. **Then, and only if the gate passes**, the class deliverable could be
   descriptive Kaplan–Meier curves by baseline state with Q1 calendar follow-up,
   plus at most one simple Cox model. Unexplained exits and gaps would get
   sensitivity analyses. This is a plan, not an approval. It is not done here.
5. **Bounded linkage** (Dec 18–31, Apr 1–14; 28 members) can follow as a
   sensitivity input. It is not a precondition for constructing the Q1 cohort.

### Non-negotiable checks (each needs a recorded result before modelling)

- Source calendar complete for Jan 1–Mar 31. The builder refuses otherwise.
- Member CRC32 matches `results/audit/data_manifest.json`
  (`--expect-manifest`).
- Unique `(date, serial)` keys, binary failure, filename date equals row date,
  and no unapproved model alias. These are enforced by the `HistoryAudit`
  ingest checks.
- Accounting reconciles: included + later arrivals + baseline failures equals
  observed drives, and failure + censoring + exit equals included. This is
  asserted in code.
- Baseline state taken from the Jan 1 row only. Missing is its own state.
- Unexplained exits are never failures. The exit share and the gap burden are
  reported by stratum.
- Post-failure rows and repeated flags are counted. A terminal-first-flag
  policy must be written down before they are truncated.
- Day-one / prior-presence ascertainment, left truncation (prevalent drives)
  and possible informative retirement are stated as limitations.

## 3. Assumptions table (checked against repository evidence)

| # | Assumption | Status | Evidence / consequence |
|---|---|---|---|
| A1 | Q1 has all 90 daily files and a stable schema | **Verified** (prior audit) | `data_manifest.json`; the builder re-checks completeness |
| A2 | Seagate Q1 is large enough for single-model work | **Verified, all-quarter only** | 18,650 drives / 129 recorded failures (preserved Q1). Baseline-conditional and by-group support: **unknown** |
| A3 | SMART 197 and 5 are reported for Seagate in Q1 | **Verified, drive-day level** | 99.9996% coverage. Baseline-drive coverage: **unknown** |
| A4 | SMART 9 means nominal powered hours | **Inference** (Q2 2023 endpoints) | Not physical or installation age. Q1 integrity is unchecked |
| A5 | Only `failure == 1` is an event | **Adopted convention** | Exits stay a separate class. Exits may be informative (retirement) |
| A6 | A drive present on Mar 31 without a flag is administratively censored | **Proposed** | Standard for a window design. Needs group sign-off |
| A7 | Censoring time for an unexplained exit = last observed date | **Proposed; open** | The alternative is the first missing day (`last_observed_date` + 1). The skeleton records the last observed date. Decision needed |
| A8 | Gaps are not failures, and a drive is at risk across a gap | **Open** | Q2 2023 shows heavy synchronized gaps. Gap handling needs an explicit policy plus a sensitivity check |
| A9 | A failure flag on Jan 1 is excluded from subsequent events | **Adopted (history.py convention)** | Counted separately in the accounting |
| A10 | Prevalent-cohort risk is conditional on being observed at baseline | **Inference** | Not lifetime risk. Left truncation is unresolved without an age origin |
| A11 | Q2 2023 counts transfer to Q1 | **Rejected** | Different deployment era. Q2 2023 is design-support evidence only |

## 4. What was built in this change (tested, synthetic fixtures only)

`src/backblaze_audit/cohort.py` reuses `HistoryAudit` validation and the
existing `Source` readers (local ZIP, directory, remote ZIP byte ranges). It
produces, per drive:

- `inclusion`: `included`, `excluded_later_arrival` or
  `excluded_failure_on_or_before_baseline`
- `baseline_smart_197_raw_state` and `baseline_smart_5_raw_state`: zero /
  nonzero / missing, from the baseline row only
- `baseline_smart_9_raw_powered_hours_counter`: a raw descriptor, never age
- `outcome`: `recorded_failure`, `administrative_censoring` or
  `unexplained_exit`, plus `outcome_date` and `followup_days` (calendar)
- Gap flags: `gap_episodes`, `missing_days_in_gaps`, `longest_gap_days`,
  `gap_before_first_failure` and `gap_after_first_failure`
- Post-failure and repeated-flag counts, the SMART 9 review flag, and
  `boundary_linkage = not_attempted`

`cohort_accounting` reconciles totals overall and by 197 and 5 baseline
strata. These are descriptive counts with no tests or estimates.
`tests/test_cohort.py` has 11 tests built on invented trajectories, which are
not Backblaze data.

## 5. Exact input-data request / permitted retrieval (for Aayush)

The managed cloud session could not reach the source. On 2026-11-01,
`curl --range 0-31` to `f001.backblazeb2.com` returned **CONNECT tunnel failed,
response 403**: the environment's network policy denies that host. Choose one
option:

**Option A (recommended): local machine, official ZIP.** This is a 1.31 GB
download. Do not extract it and do not commit it.

```bash
curl -fL -o data/raw/data_Q1_2026.zip https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q1_2026.zip
```

```bash
shasum -a 1 data/raw/data_Q1_2026.zip   # expect 23448d5733a4762a9cf1d5e341fc240c2d10b13c
```

```bash
PYTHONPATH=src python scripts/build_cohort_skeleton.py --zip-path data/raw/data_Q1_2026.zip --expect-manifest results/audit/data_manifest.json --output-dir data/processed/q1_cohort
```

**Option B: no local retention.** Use `--remote-url
https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q1_2026.zip`
in place of `--zip-path`. It reads the members by byte range, so it still
transfers about 1.3 GB.

**Option C: cloud session.** Add `f001.backblazeb2.com` to this environment's
allowed network domains, then rerun Option B in a new session.

Outputs go to the Git-ignored `data/processed/q1_cohort/`:

- `cohort_drives.csv` (serial-level, **do not commit**)
- `cohort_accounting.csv`
- `cohort_manifest.json`

Share only `cohort_accounting.csv` and the manifest for group review, and copy
any aggregate into `results/` only after review. The 28 linkage members
(2025-12-18…31 from `data_Q4_2025.zip`, 2026-04-01…14 from `data_Q2_2026.zip`)
are a later, separate request. The skeleton does not link them yet.

## 6. Fallback (proposal only; needs owner and group approval)

- If the 197 nonzero group lacks the pre-agreed event support, switch to
  SMART 5. Document the reason before modelling, as already predeclared.
- If neither attribute is supported, report a descriptive Q1 cohort
  (accounting, exits, gaps) without group comparison.
- If Q1 rows cannot be obtained before the deadline, Q2 2023 Seagate (already
  processed locally by the owner) could serve as an explicitly labelled
  *historical methods demonstration*. Its scope differs, so it is not a Q1
  result and must not be presented as one.

## 7. Requirements to get unblocked (checklist)

- [ ] Q1 candidate rows acquired by Option A, B or C, with SHA1 / CRC32 matching
- [ ] `build_cohort_skeleton.py` run; accounting reconciles; manifest kept
- [ ] Group agrees on a minimum event-support rule *before* reading events by
      stratum
- [ ] Decisions on A6–A8 (administrative censoring, exit censoring date, gap
      policy) recorded in `decision_log.md`
- [ ] Terminal-first-flag policy for post-failure rows recorded
- [ ] Joint review with the teammate SMART/literature audit
- [ ] Owner approval to lift the BLOCKED gate. Only then may any KM or Cox work
      start

## 8. Ten-minute review note

- **Completed:** gap analysis (§1), conditional minimal plan (§2), checked
  assumptions (§3), and a tested per-drive cohort builder with a CLI and CRC
  guard (§4). 25 of 25 tests pass, and the Q1 and history verifiers still pass.
  No existing result file changed.
- **Still blocked:** all Q1 cohort-level numbers. The managed network denies the
  Backblaze host. No Q1 rows exist in the repository or the session.
- **Decide next:**
  1. Which acquisition option (A, B or C)?
  2. A7: censor exits at the last observed day or the first missing day?
  3. A8: gap policy (at risk throughout, or sensitivity exclusion)?
  4. The event-support rule for 197 versus 5, fixed before tabulation.
  5. Whether the Q2 2023 fallback is acceptable at all.

## 9. Checklist status (2026-11-02)

- [x] Q1 candidate rows acquired (Option A). SHA1 and all 90 member CRC32 match
  (`q1_retrieval_record.json`).
- [x] `build_cohort_skeleton.py` run, accounting reconciles, manifest kept
  (`q1_cohort_feasibility.md`).
- [ ] Event-support rule. **Still open; group counts sealed until it is recorded.**
- [ ] A6–A8, plus timing of failures flagged on return from a gap (new). Still open.
- [ ] Terminal-first-flag policy. Still open, though Q1 has 0 post-failure rows for this model.
- [ ] Joint review with the teammate SMART/literature audit.
- [ ] Owner approval to lift the BLOCKED gate.

## 10. Status (2026-11-02, later)

- [x] Bounded Apr 1–14 linkage for the 96 Q1 exits (`q1_exit_linkage.md`). It is a
  sensitivity input only; the Q1 cohort is unchanged. The Dec 18–31 lookback has not
  been retrieved.

## 11. Status (2026-11-10)

- Owner confirmed both downloads were authorised.
- All remaining unblock items are decisions, now collected with options in
  [`q1_decision_record.md`](q1_decision_record.md) (D1–D9, all blank).
