from datetime import date
import pandas as pd
import pytest

from backblaze_audit.history import HistoryAudit, MODELS, pair_flags, quantile
from collections import Counter
from pathlib import Path
import json
import zipfile
from backblaze_audit.history import run_history, digest

A,B=MODELS

def frame(day, rows, missing=()):
    columns=["serial_number","model","capacity_bytes","failure","smart_9_raw","smart_197_raw","smart_5_raw"]
    f=pd.DataFrame(rows,columns=columns)
    f["date"]=day
    return f.drop(columns=list(missing))

def fixture():
    audit=HistoryAudit(date(2026,1,1),date(2026,1,4))
    audit.ingest(frame("2026-01-01",[
        ["a",A,100,0,100,0,1], ["b",A,100,0,None,None,0],
        ["c",A,100,1,10,3,0], ["w",B,200,0,0,0,0],
    ]),date(2026,1,1))
    audit.ingest(frame("2026-01-02",[
        ["a",A,100,0,124,1,1], ["new",A,100,0,5,0,0],
        ["w",B,200,0,24,0,0],
    ]),date(2026,1,2))
    audit.ingest(frame("2026-01-03",[["w",B,200,0,48,0,0]]),date(2026,1,3))
    audit.ingest(frame("2026-01-04",[
        ["a",A,100,1,172,2,1], ["b",A,100,0,10,0,0],
        ["new",A,100,0,53,0,0], ["w",B,200,0,72,0,0],
    ]),date(2026,1,4))
    return audit

def test_temporal_anomalies_and_units():
    assert pair_flags(100,124,1)["calendar_like"]
    assert pair_flags(100,148,2)["gap_class"]=="calendar_like"
    assert pair_flags(100,100,3)["gap_class"]=="unchanged"
    assert pair_flags(100,101,3)["gap_class"]=="partial_powered_time"
    assert pair_flags(100,0,1)["reset_candidate"]
    assert not pair_flags(10,0,1)["reset_candidate"]
    assert pair_flags(100,173,1)["excess_48h"]
    with pytest.raises(ValueError): pair_flags(1,2,0)

def test_baseline_states_do_not_leak_future_warning():
    audit=fixture()
    rows=audit.tables()["smart_warning_feasibility.csv"]
    r=next(r for r in rows if r["model"]==A and r["column"]=="smart_197_raw" and r["baseline_definition"]=="fixed_snapshot")
    assert r["zero_baseline_drives"]==1
    assert r["zero_subsequent_failure_drives"]==1
    assert r["nonzero_subsequent_failure_drives"]==0
    assert r["missing_baseline_drives"]==1
    assert r["excluded_failure_at_or_before_baseline"]==1
    assert r["adjacent_state_changes"]==1

def test_accounting_events_and_first_dates_reconcile():
    audit=fixture()
    tables=audit.tables()
    inv=next(r for r in tables["historical_model_inventory.csv"] if r["model"]==A)
    assert inv["failure_rows"]==inv["unique_failed_drives"]==2
    assert inv["unique_drives"]==4
    assert inv["q1_linked_drives"]==4
    assert audit.drives["new"]["first"]==date(2026,1,2)
    for r in tables["cohort_accounting.csv"]:
        assert r["retained"]+r["excluded_by_rule"]+r["excluded_failure_at_or_before_baseline"]==r["drives_present"]
        assert r["retained"]==sum(r[k] for k in ("subsequent_recorded_failures","administrative_survivors","unexplained_exits_within_observed_window"))
    gap=next(r for r in tables["gap_exit_audit.csv"] if r["model"]==A)
    assert gap["intermittent_gap_drives"]==3
    assert gap["failed_drives_with_any_gap"]==1
    assert gap["failures_after_return"]==1

def test_duplicate_dates_and_serials_are_rejected():
    audit=fixture()
    with pytest.raises(ValueError,match="Duplicate source date"):
        audit.ingest(frame("2026-01-04",[]),date(2026,1,4))
    audit=HistoryAudit(date(2026,1,1),date(2026,1,1))
    with pytest.raises(ValueError,match="Duplicate or unordered"):
        audit.ingest(frame("2026-01-01",[["a",A,100,0,1,0,0]]*2),date(2026,1,1))

