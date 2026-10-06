#!/usr/bin/env python3
"""Reconcile only measured scopes; reject invented Q1 baseline cells."""
from pathlib import Path
import csv
import json
import argparse
import zipfile

from backblaze_audit.history import digest

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument("--verify-archive",action="store_true",help="Also rehash ZIP and CRC-check every member; reads approximately 8 GB expanded sequentially")
args=parser.parse_args()
manifest=json.loads((root/"results/audit/history_manifest.json").read_text())
read=lambda name:list(csv.DictReader((root/"results/tables"/name).open()))
for name,expected in manifest["output_hashes"].items():
    assert digest(root/"results/tables"/name)==expected, name
for name,expected in manifest.get("q1_aggregate_inputs",{}).items():
    assert digest(root/"results/tables"/name)==expected,name
measured=[r for r in read("historical_model_inventory.csv") if r["evidence_scope"]=="observed_daily_files_only"]
for r in measured:
    assert int(r["failure_rows"])==int(r["unique_failed_drives"])
    assert int(r["repeated_failure_drives"])==0
    # An observed violation is a reported data-quality finding, not a failed
    # calculation. Never discard these observations to make an assertion pass.
    if int(r["post_failure_rows"]):
        print("FLAG: post-failure observations:",r["model"],r["post_failure_rows"],"rows")
assert manifest["missing_dates"]==[]
assert len({r["date"] for r in manifest["member_evidence"]})==manifest["days_processed"]
assert len({tuple(r["header"]) for r in manifest["member_evidence"]})==1, "Schema changed within inspected quarter"
for r in read("smart9_consistency.csv"):
    assert int(r["reported"])+int(r["missing"])==int(r["drive_days"])
    if r["evidence_scope"]=="observed_daily_files_only":
        assert sum(int(r[k]) for k in ("increases","unchanged","decreases"))==int(r["pairs"])
        assert sum(int(r["gap_"+k]) for k in ("calendar_like","unchanged","partial_powered_time","decrease","excess_or_ambiguous"))==int(r["gap_smart9_pairs"])
for r in read("smart_warning_feasibility.csv"):
    assert int(r["zero_rows"])+int(r["nonzero_rows"])==int(r["reported"])
    assert int(r["reported"])+int(r["missing"])==int(r["drive_days"])
    if r["evidence_scope"]=="q1_2026_verified_aggregate_only":
        assert not r["zero_subsequent_failure_drives"]
        assert not r["nonzero_subsequent_failure_drives"]
    else:
        assert sum(int(r[s+"_baseline_drives"]) for s in ("zero","nonzero","missing"))+int(r["excluded_failure_at_or_before_baseline"])==int(r["baseline_drives"])
        for state in ("zero","nonzero","missing"):
            assert int(r[state+"_subsequent_failure_drives"])<=int(r[state+"_baseline_drives"])
for r in read("cohort_accounting.csv"):
    if r["evidence_scope"]=="q1_2026_verified_aggregate_only":
        assert not r["retained"]
        assert not r["subsequent_recorded_failures"]
        continue
    assert int(r["drives_present"])==sum(int(r[k]) for k in ("excluded_failure_at_or_before_baseline","excluded_by_rule","retained"))
    assert int(r["retained"])==sum(int(r[k]) for k in ("subsequent_recorded_failures","administrative_survivors","unexplained_exits_within_observed_window"))
for r in read("gap_exit_audit.csv"):
    if r["evidence_scope"]=="observed_daily_files_only":
        if r["failures_after_return_order_verified"]=="True":
            assert r["failures_after_return"]==r["failed_drives_with_any_gap"]
        else:
            assert not r["failures_after_return"]
assert set(manifest["aliases"].values())=={"ST12000NM0008","WDC WUH722222ALE6L4"}
source=manifest["source_archives"][0]
assert source["sha256"]==manifest["provenance"]["local_sha256"]
assert source["bytes"]==manifest["provenance"]["content_length_bytes"]
if args.verify_archive:
    archive=root/"data/raw"/source["path"]
    assert digest(archive)==source["sha256"]
    assert digest(archive,"sha1")==source["sha1"]
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None, "ZIP member CRC failure"
    print("PASS: archive SHA256/SHA1 and every ZIP member CRC")
private=root/"data/processed/history_drive_summary.csv"
if private.exists():
    rows=list(csv.DictReader(private.open()))
    assert len({r["serial_number"] for r in rows})==len(rows)
    for m in measured:
        ds=[r for r in rows if r["model"]==m["model"]]
        assert len(ds)==int(m["unique_drives"])
        assert sum(int(r["observed_drive_days"]) for r in ds)==int(m["drive_days"])
        assert sum(bool(r["failure_date"]) for r in ds)==int(m["unique_failed_drives"])
        assert min(r["earliest_observed_backblaze_date"] for r in ds)==m["earliest_observed_backblaze_date"]
        assert max(r["latest_observed_date"] for r in ds)==m["latest_observed_date"]
print("PASS: history hashes, calendar/key enforcement, events, SMART states, accounting and scope checks")
