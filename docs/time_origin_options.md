# Time origin and smallest defensible window

The proposed estimand concerns subsequent **recorded failure**, conditional on
being observable and eligible at baseline, not lifetime reliability from birth.
No survival estimator, fitted model or final hypothesis has been created.

## Four time scales

| Scale | Observed | Assumptions / censoring and entry | Burden / decision |
|---|---|---|---|
| Calendar follow-up from January 1 | Days from fixed snapshot to first recorded event, last observation or administrative end | Prevalent cohort conditional on survival/observation at baseline. Unflagged exits require sensitivity and a defensible censoring policy; daily records cannot locate exact failure time. | Low; preferred primary scale after Q1 baseline reconciliation. READY WITH CONDITIONS as a design option, not a modelling approval. |
| Time since earliest Backblaze observation | Earliest date in inspected files | Full historical coverage needed to establish dataset-first appearance; installation still unknown. Restricting history to Q1 survivors creates selection. Prior unobserved exposure cannot be credited. | High; descriptive only. BLOCKED for complete history-based age. |
| SMART-9 powered age | Raw counter at observed snapshots | Nominal hours supported by Q2 endpoint behavior; physical age and powered age differ. Firmware, counter anomalies and gaps need review; event age is daily-resolution. Pre-entry counter is not observed risk time. | Medium; REVISE until Q1 longitudinal integrity is checked. Potential baseline descriptor, not yet the primary survival clock. |
| Delayed entry using SMART 9 | Counter at entry and exit | Requires valid monotone common powered-age scale, independent truncation/censoring assumptions and explicit risk-set entry at observed age. Selection into Backblaze is not random. No backfilled pre-entry risk time. | High; BLOCKED pending counter integrity and selection justification. |

INFERENCE: recovering more pre-Q1 serial observations would improve knowledge
of observation history but would not itself recover birth. Historical SMART 9
may expose pre-entry powered age; it cannot establish manufacture, installation,
powered-off time, unseen failures or absent drive intervals. Delayed entry is a
statistical treatment of selection, not a cure for unknown age or informative exits.

## Window comparison

VERIFIED FACT: Q1 includes Seagate 18,650 drives / 129 recorded events and WDC
45,638 / 42. These are all-quarter totals. Q2 2023 includes Seagate 19,830 / 157
and WDC four / zero. All-history unique drives and events have not been measured.
The additional quarters below have no measured incremental counts yet.

- **Q1 only:** smallest follow-up, strong SMART coverage, manageable sequential
  processing; unresolved January 1 groups, day-one ascertainment and boundary
  returns. Does not establish incident entry or lifetime age. Candidate only.
- **Q1 + limited Q4 lookback:** retain Q1 events; previous values can distinguish
  longstanding baseline warnings from recent/missing states. Must not use future
  warnings to classify January 1. Requiring lookback completeness would select
  stable, prevalent drives and needs accounting. Extra drives/events unknown.
- **Q1 + lookback + Q2 linkage:** preferred smallest *acquisition* plan, not a
  longer event window. Proposed December 18–31 and April 1–14 add 28 daily
  members (118 total). Link Q1-end absences to returns and recorded Q2 flags,
  but keep Q2 events outside the primary Q1 endpoint. Fourteen days does not
  prove that an unresolved exit is permanent; report sensitivity to the linkage
  horizon. No measured improvement is claimed yet.
- **Longer historical follow-up:** might improve sparse warning-group event
  support, but introduces deployment/firmware/schema shifts, changing selection
  and more acquisition. Q2 2023 WDC is a four-drive test cohort, not comparable
  support for modern Q1 deployment. REVISE unless bounded Q1 checks demonstrate
  a specific design limitation that extension can address.

PROPOSED METHOD: favor one-model Seagate fixed January 1 baseline with Q1
calendar follow-up, 197 status predeclared and 5 as the documented alternative.
Acquire limited lookback and boundary linkage before final eligibility/gap policy.
Do not select by observed effect size. Jointly review this and the literature
audit before freezing the question. Do not require SMART 9 merely for convenience
if the primary design does not need it; age adjustment/use remains unresolved.

## Gaps, exits and terminal events

VERIFIED FACT: all daily **source files** exist in Q2 2023, but 15,245 Seagate
drives have 30,631 temporary gap episodes; missing-day min/median/p95/max is
1/1/1/30. All four WDC drives have gaps: eight one-day episodes. Large
synchronized Seagate absences occur around April 13–16 (approximately 4,510
candidate rows compared with approximately 19,700 on most days).

INFERENCE: synchronized absences suggest collection/location-level disruption
rather than independent physical failures. The mechanism remains unknown; do
not call a gap powered-off storage, replacement or a failure. Source-date
completeness alone is insufficient for complete observation ascertainment.

VERIFIED FACT: 115 Seagate failed drives have gaps before their first flag (a
return may occur on the flag date). Ordering can be established here without
the full trajectory: the ten post-failure records fill all ten possible dated
post-event days across the two returning failed drives, so no gaps occur after
the first flag. The general pipeline leaves this count unknown if post-event
gaps make that proof unavailable; it does not equate any-gap coexistence with
return-before-failure in that case.
No unfailed candidate exits before June 30 occur in this inspected quarter;
therefore none are within seven days of the end. This does not establish absence
of permanent exits in Q1. Permanence cannot be established by finite follow-up.

VERIFIED FACT: two Seagate serials have ten observations after their first
`failure == 1` date. They are preserved and flagged, not forced to disappear or
turned into extra events. Repeated failure rows are zero. A prospective analytic
policy might treat the first flag as terminal and audit/truncate later records,
but would require an explicit documented decision; this audit does not implement
that final survival dataset. The prior Q1 all-drive check found no post-failure
rows; the Q2 violation does not invalidate or rewrite that Q1 finding.

Q1 model-specific gap/exit accounting and Q4/Q2 linkage are blocked by absent
serial-level inputs. In particular, no events or exits were imputed from marginal
tables. [Backblaze's Q1 report](https://www.backblaze.com/blog/backblaze-drive-stats-for-q1-2026/)
also documents daily ascertainment/day-one limitations and return-related
adjustments; these must be reflected in the final endpoint and sensitivity plan.
