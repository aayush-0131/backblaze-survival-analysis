"""Outcome-blinded verification summary of ``run_cohort`` outputs. No estimators.

``docs/q1_minimal_path.md`` (section 2, step 3) requires the minimum
event-support rule for choosing between SMART 197 and SMART 5 to be agreed
*before* anyone reads recorded events by baseline group. This module therefore
reports:

* overall cohort accounting, calendar and provenance checks;
* baseline-state group *sizes* (outcome-blind);
* per-stratum non-event burden (unexplained exits, gap drives);

and seals every per-stratum quantity from which an event count by group could
be read or derived (recorded failures, administrative censoring, follow-up,
post-failure rows, gap-before-failure). Those values stay only in the
Git-ignored ``cohort_accounting.csv`` / ``cohort_drives.csv`` until the group
records its rule.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import json

import pandas as pd

from .cohort import INCLUSIONS, OUTCOMES, WARNING_COLUMNS
from .history import digest

STATES = ("zero", "nonzero", "missing")
SEALED_STRATUM_FIELDS = ("recorded_failure", "administrative_censoring", "followup_days",
                         "post_failure_row_drives", "gap_before_first_failure")
OPEN_STRATUM_FIELDS = ("included", "unexplained_exit", "intermittent_gap_drives", "missing_days_in_gaps")


def _check(condition: bool, message: str):
    if not condition:
        raise ValueError("Cohort output verification failed: " + message)


def _truthy(series: pd.Series) -> pd.Series:
    return series.map(lambda v: str(v) == "True")


def load_verified(cohort_dir: Path) -> tuple[pd.DataFrame, dict]:
    """Read builder outputs and refuse them unless their hashes match the builder manifest."""
    cohort_dir = Path(cohort_dir)
    manifest = json.loads((cohort_dir / "cohort_manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["output_sha256"].items():
        _check(digest(cohort_dir / name) == expected, f"{name} hash differs from cohort_manifest.json")
    _check(manifest.get("models_fitted") == "none", "manifest does not record models_fitted == none")
    drives = pd.read_csv(cohort_dir / "cohort_drives.csv", dtype={"serial_number": "string"},
                         keep_default_na=True)
    return drives, manifest


def blinded_summary(drives: pd.DataFrame, manifest: dict, reference: dict | None = None) -> dict:
    """Aggregate, stratum-outcome-blinded summary. Raises if anything fails to reconcile."""
    baseline, end = date.fromisoformat(manifest["baseline"]), date.fromisoformat(manifest["window_end"])
    expected = [(baseline + timedelta(days=i)).isoformat() for i in range((end - baseline).days + 1)]
    evidence = manifest["member_evidence"]
    _check([e["date"] for e in evidence] == expected, "member calendar is not complete and contiguous")
    _check(drives["serial_number"].is_unique, "duplicate serial records")
    _check(set(drives["model"]) <= {manifest["model"]}, "record from another model")
    candidate_rows = sum(int(e["candidate_rows"]) for e in evidence)
    _check(int(drives["observed_drive_days"].sum()) == candidate_rows, "drive-days differ from member rows")
    failed = drives["first_failure_date"].notna()

    inclusion = {k: int((drives["inclusion"] == k).sum()) for k in INCLUSIONS}
    _check(sum(inclusion.values()) == len(drives), "inclusion classes do not sum to observed drives")
    inc = drives[drives["inclusion"] == "included"]
    outcomes = {k: int((inc["outcome"] == k).sum()) for k in OUTCOMES}
    _check(sum(outcomes.values()) == len(inc), "outcomes do not sum to included drives")
    _check(bool((inc["first_observed_date"] == baseline.isoformat()).all()), "included drive absent at baseline")

    reconciliation = None
    if reference is not None:
        # Failure rows equal failed drives only when no drive repeats a flag, so require that first.
        _check(int(_truthy(drives["repeated_failure_flags"]).sum()) == 0,
               "repeated failure flags present; failure rows cannot be read from drive records")
        observed = dict(unique_drives=len(drives), drive_days=candidate_rows, failure_rows=int(failed.sum()))
        for key, value in observed.items():
            _check(value == int(reference[key]), f"{key} differs from recorded Q1 audit")
        reconciliation = dict(reference=reference, observed=observed, matches=True)

    exits = inc[inc["outcome"] == "unexplained_exit"]
    gaps = inc[inc["gap_episodes"] > 0]
    inc_failed = inc[inc["outcome"] == "recorded_failure"]
    states = {}
    for column in WARNING_COLUMNS:
        key = f"baseline_{column}_state"
        groups = {}
        for state in STATES:
            g = inc[inc[key] == state]
            groups[state] = dict(included=len(g), unexplained_exit=int((g["outcome"] == "unexplained_exit").sum()),
                                 intermittent_gap_drives=int((g["gap_episodes"] > 0).sum()),
                                 missing_days_in_gaps=int(g["missing_days_in_gaps"].sum()))
        _check(sum(v["included"] for v in groups.values()) == len(inc), f"{column} states do not sum")
        states[column] = groups
    cross = pd.crosstab(inc["baseline_smart_197_raw_state"], inc["baseline_smart_5_raw_state"])
    summary = dict(
        model=manifest["model"], baseline=manifest["baseline"], window_end=manifest["window_end"],
        models_fitted="none", time_scale=manifest["time_scale"], boundary_linkage=manifest["boundary_linkage"],
        builder_output_sha256=manifest["output_sha256"],
        calendar=dict(daily_members=len(evidence), first=expected[0], last=expected[-1], contiguous=True,
                      crc32_checked_against_recorded_manifest=manifest["crc32_checked_against_recorded_manifest"],
                      candidate_rows_min_per_day=min(int(e["candidate_rows"]) for e in evidence),
                      candidate_rows_max_per_day=max(int(e["candidate_rows"]) for e in evidence)),
        reconciliation_with_recorded_q1_audit=reconciliation,
        inclusion=dict(drives_observed=len(drives), **inclusion,
                       later_arrival_first_observed_by_month=_month_counts(
                           drives.loc[drives["inclusion"] == "excluded_later_arrival", "first_observed_date"])),
        failure_flags_all_drives=dict(
            drives_with_failure_flag=int(failed.sum()),
            by_inclusion={k: int((failed & (drives["inclusion"] == k)).sum()) for k in INCLUSIONS},
            repeated_failure_flag_drives=int(_truthy(drives["repeated_failure_flags"]).sum()),
            post_failure_rows=int(drives["post_failure_rows"].sum())),
        included_overall=dict(
            included=len(inc), **outcomes, included_drive_days=int(inc["observed_drive_days"].sum()),
            recorded_failure_by_month=_month_counts(inc_failed["outcome_date"]),
            recorded_failures_with_gap_before_first_failure=int(_truthy(inc_failed["gap_before_first_failure"]).sum()),
            recorded_failures_with_gap_after_first_failure=int(_truthy(inc_failed["gap_after_first_failure"]).sum())),
        unexplained_exits=dict(
            count=len(exits), last_observed_by_date=_date_counts(exits["last_observed_date"]),
            days_unobserved_before_window_end=_date_counts(exits["days_unobserved_before_window_end"]),
            with_any_gap_episode=int((exits["gap_episodes"] > 0).sum())),
        observation_gaps_included=dict(
            drives_with_gap=len(gaps), gap_episodes=int(inc["gap_episodes"].sum()),
            missing_days_in_gaps=int(inc["missing_days_in_gaps"].sum()),
            episodes_per_drive=_date_counts(inc["gap_episodes"]),
            longest_gap_days_among_gap_drives=_date_counts(gaps["longest_gap_days"])),
        baseline_descriptors_included=dict(
            smart_9_raw_missing=int(inc["baseline_smart_9_raw_powered_hours_counter"].isna().sum()),
            smart9_review_flag_drives=int(_truthy(inc["smart9_review_flag_in_window"]).sum()),
            invalid_baseline_capacity=int((~_truthy(inc["baseline_capacity_valid"])).sum()),
            distinct_baseline_capacity_bytes=sorted(int(c) for c in inc["baseline_capacity_bytes"].dropna().unique())),
        baseline_state_groups=dict(
            open_fields=list(OPEN_STRATUM_FIELDS), sealed_fields=list(SEALED_STRATUM_FIELDS),
            sealed_reason=("Event counts by baseline group are withheld until the group records a minimum "
                           "event-support rule (docs/q1_minimal_path.md section 2, step 3). They exist only in "
                           "the Git-ignored data/processed/q1_cohort/cohort_accounting.csv."),
            by_attribute=states,
            smart_197_by_smart_5_included={r: {c: int(cross.loc[r, c]) for c in cross.columns} for r in cross.index}),
    )
    return summary


def _date_counts(series: pd.Series) -> dict:
    return {str(k): int(v) for k, v in sorted(series.value_counts().items(), key=lambda kv: kv[0])}


def _month_counts(series: pd.Series) -> dict:
    return _date_counts(series.astype(str).str[:7])
