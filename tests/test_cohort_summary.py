"""Synthetic checks for the outcome-blinded cohort summary.

Fixtures reuse the invented trajectories in test_cohort.py; none are Backblaze data.
"""
import json

import pandas as pd
import pytest

from backblaze_audit.cohort import drive_records
from backblaze_audit.cohort_summary import SEALED_STRATUM_FIELDS, blinded_summary, load_verified
from backblaze_audit.history import digest, write_table

from test_cohort import D, build


def write_outputs(tmp_path):
    write_table(tmp_path / "cohort_drives.csv", drive_records(build()))
    write_table(tmp_path / "cohort_accounting.csv", [dict(x=1)])
    rows = {d.isoformat(): n for d, n in zip(D, (8, 7, 7, 7, 4, 4))}
    manifest = dict(model="ST12000NM0008", baseline=D[0].isoformat(), window_end=D[-1].isoformat(),
                    models_fitted="none", time_scale="calendar", boundary_linkage="not_attempted",
                    crc32_checked_against_recorded_manifest=True,
                    member_evidence=[dict(date=k, candidate_rows=v) for k, v in rows.items()],
                    output_sha256={n: digest(tmp_path / n) for n in ("cohort_drives.csv", "cohort_accounting.csv")})
    (tmp_path / "cohort_manifest.json").write_text(json.dumps(manifest))
    return manifest


def test_summary_reconciles_and_seals_event_counts_by_group(tmp_path):
    write_outputs(tmp_path)
    drives, manifest = load_verified(tmp_path)
    s = blinded_summary(drives, manifest, dict(unique_drives=9, drive_days=37, failure_rows=4))
    assert s["reconciliation_with_recorded_q1_audit"]["matches"] is True
    assert s["inclusion"]["included"] == 7 and s["inclusion"]["excluded_later_arrival"] == 1
    assert s["included_overall"]["recorded_failure"] == 3  # overall only
    assert s["unexplained_exits"]["count"] == 1
    assert s["failure_flags_all_drives"]["post_failure_rows"] == 2
    for column, groups in s["baseline_state_groups"]["by_attribute"].items():
        assert sum(g["included"] for g in groups.values()) == 7
        for g in groups.values():
            assert not set(SEALED_STRATUM_FIELDS) & set(g), "event-derivable field leaked into a stratum"
    assert s["baseline_state_groups"]["by_attribute"]["smart_197_raw"]["missing"]["included"] == 1
    json.dumps(s)  # serialisable


def test_summary_refuses_tampered_or_unreconciled_outputs(tmp_path):
    write_outputs(tmp_path)
    drives, manifest = load_verified(tmp_path)
    with pytest.raises(ValueError, match="failure_rows differs"):
        blinded_summary(drives, manifest, dict(unique_drives=9, drive_days=37, failure_rows=5))
    with pytest.raises(ValueError, match="calendar"):
        blinded_summary(drives, {**manifest, "member_evidence": manifest["member_evidence"][:-1]})
    frame = pd.read_csv(tmp_path / "cohort_drives.csv")
    frame.loc[0, "outcome"] = "recorded_failure"
    frame.to_csv(tmp_path / "cohort_drives.csv", index=False)
    with pytest.raises(ValueError, match="hash differs"):
        load_verified(tmp_path)
