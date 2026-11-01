"""Synthetic fixtures for the per-drive cohort-construction skeleton.

Every serial, date and SMART value below is invented to exercise a rule.
None of these rows are Backblaze data and no count here is a research result.
"""
from datetime import date
import json
import zipfile

import pandas as pd
import pytest

from backblaze_audit.cohort import (
    SEAGATE, CohortAudit, cohort_accounting, drive_records, run_cohort,
)
from backblaze_audit.history import MODELS
from backblaze_audit.sources import LocalZipSource

WDC = MODELS[1]
COLUMNS = ["serial_number", "model", "capacity_bytes", "failure",
           "smart_9_raw", "smart_197_raw", "smart_5_raw"]
D = [date(2026, 1, d) for d in range(1, 7)]  # synthetic six-day window


def frame(day, rows):
    f = pd.DataFrame(rows, columns=COLUMNS)
    f["date"] = day.isoformat()
    return f


def build():
    """Synthetic trajectories, one per rule under test.

    base0   present throughout, SMART 197 zero at baseline but nonzero later
    fail    present at baseline, records failure on day 4
    exit    present at baseline, last seen day 3, no failure flag
    gapfail missing days 2-3, returns day 4, fails day 5
    gapcen  missing day 5 only, present at end
    late    first observed day 2 (later arrival)
    day0    failure flag on baseline date
    miss    SMART 197/5/9 missing at baseline
    post    fails day 2, then two further rows (post-failure records)
    """
    a = CohortAudit(SEAGATE, D[0], D[-1])
    S = SEAGATE
    rows = {
        D[0]: [["base0", S, 12, 0, 1000, 0, 0], ["fail", S, 12, 0, 2000, 3, 8],
               ["exit", S, 12, 0, 3000, 0, 1], ["gapfail", S, 12, 0, 4000, 0, 0],
               ["gapcen", S, 12, 0, 5000, 0, 0], ["day0", S, 12, 1, 6000, 0, 0],
               ["miss", S, 12, 0, None, None, None], ["post", S, 12, 0, 7000, 0, 0],
               ["w1", WDC, 22, 0, 10, 0, 0]],
        D[1]: [["base0", S, 12, 0, 1024, 5, 0], ["fail", S, 12, 0, 2024, 3, 8],
               ["exit", S, 12, 0, 3024, 0, 1], ["gapcen", S, 12, 0, 5024, 0, 0],
               ["late", S, 12, 0, 50, 0, 0], ["miss", S, 12, 0, 9, 0, 0],
               ["post", S, 12, 1, 7024, 0, 0]],
        D[2]: [["base0", S, 12, 0, 1048, 5, 0], ["fail", S, 12, 0, 2048, 3, 8],
               ["exit", S, 12, 0, 3048, 0, 1], ["gapcen", S, 12, 0, 5048, 0, 0],
               ["late", S, 12, 0, 74, 0, 0], ["miss", S, 12, 0, 33, 0, 0],
               ["post", S, 12, 0, 7048, 0, 0]],
        D[3]: [["base0", S, 12, 0, 1072, 5, 0], ["fail", S, 12, 1, 2072, 3, 8],
               ["gapfail", S, 12, 0, 4072, 0, 0], ["gapcen", S, 12, 0, 5072, 0, 0],
               ["late", S, 12, 0, 98, 0, 0], ["miss", S, 12, 0, 57, 0, 0],
               ["post", S, 12, 0, 7072, 0, 0]],
        D[4]: [["base0", S, 12, 0, 1096, 5, 0], ["gapfail", S, 12, 1, 4096, 0, 0],
               ["late", S, 12, 0, 122, 0, 0], ["miss", S, 12, 0, 81, 0, 0]],
        D[5]: [["base0", S, 12, 0, 1120, 5, 0], ["gapcen", S, 12, 0, 5120, 0, 0],
               ["late", S, 12, 0, 146, 0, 0], ["miss", S, 12, 0, 105, 0, 0]],
    }
    for day, r in rows.items():
        a.ingest(frame(day, r), day)
    return a


def by_serial():
    return {r["serial_number"]: r for r in drive_records(build())}


def test_baseline_inclusion_rules():
    r = by_serial()
    assert "w1" not in r  # other candidate model never enters a single-model cohort
    assert r["late"]["inclusion"] == "excluded_later_arrival"
    assert r["late"]["followup_days"] is None
    assert r["day0"]["inclusion"] == "excluded_failure_on_or_before_baseline"
    included = {s for s, x in r.items() if x["inclusion"] == "included"}
    assert included == {"base0", "fail", "exit", "gapfail", "gapcen", "miss", "post"}


def test_baseline_state_uses_baseline_row_only_and_keeps_missing():
    r = by_serial()
    assert r["base0"]["baseline_smart_197_raw_state"] == "zero"  # later nonzero must not leak
    assert r["fail"]["baseline_smart_197_raw_state"] == "nonzero"
    assert r["fail"]["baseline_smart_5_raw_state"] == "nonzero"
    for column in ("smart_197_raw", "smart_5_raw"):
        assert r["miss"][f"baseline_{column}_state"] == "missing"
    assert r["miss"]["baseline_smart_9_raw_powered_hours_counter"] is None
    assert r["fail"]["baseline_smart_9_raw_powered_hours_counter"] == 2000


def test_first_failure_versus_non_failure_exit():
    r = by_serial()
    assert (r["fail"]["outcome"], r["fail"]["outcome_date"], r["fail"]["followup_days"]) == \
        ("recorded_failure", D[3], 3)
    assert (r["base0"]["outcome"], r["base0"]["followup_days"]) == ("administrative_censoring", 5)
    # An unexplained disappearance is never relabelled a failure.
    assert r["exit"]["outcome"] == "unexplained_exit"
    assert r["exit"]["outcome_date"] == D[2]
    assert r["exit"]["days_unobserved_before_window_end"] == 3
    assert r["exit"]["boundary_linkage"] == "not_attempted"
    assert r["exit"]["first_failure_date"] is None


