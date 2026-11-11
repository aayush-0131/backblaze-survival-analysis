"""Synthetic checks for bounded exit linkage. Every serial and date is invented."""
from datetime import date
import json
import zipfile

import pandas as pd
import pytest

from backblaze_audit.cohort import SEAGATE
from backblaze_audit.history import digest, write_table
from backblaze_audit.linkage import ExitLinkage, exit_targets, linkage_summary, run_linkage
from backblaze_audit.sources import LocalZipSource

END = date(2026, 3, 31)
L = [date(2026, 4, d) for d in (1, 2, 3)]  # synthetic three-day linkage window
COLS = ["date", "serial_number", "model", "capacity_bytes", "failure"]


def drives():
    def row(serial, inclusion, outcome, last):
        return dict(serial_number=serial, inclusion=inclusion, outcome=outcome, last_observed_date=last,
                    days_unobserved_before_window_end=(END - date.fromisoformat(last)).days)
    return pd.DataFrame([
        row("near_back", "included", "unexplained_exit", "2026-03-30"),
        row("near_gone", "included", "unexplained_exit", "2026-03-28"),
        row("deep_back", "included", "unexplained_exit", "2026-01-09"),
        row("deep_gone", "included", "unexplained_exit", "2026-03-27"),  # 4 days unobserved -> earlier
        row("relabel", "included", "unexplained_exit", "2026-03-29"),
        row("flagged", "included", "unexplained_exit", "2026-03-30"),
        row("censored", "included", "administrative_censoring", "2026-03-31"),
        row("late_exit", "excluded_later_arrival", "unexplained_exit", "2026-03-30"),
    ])


def day(d, rows):
    return pd.DataFrame([[d.isoformat(), *r] for r in rows], columns=COLS)


def scan():
    link = ExitLinkage(exit_targets(drives()), SEAGATE, L[0], L[-1])
    link.ingest(day(L[0], []), L[0])
    link.ingest(day(L[1], [["near_back", SEAGATE, 12, 0], ["relabel", "ST12000NM000", 12, 0],
                           ["deep_back", SEAGATE, 12, 0]]), L[1])
    link.ingest(day(L[2], [["near_back", SEAGATE, 12, 0], ["flagged", SEAGATE, 12, 1]]), L[2])
    return link


def test_targets_are_included_unexplained_exits_with_descriptive_groups():
    t = exit_targets(drives())
    assert set(t) == {"near_back", "near_gone", "deep_back", "deep_gone", "relabel", "flagged"}
    assert {s for s, v in t.items() if v["exit_group"] == "near_end"} == {"near_back", "near_gone", "relabel", "flagged"}
    assert t["deep_gone"]["exit_group"] == "earlier"


def test_reappearance_is_earliest_verified_row_and_absence_is_unresolved():
    r = {x["serial_number"]: x for x in scan().records()}
    assert r["near_back"]["first_reappearance_date"] == L[1]
    assert r["near_back"]["days_absent_before_reappearance"] == 2  # Mar 31, Apr 1
    assert r["near_back"]["days_observed_in_window"] == 2 and r["near_back"]["observed_on_window_end"] is True
    assert r["near_gone"]["linkage_status"] == "not_observed_through_window_end"
    assert r["near_gone"]["first_reappearance_date"] is None
    assert r["relabel"]["model_label_differs"] is True  # found by serial, flagged, not dropped
    assert r["flagged"]["failure_flags_in_window"] == 1  # descriptive only; never a Q1 event


def test_summary_reconciles_by_exit_group_without_serials():
    s = linkage_summary(scan().records())
    assert s["all_exits"]["exits"] == 6
    assert s["all_exits"]["reappeared_verified"] == 4
    assert s["all_exits"]["not_observed_through_window_end"] == 2
    assert s["by_exit_group"]["near_end"] == dict(
        exits=4, reappeared_verified=3, not_observed_through_window_end=1,
        first_reappearance_by_date={"2026-04-02": 2, "2026-04-03": 1},
        reappeared_and_observed_on_window_end=2, reappeared_with_different_model_label=1,
        reappeared_with_failure_flag_in_window=1)
    assert s["by_exit_group"]["earlier"]["reappeared_verified"] == 1
    assert "near_back" not in json.dumps(s)


