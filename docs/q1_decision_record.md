# Q1 design decision record — form for Aayush and the group (opened 2026-11-10)

**Status update 2026-11-10: D1–D8 recorded** (selected by Claude at Aayush's request, pending group review; machine-readable copy in `q1_decisions.json`). **D9 is not signed; the gate stays BLOCKED.**

**Original status: BLOCKED. Every decision below is blank.** This form collects in one place
the open decisions from `q1_minimal_path.md` (A6–A8), `q1_cohort_feasibility.md` §4
and `q1_exit_linkage.md` §5. It lists options and consequences only; it does not
recommend or adopt any of them. Fill in each **Decision** line (who, date, choice,
reason) and copy the entry into `decision_log.md`.

Rules that apply to every item:

- Decide **D1 before anyone reads the sealed per-group counts**
  (`data/processed/q1_cohort/cohort_accounting.csv` or the builder's saved stdout).
  Writing D1 after seeing them makes the 197-versus-5 choice depend on the outcome.
- Unexplained exits are never failures, under any option.
- SMART 9 stays a powered-hours descriptor, not age.
- No KM, Cox or other estimator is run until D9 is signed.

Outcome-blind context below is copied from the committed summaries; no new numbers.

## D1. Event-support rule for SMART 197 (lead) versus SMART 5 (alternative)

Context: 197-nonzero group has 162 included drives; 5-nonzero has 1,271; 110 drives
are nonzero on both. 111 recorded failures among 18,533 included drives overall.

Options (not exhaustive):

- (a) Keep 197 if its nonzero group has at least *k* recorded failures; otherwise
  switch to 5. The group must fix *k* here.
- (b) Keep 197 regardless of event count; report sparse-group limitations.
- (c) Report both attributes descriptively, with 197 labelled primary.

**Decision:** Option (a) with *k* = 10. Keep SMART 197 if its nonzero baseline group has at least 10 recorded failures in the Q1 window (ties keep 197); otherwise switch to SMART 5. The rule as written sets no minimum for SMART 5. Reason: matches the repository's existing "<10 failures" review cue. Recorded and committed **before** the sealed counts were read. Selected by Claude at Aayush's request ("go ahead with D1–D8 as proposed", 2026-11-10); **pending group review**.

**D1 applied (2026-11-10, after the decision commit `e3cf5dd`):** the 197-nonzero group has 28 recorded failures (≥ 10), so SMART 197 is kept. See `q1_group_counts.json`.

## D2. Administrative censoring on Mar 31 (A6)

Drives present on Mar 31 with no failure flag (18,326 as currently classified).

- (a) Censor at Mar 31 (standard for a fixed-window design).
- (b) Other (state).

**Decision:** Option (a): censor at Mar 31. Selected by Claude at Aayush's request ("go ahead with D1–D8 as proposed", 2026-11-10); **pending group review**.

## D3. Exits and the Apr 1–14 linkage (A7)

96 unexplained exits; 93 reappeared by Apr 14 (all 88 near-end, 5 of 8 earlier);
3 January exits unresolved.

- (a) Ignore the linkage; censor exits at the last observed Q1 day.
- (b) Ignore the linkage; censor exits at the first missing day.
- (c) Use the linkage as primary classification: reappeared drives count as gaps
  spanning Mar 31, and are then censored at Mar 31 or at their last Q1 day (choose).
- (d) Use the linkage only as a sensitivity analysis alongside (a) or (b).

Also decide how the 3 unresolved January exits are censored, and whether the 4
April failure flags appear in the informative-censoring limitation.

**Decision:** Option (d) with (a). Primary: censor exits at their last observed Q1 day. Sensitivity: use the April linkage, treating the 93 reappeared drives as censored at Mar 31. The 3 unresolved January exits are censored at their last observed day. The 4 April failure flags go in the informative-censoring limitation. Selected by Claude at Aayush's request ("go ahead with D1–D8 as proposed", 2026-11-10); **pending group review**.

## D4. Gap policy (A8)

10.2% of included drives have at least one gap; gaps are more common in the nonzero
baseline groups; 44 of the 111 failures follow a gap.

- (a) Treat drives as at risk throughout a gap.
- (b) Remove gap days from the risk set (start/stop intervals).
- (c) (a) as primary, with a no-gap or gap-excluded sensitivity analysis.

**Decision:** Option (c): at risk throughout gaps as primary, with a sensitivity analysis that excludes gap days. Selected by Claude at Aayush's request ("go ahead with D1–D8 as proposed", 2026-11-10); **pending group review**.

## D5. Timing of failures flagged on the first day back after a gap

21 of the 44 gap-preceded failures were flagged on the day the drive reappeared
(exploratory figure, not produced by committed code).

- (a) Use the flag date as the event date.
- (b) Treat the event as occurring somewhere in the gap (interval-type), possibly as
  a sensitivity analysis.

**Decision:** Option (a): the flag date is the event date. The 21 return-day failures are stated as a limitation. Selected by Claude at Aayush's request ("go ahead with D1–D8 as proposed", 2026-11-10); **pending group review**.

## D6. Terminal-first-flag policy

Q1 has 0 post-failure rows and 0 repeated flags for this model, so this has no Q1
effect, but the policy should still be written down for reuse.

- (a) The first flag is terminal; later rows are audited and dropped from risk time.
- (b) Other (state).

**Decision:** Option (a): the first flag is terminal. Selected by Claude at Aayush's request ("go ahead with D1–D8 as proposed", 2026-11-10); **pending group review**.

## D7. Failures outside the fixed-baseline risk set

17 failures among later arrivals and 1 failure on the baseline date are excluded by
design.

- (a) Confirm exclusion and report the counts.
- (b) Other (state).

**Decision:** Option (a): keep the 17 later-arrival failures and the 1 baseline-date failure excluded, and report the counts. Selected by Claude at Aayush's request ("go ahead with D1–D8 as proposed", 2026-11-10); **pending group review**.

## D8. Presentation items

- The "expected failures per group under no association" figure (about 1.0 and 7.6)
  in `q1_cohort_feasibility.md` §4: keep or remove before D1 is set?
- How to state the 110-drive overlap between the 197 and 5 nonzero groups.

**Decision:** Keep the "expected failures" figure, labelled plainly as illustrative arithmetic under no association (not an estimate or projection). State the 110-drive overlap between the 197 and 5 nonzero groups. Selected by Claude at Aayush's request ("go ahead with D1–D8 as proposed", 2026-11-10); **pending group review**.

## D9. Lift the gate

Requires D1–D8 recorded, and joint review with the teammate SMART/literature audit.

**Decision (owner):** ____________________

## Source of the D1–D8 choices

Proposed on 2026-11-10 (20:53Z) by the Claude session that opened this form, as
"likely picks" to be recorded only on Aayush's request; Aayush replied "go ahead with
D1–D8 as proposed". That proposal also noted that, at the overall 0.6% failure rate,
about 1 failure would be expected in the 162-drive 197-nonzero group under no
association, so a switch to SMART 5 under D1 is fairly likely. The rule is still
fixed before the counts are read. Any later change to D1 by the group would be made
after the counts are known and should be labelled outcome-informed.