def test_post_failure_rows_flagged_not_converted():
    p = by_serial()["post"]
    assert p["outcome"] == "recorded_failure" and p["outcome_date"] == D[1]
    assert p["post_failure_rows"] == 2
    assert p["repeated_failure_flags"] is False
    assert p["last_observed_date"] == D[3]


def test_observation_gap_flags():
    r = by_serial()
    g = r["gapfail"]
    assert (g["gap_episodes"], g["missing_days_in_gaps"], g["longest_gap_days"]) == (1, 2, 2)
    assert g["gap_before_first_failure"] is True and g["gap_after_first_failure"] is False
    assert g["outcome"] == "recorded_failure"
    c = r["gapcen"]
    assert (c["gap_episodes"], c["missing_days_in_gaps"], c["outcome"]) == (1, 1, "administrative_censoring")
    assert c["gap_before_first_failure"] is None  # undefined without a failure
    assert r["base0"]["gap_episodes"] == 0


def test_accounting_reconciles_by_baseline_strata():
    rows = cohort_accounting(drive_records(build()))
    total = next(x for x in rows if x["stratum"] == "all")
    assert total["drives_observed"] == 9
    assert total["excluded_later_arrival"] == 1
    assert total["excluded_failure_on_or_before_baseline"] == 1
    assert total["included"] == 7
    assert (total["recorded_failure"], total["administrative_censoring"], total["unexplained_exit"]) == (3, 3, 1)
    for column in ("smart_197_raw", "smart_5_raw"):
        strata = [x for x in rows if x["attribute"] == column]
        assert {x["stratum"] for x in strata} == {"zero", "nonzero", "missing"}
        for key in ("included", "recorded_failure", "administrative_censoring", "unexplained_exit"):
            assert sum(x[key] for x in strata) == total[key]
    miss = next(x for x in rows if x["attribute"] == "smart_197_raw" and x["stratum"] == "missing")
    assert miss["included"] == 1


def test_model_guard_and_determinism():
    with pytest.raises(ValueError, match="candidate model"):
        CohortAudit("NOT_A_CANDIDATE", D[0], D[-1])
    assert drive_records(build()) == drive_records(build())


def test_run_cohort_from_zip_checks_calendar_and_writes_ignored_outputs(tmp_path):
    archive = tmp_path / "synthetic.zip"
    with zipfile.ZipFile(archive, "w") as z:
        for day, rows in ((D[0], [["s1", SEAGATE, 12, 0, 1, 0, 0], ["w1", WDC, 22, 0, 1, 0, 0]]),
                          (D[1], [["s1", SEAGATE, 12, 1, 25, 0, 0]])):
            z.writestr(f"data/{day}.csv", frame(day, rows).to_csv(index=False))
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="Incomplete source calendar"):
        run_cohort(LocalZipSource(archive), out, baseline=D[0], end=D[2])
    run_cohort(LocalZipSource(archive), out, baseline=D[0], end=D[1], chunksize=1)
    drives = pd.read_csv(out / "cohort_drives.csv")
    assert list(drives.serial_number) == ["s1"]
    assert drives.outcome.tolist() == ["recorded_failure"]
    manifest = json.loads((out / "cohort_manifest.json").read_text())
    assert manifest["model"] == SEAGATE and len(manifest["member_evidence"]) == 2
    assert all(len(m["sha256"]) == 64 for m in manifest["member_evidence"])
    assert manifest["models_fitted"] == "none"
    good = {m["date"]: m["crc32"] for m in manifest["member_evidence"]}
    run_cohort(LocalZipSource(archive), out, baseline=D[0], end=D[1], expected_crc32=good)
    with pytest.raises(ValueError, match="CRC32"):
        run_cohort(LocalZipSource(archive), out, baseline=D[0], end=D[1],
                   expected_crc32={**good, D[1].isoformat(): "00000000"})


def test_guards_alias_window_and_post_failure_gap():
    a = CohortAudit(SEAGATE, D[0], D[2])
    with pytest.raises(ValueError, match="outside the cohort window"):
        a.ingest(frame(D[3], []), D[3])
    with pytest.raises(ValueError, match="Unapproved model"):
        CohortAudit(WDC, D[0], D[0]).ingest(frame(D[0], [["x", "WUH722222ALE6L4", 22, 0, 1, 0, 0]]), D[0])
    a.ingest(frame(D[0], [["f", SEAGATE, 12, 1, 10, 0, 0]]), D[0])
    a.ingest(frame(D[1], []), D[1])
    a.ingest(frame(D[2], [["f", SEAGATE, 12, 0, 58, 0, 0]]), D[2])
    f = drive_records(a)[0]
    assert f["inclusion"] == "excluded_failure_on_or_before_baseline"
    assert f["gap_after_first_failure"] is True and f["gap_before_first_failure"] is False
    assert f["post_failure_rows"] == 1


def test_incomplete_calendar_blocks_records_and_absent_column_is_missing():
    a = CohortAudit(SEAGATE, D[0], D[1])
    a.ingest(frame(D[0], [["s", SEAGATE, 12, 0, 1, 0, 0]]).drop(columns=["smart_197_raw"]), D[0])
    with pytest.raises(ValueError, match="Incomplete source calendar"):
        drive_records(a)
    a.ingest(frame(D[1], [["s", SEAGATE, 12, 0, 25, 0, 0]]), D[1])
    assert drive_records(a)[0]["baseline_smart_197_raw_state"] == "missing"