def test_missing_columns_aliases_and_post_failure_are_visible():
    audit=HistoryAudit(date(2026,1,1),date(2026,1,2))
    audit.ingest(frame("2026-01-01",[["a",A,100,1,1,0,0]],missing=("smart_9_raw",)),date(2026,1,1))
    audit.ingest(frame("2026-01-02",[["a",A,100,0,1,0,0]]),date(2026,1,2))
    assert audit.counts[A]["smart_9_raw_missing"]==1
    assert audit.counts[A]["post_failure_rows"]==1
    assert audit.counts[A]["smart_9_raw_missing_pairs"]==1
    alias="WUH722222ALE6L4"
    with pytest.raises(ValueError,match="Unapproved model"):
        HistoryAudit(date(2026,1,1),date(2026,1,1)).ingest(frame("2026-01-01",[["w",alias,200,0,1,0,0]]),date(2026,1,1))
    mapped=HistoryAudit(date(2026,1,1),date(2026,1,1),aliases={alias:B})
    mapped.ingest(frame("2026-01-01",[["w",alias,200,0,1,0,0]]),date(2026,1,1))
    assert mapped.drives["w"]["model"]==B
    assert alias in mapped.raw_labels

def test_deterministic_aggregation_and_exact_quantiles():
    assert fixture().tables()==fixture().tables()
    assert quantile(Counter({0:4,24:6}),.5)==24
    assert quantile(Counter(),.5) is None

def test_invalid_binary_failure_and_date_are_rejected():
    for bad_failure in (2,None):
        with pytest.raises(ValueError):
            HistoryAudit(date(2026,1,1),date(2026,1,1)).ingest(frame("2026-01-01",[["a",A,100,bad_failure,1,0,0]]),date(2026,1,1))
    with pytest.raises(ValueError,match="filename/date"):
        HistoryAudit(date(2026,1,1),date(2026,1,1)).ingest(frame("2026-01-02",[["a",A,100,0,1,0,0]]),date(2026,1,1))

def test_zip_provenance_checkpoint_and_table_reproduction(tmp_path):
    archive=tmp_path/"fixture.zip"
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
        for day,age,failure in (("2026-01-01",100,0),("2026-01-02",124,1)):
            z.writestr(day+".csv",frame(day,[["a",A,100,failure,age,0,1]]).to_csv(index=False))
    provenance={"local_sha256":digest(archive),"local_sha1":digest(archive,"sha1"),"content_length_bytes":archive.stat().st_size}
    checkpoint=tmp_path/"local.pkl"
    arguments=([archive],tmp_path,date(2026,1,1),date(2026,1,2))
    first=run_history(*arguments,chunksize=1,provenance=provenance,checkpoint=checkpoint)
    manifest_path=tmp_path/"results/audit/history_manifest.json"
    before=manifest_path.read_bytes()
    second=run_history(*arguments,chunksize=1,provenance=provenance,checkpoint=checkpoint)
    assert first.tables()==second.tables()
    assert manifest_path.read_bytes()==before
    manifest=json.loads(before)
    assert len(manifest["member_evidence"])==2
    assert all(len(m["sha256"])==64 for m in manifest["member_evidence"])
    assert manifest["private_output_hashes"]["history_drive_summary.csv"]==digest(tmp_path/"data/processed/history_drive_summary.csv")
    with pytest.raises(ValueError,match="provenance"):
        run_history(*arguments,provenance={"local_sha256":"wrong"})

def test_source_calendar_overlap_and_missing_capacity(tmp_path):
    archive=tmp_path/"gap.zip"
    with zipfile.ZipFile(archive,"w") as z:
        for day in ("2026-01-01","2026-01-03"):
            z.writestr(day+".csv",frame(day,[["a",A,None,0,None,None,0]]).to_csv(index=False))
    with pytest.raises(ValueError,match="Incomplete source calendar"):
        run_history([archive],tmp_path,date(2026,1,1),date(2026,1,3))
    with pytest.raises(ValueError,match="Overlapping"):
        run_history([archive,archive],tmp_path,date(2026,1,1),date(2026,1,3))
    audit=HistoryAudit(date(2026,1,1),date(2026,1,1))
    audit.ingest(frame("2026-01-01",[["a",A,None,0,None,None,0]]),date(2026,1,1))
    assert audit.counts[A]["invalid_capacity_rows"]==1
    complete=[r for r in audit.tables()["cohort_accounting.csv"] if r["model"]==A and r["rule"]=="complete_warning"]
    assert all(r["retained"]==0 for r in complete)

def test_post_failure_gap_does_not_claim_return_preceded_failure():
    audit=HistoryAudit(date(2026,1,1),date(2026,1,3))
    audit.ingest(frame("2026-01-01",[["a",A,100,1,100,0,0]]),date(2026,1,1))
    audit.ingest(frame("2026-01-02",[]),date(2026,1,2))
    audit.ingest(frame("2026-01-03",[["a",A,100,0,148,0,0]]),date(2026,1,3))
    gap=next(r for r in audit.tables()["gap_exit_audit.csv"] if r["model"]==A)
    assert gap["failed_drives_with_any_gap"]==1
    assert gap["failures_after_return"] is None
    assert not gap["failures_after_return_order_verified"]
