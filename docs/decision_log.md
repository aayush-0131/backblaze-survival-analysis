# Decision log

## 2026-09-29 — quarter and scope

- Used Q1 2026 as explicitly directed, even though the live download page now also lists Q2 2026.
- Kept this phase as a data gate. No Cox model, Kaplan–Meier estimator, regression, machine-learning model, feature selection, confirmatory test, or final hypothesis was created.

## 2026-09-29 — acquisition safety

- Found only about 2.1 GiB free disk space.
- Rejected full ZIP retention and extraction: the artifact is 1.313 GB compressed and approximately 12.02 GB extracted.
- Tried the official read-only Iceberg copy as a no-download alternative; it exposed no Q1 2026 rows and was rejected as the controlling source.
- Used byte-range reads against the official ZIP, one daily CSV and one bounded chunk at a time.
- Added daily checkpoints, a 60-second network timeout, and bounded retries after transient DNS/read failures. Checkpoints are ignored and removed on success.

## 2026-09-29 — row and event policy

- Audited all raw line-item rows. Did not silently reproduce Backblaze's publication exclusions.
- Treated `(date, serial_number)` as the candidate drive-day key and verified zero duplicates.
- Treated only `failure == 1` as an observed source event. Disappearance was retained separately.
- Did not convert first Q1 appearance into installation date.
- Preserved observation gaps and non-failure exits as distinct audit evidence.

## 2026-09-29 — schema and model labels

- Used actual Q1 headers as quarter-specific authority because official schema documents are older.
- Preserved the two documentation misspellings as a comparison finding rather than renaming observed columns.
- Kept raw model labels in the main inventory. Flagged the `WDC WUH721816ALE6L4` / `WUH721816ALE6L4` alias split; canonicalization is required before choosing that hardware cohort.
- Manufacturer is a conservative model-prefix inference only. Unmapped values remain `Unknown`.

## 2026-09-29 — SMART policy

- Calculated reporting and zero fractions without imputation.
- Treated raw and normalized columns as availability pairs, not semantically interchangeable measurements.
- Used min/max/mean for compact numeric profiling. SMART distinct counts are bounded in the schema table (`0`, `1`, or `>=2`) to avoid large in-memory sets.
- Defined “major model” for the by-model coverage table as at least 1% of Q1 drive-days. This is a reporting-scope rule, not a permanent exclusion or statistical threshold.

## 2026-09-29 — candidate cohorts and verdict

- Proposed two single-model cohorts, a major-model stratified pool, and a manufacturer-defined diagnostic pool.
- Descriptive low-count flags (`<1,000` drives and `<10` failures) are configurable review cues, not universal sufficiency rules.
- Overall verdict: **READY WITH CONDITIONS**. A bounded historical first-appearance and model-specific SMART 9 semantics audit must precede a frozen survival design.

## 2026-10-06 — resumed bounded historical / SMART feasibility stage

- Verified the exact checkpoint, branch, clean tree and original four tests plus Q1 reconciliation. Preserved all authoritative Q1 result artifacts.
- Used only managed sandbox execution; did not interact with external DuckDB terminals, bypass the proxy, escalate acquisition or perform unbounded mirror scans.
- Found the interrupted Q2 2023 ZIP complete, verified all-entry CRC, size and local SHA1/SHA256; processed 91 compressed daily members in 50k chunks without expansion. Retained valid raw data, ignored checkpoint and compact per-drive outputs.
- Corrected the preliminary WDC timing: first in inspected Q2 files is April 8, not late Q2. Complete all-history first appearance is still open. Seagate is independently documented by Q1 2022; no birth/install date inferred.
- Kept exact raw model identity; did not normalize a hypothetical WDC prefix variant without observing and justifying it.
- Audited only predeclared SMART 9/197/5. Fixed zero/nonzero status, separate missingness, fixed April 1 and first-observed snapshots; no thresholds searched, inferential tests or fitted effects.
- Preserved 52 invalid capacity rows and 10 post-failure rows from two Seagate drives. Checkers flag genuine data-quality violations instead of discarding data to enforce ideal assumptions.
- SMART 9 endpoint rates support nominal hours, while daily 16/32-like increments and 180 excess-change flags need timing/firmware review. Q1 age integrity and lifetime continuity remain unvalidated.
- Gaps are not failures. Return-before-first-flag chronology is asserted only when complete post-event day coverage rules out later gaps; otherwise the count is unknown. No-gap eligibility is illustrative sensitivity accounting, not a recommended data exclusion.
- Reused Q1 aggregate counts; left all unavailable Q1 baseline-state/event/transition/gap/exit cells blank. Published lifetime counts are labelled external reporting-subset context, not reconstructed history.
- Managed range acquisition failed DNS. Scope reduction: completed local Q2 2023 and Q1 aggregate context; deferred Q1 serial linkage, bounded Q4 lookback/Q2 returns and full historical census.
- Prefer validating single-model Seagate fixed-baseline Q1 calendar follow-up; keep 197 lead / 5 predeclared alternative. Choose neither based on observed effect size. Proposed 14-day linkage is an operational sensitivity horizon, not permanence proof.
- Narrow design-approval gate: **BLOCKED** pending the missing acquisition/reconciliation. Original Q1 data gate stays READY WITH CONDITIONS. Joint review with the literature audit is required; no final hypothesis/cohort frozen and no modelling, push or merge performed.