def test_guards():
    t = exit_targets(drives())
    link = ExitLinkage(t, SEAGATE, L[0], L[-1])
    with pytest.raises(ValueError, match="outside the linkage window"):
        link.ingest(day(date(2026, 4, 9), []), date(2026, 4, 9))
    with pytest.raises(ValueError, match="filename/date"):
        link.ingest(day(L[1], [["near_back", SEAGATE, 12, 0]]), L[0])
    with pytest.raises(ValueError, match="Duplicate target serial"):
        link.ingest(day(L[0], [["near_back", SEAGATE, 12, 0], ["near_back", SEAGATE, 12, 0]]), L[0])
    with pytest.raises(ValueError, match="Non-target"):
        link.ingest(day(L[0], [["censored", SEAGATE, 12, 0]]), L[0])
    link.ingest(day(L[0], []), L[0])
    with pytest.raises(ValueError, match="Duplicate source date"):
        link.ingest(day(L[0], []), L[0])
    with pytest.raises(ValueError, match="Incomplete linkage calendar"):
        link.records()
    with pytest.raises(ValueError, match="start after"):
        ExitLinkage(t, SEAGATE, date(2026, 3, 30), L[-1])


def write_cohort(tmp_path):
    out = tmp_path / "cohort"
    write_table(out / "cohort_drives.csv", drives().to_dict("records"))
    write_table(out / "cohort_accounting.csv", [dict(x=1)])
    (out / "cohort_manifest.json").write_text(json.dumps(dict(
        model=SEAGATE, models_fitted="none",
        output_sha256={n: digest(out / n) for n in ("cohort_drives.csv", "cohort_accounting.csv")})))
    return out


def test_run_linkage_from_zip_reads_only_window_and_checks_calendar(tmp_path):
    cohort = write_cohort(tmp_path)
    archive = tmp_path / "later.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for d, rows in ((L[0], [["other1", SEAGATE, 12, 0], ["near_back", SEAGATE, 12, 0]]),
                        (L[1], [["other1", SEAGATE, 12, 0], ["deep_gone", "WDC X", 22, 0]]),
                        (date(2026, 4, 20), [["near_gone", SEAGATE, 12, 0]])):  # outside window: never read
            z.writestr(f"q/{d}.csv", day(d, rows).to_csv(index=False))
    s = run_linkage(LocalZipSource(archive), cohort, tmp_path / "out", L[0], L[1])
    assert s["all_exits"]["reappeared_verified"] == 2
    assert s["by_exit_group"]["earlier"]["reappeared_with_different_model_label"] == 1
    assert s["by_exit_group"]["near_end"]["not_observed_through_window_end"] == 3  # Apr 20 row ignored
    assert [e["rows"] for e in s["member_evidence"]] == [2, 2]
    assert all(e["decompressed_bytes"] == e["uncompressed_size"] for e in s["member_evidence"])
    assert s["q1_cohort_modified"] is False and s["models_fitted"] == "none"
    assert s["source"] == "later.zip"
    assert "near_back" not in json.dumps(s, default=str)
    assert "near_back" in (tmp_path / "out" / "exit_linkage_drives.csv").read_text()
    with pytest.raises(ValueError, match="Incomplete or overlapping"):
        run_linkage(LocalZipSource(archive), cohort, tmp_path / "out", L[0], L[2])
    (cohort / "cohort_drives.csv").write_text("tampered\n")
    with pytest.raises(ValueError, match="hash differs"):
        run_linkage(LocalZipSource(archive), cohort, tmp_path / "out", L[0], L[1])


def test_corrupted_member_is_refused_by_crc(tmp_path):
    cohort = write_cohort(tmp_path)
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as z:
        z.writestr(f"q/{L[0]}.csv", day(L[0], [["near_back", SEAGATE, 12, 0]]).to_csv(index=False))
    raw = archive.read_bytes()
    archive.write_bytes(raw.replace(b"near_back", b"near_bacK", 1))  # flip one stored byte
    with pytest.raises(zipfile.BadZipFile, match="CRC"):
        run_linkage(LocalZipSource(archive), cohort, tmp_path / "out", L[0], L[0])
