"""Recorded Q1 design decisions that code must apply mechanically. No estimators.

D1 (docs/q1_decisions.json), recorded 2026-11-10: keep SMART 197 as the baseline warning
attribute if its nonzero baseline group has at least ``D1_MIN_EVENTS`` recorded
failures in the Q1 window; otherwise switch to SMART 5. As written, the rule sets
no minimum for SMART 5. The rule and this code were committed before the sealed
per-group counts were read.
"""
from __future__ import annotations

from .cohort import OUTCOMES

D1_MIN_EVENTS = 10
D1_LEAD, D1_ALTERNATIVE = "smart_197_raw", "smart_5_raw"
STATES = ("zero", "nonzero", "missing")


def validated_group_counts(accounting: list[dict]) -> list[dict]:
    """Integer accounting rows; refuse them unless every attribute's strata sum to the totals."""
    rows = [{k: (v if k in ("attribute", "stratum") else int(v)) for k, v in r.items() if v not in ("", None)}
            for r in accounting]
    total = [r for r in rows if r["attribute"] == "all"]
    if len(total) != 1:
        raise ValueError("Accounting must have exactly one overall row")
    total = total[0]
    for attribute in (D1_LEAD, D1_ALTERNATIVE):
        strata = {r["stratum"]: r for r in rows if r["attribute"] == attribute}
        if set(strata) != set(STATES):
            raise ValueError(f"{attribute}: expected strata {STATES}")
        for key in ("included", *OUTCOMES):
            if sum(s[key] for s in strata.values()) != total[key]:
                raise ValueError(f"{attribute}: {key} strata do not sum to the overall total")
        for s in strata.values():
            if sum(s[k] for k in OUTCOMES) != s["included"]:
                raise ValueError(f"{attribute}/{s['stratum']}: outcomes do not sum to included")
    return rows


def apply_d1(accounting: list[dict], min_events: int = D1_MIN_EVENTS) -> dict:
    """Apply the recorded D1 rule to validated accounting rows. Returns the choice and its basis."""
    rows = validated_group_counts(accounting)
    lead = next(r for r in rows if r["attribute"] == D1_LEAD and r["stratum"] == "nonzero")
    events = lead["recorded_failure"]
    keep = events >= min_events
    return dict(
        rule=(f"Keep {D1_LEAD} if its nonzero baseline group has >= {min_events} recorded failures "
              f"in the Q1 window; otherwise switch to {D1_ALTERNATIVE}. No minimum is set for {D1_ALTERNATIVE}."),
        min_events=min_events, lead_attribute=D1_LEAD, alternative_attribute=D1_ALTERNATIVE,
        lead_nonzero_included=lead["included"], lead_nonzero_recorded_failures=events,
        lead_meets_rule=keep, chosen_attribute=D1_LEAD if keep else D1_ALTERNATIVE)