## 2026-11-01 — issue #2: minimal Q1 path and cohort-construction skeleton

- Re-ran the baseline before editing: 14 tests passed; Q1 and history verifiers passed.
- Managed range smoke check to `f001.backblazeb2.com` failed (`CONNECT tunnel failed, response 403`; environment network policy). No Q1 candidate rows exist locally. Gate stays **BLOCKED**; no KM/Cox or other estimator was run.
- Added `backblaze_audit.cohort`: per-drive fixed-baseline records for one exact model (inclusion, baseline 197/5 state, first recorded failure vs administrative censoring vs unexplained exit, gap flags, post-failure counts) and reconciled accounting. Reuses `HistoryAudit` validation and existing `Source` readers. Tested only with invented fixtures.
- Proposed (not adopted) conventions are listed as A6–A8 in `docs/q1_minimal_path.md`; they need owner/group decisions. Unexplained exits remain non-events. SMART 9 stays a powered-hours descriptor, not age.
- Serial-level outputs default to the ignored `data/processed/q1_cohort/`. No raw data, result tables or prior artifacts were changed.

## 2026-11-02 — Q1 retrieval and cohort-construction feasibility run (PR #3)

- The owner authorised retrieval of the official Q1 2026 ZIP (about 1.3 GB) for cohort
  construction and feasibility validation only.
- The 32-byte smoke test to `f001.backblazeb2.com` now succeeds (HTTP 206, `PK` header).
  Retrieved with Option A to the ignored `data/raw/`, not extracted.
- Integrity: exact size, SHA1 equals the recorded large-file SHA1, 90/90 member CRC32 and
  sizes match `data_manifest.json`, `testzip` passed. The builder's `--expect-manifest`
  guard was active. Record: `docs/q1_retrieval_record.json`.
- Ran the unchanged `build_cohort_skeleton.py`. Reconciled exactly with the Q1 audit
  (18,650 drives / 1,664,558 drive-days / 129 failure flags). Outputs are deterministic
  (byte-identical rerun).
- **Sealing.** Following `q1_minimal_path.md` section 2 step 3, event counts by 197/5
  baseline group were not read or reported. The builder's stdout went to the ignored
  tree. `scripts/summarize_q1_cohort.py` publishes only outcome-blinded aggregates
  (`docs/q1_cohort_feasibility_summary.json`) and re-verifies output hashes and
  reconciliation.
- No convention (A6–A8), censoring date, gap policy or event-support threshold was
  chosen. New open item: timing of failures flagged on the first day back after a gap
  (21 of 111 included failures).
- Nothing was copied to `results/`. No KM, Cox or other estimator was run. No raw or
  drive-level data was committed. PR #3 stays draft and unmerged.
- The gate remains **BLOCKED**, now pending recorded decisions rather than missing data.

## 2026-11-02 — bounded Apr 1–14 linkage of Q1 unexplained exits (PR #3)

- The owner authorised retrieval of official Apr 1–14, 2026 daily files solely to
  investigate the 96 Q1 unexplained exits.
- Read the Q2 2026 ZIP central directory first. The 14 members are 316,484,017
  compressed bytes (15.1% of 2,092,757,685), so the full archive was not required.
  Read them by HTTP byte range with the repo-pinned `remotezip`; measured receive was
  320,330,942 bytes. Nothing was written to `data/raw/`.
- Integrity per member: 14/14 CRC32 verified on full decompression, sizes equal the
  directory, complete calendar, row dates equal file dates, 0 duplicate keys. The
  whole-archive SHA1 was not checked, because that would need the full download.
- Reused the same-session Q1 outputs after re-verifying their hashes. Matching is by
  serial across all model labels.
- Result: 93/96 reappeared (88/88 near-end, 5/8 earlier). 3 January exits were not
  observed through Apr 14; their status is unresolved, not retired or failed.
  4 reappeared drives carry an April failure flag, which is descriptive only and not
  a Q1 event.
- No change to cohort definition, baseline, censoring policy or failure dates. No
  SMART-group breakdown, no unsealing, no model fitted. Whether and how to use the
  linkage stays an owner/group decision (A6/A7).

## 2026-11-10 — owner confirmation of downloads; decision form opened (PR #3)

- Aayush confirmed in chat that both downloads made by the other session were
  authorised: the full Q1 2026 ZIP and the bounded Apr 1–14 2026 daily members.
- Opened `docs/q1_decision_record.md`, which collects the open decisions (D1–D9:
  event-support rule, A6–A8, gap-return timing, terminal-first-flag, excluded
  failures, presentation, gate) with options only. Every decision is blank; none
  was taken. The gate remains **BLOCKED**. No data was read, no counts were
  unsealed and no model was fitted.

## 2026-11-10 — D1–D8 recorded before unsealing (PR #3)

- Aayush: "go ahead with D1–D8 as proposed". The choices are the proposal of
  2026-11-10T20:53Z, now written into `docs/q1_decision_record.md` and
  `docs/q1_decisions.json`, labelled "selected by Claude at Aayush's request, pending
  group review".
- D1: keep SMART 197 if its nonzero group has ≥ 10 recorded Q1 failures, else switch
  to SMART 5 (no minimum for 5). D2 censor at Mar 31. D3 exits censored at last
  observed day, linkage as sensitivity (93 reappeared censored at Mar 31), 3 January
  exits at last seen, 4 April flags as a limitation. D4 at risk through gaps, gap-day
  exclusion as sensitivity. D5 flag date is the event date. D6 first flag terminal.
  D7 exclusions kept and reported. D8 label the expected-failures figure; state the
  110-drive overlap.
- The D1 threshold is also fixed in code (`backblaze_audit.decisions`). The unseal
  script refuses to run unless `q1_decisions.json` is committed and unmodified.
- This entry is committed and pushed **before** the sealed accounting is read.
- D9 is not signed. The gate stays **BLOCKED**; no model is fitted.

## 2026-11-10 — sealed counts read after D1; D1 applied (PR #3)

- After `e3cf5dd` (D1–D8 recorded, pushed 2026-11-10T20:59:57Z), ran
  `scripts/unseal_q1_group_counts.py`. It verified the accounting hash
  (`33cd2bd9…b6e2`) and the committed decision file, then applied D1.
- SMART 197-nonzero: 28 recorded failures among 162 included drives, which is ≥ 10, so
  **SMART 197 is kept**. Other groups: 197-zero 83 / 18,371; 5-nonzero 61 / 1,271;
  5-zero 50 / 17,262. Descriptive counts only (`docs/q1_group_counts.json`).
- D9 is not signed. The gate stays **BLOCKED**; no model was fitted.

## 2026-11-10 — owner signs D1–D9; analysis plan pre-specified (PR #3)

- Aayush: "Go ahead. I sign D9 and others". D1–D8 are now signed by the owner, and
  D9 is signed, which lifts the gate for the plan in `docs/q1_analysis_plan.md`.
- D9's prerequisite, a joint review with the teammate SMART/literature audit, is not
  documented in the repository, and no such audit exists on any branch. The owner
  signed regardless; this is carried as a limitation.
- The plan covers:
  - KM by baseline SMART 197 group, plus one Cox model with a single binary
    covariate (Efron ties), with a PH check;
  - sensitivities S1 (linkage: reappeared exits censored at Mar 31) and S2 (gap
    days removed via start/stop intervals);
  - lifelines as the engine, with a statsmodels cross-check.
- The plan is committed **before** any model is fitted.

## 2026-11-10 — pre-specified survival analysis run (PR #3)

- Ran `scripts/fit_q1_survival.py` under signed D9 and the plan committed in `2b91f38`.
  Inputs were hash-verified, and the gap episodes were re-derived with byte-for-byte
  reproduction of `cohort_drives.csv`.
- Primary: KM S(89) is 0.9955 for 197 = 0 and 0.8262 for 197 > 0. Cox HR 43.2
  (95% CI 28.1–66.3). The PH test rejects proportionality (p = 0.0069): the excess
  hazard is concentrated early. S1 gives HR 43.2 and S2 gives HR 44.1.
- Numerical and reporting deviations, recorded in `docs/q1_survival_results.md` §3:
  - damped optimisers, because undamped Newton diverged;
  - a half-day entry shift in the statsmodels cross-check, to match the plan's
    strict risk set;
  - KM at-risk counts computed directly;
  - no PH test for S2.

  None of these changes the model.
- Refactor: `run_cohort` now delegates its streaming loop to `stream_cohort`. Its
  outputs are byte-identical, as the analysis rerun verified.
