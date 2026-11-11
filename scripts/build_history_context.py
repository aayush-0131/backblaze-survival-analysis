#!/usr/bin/env python3
"""Reuse authoritative Q1 aggregates; unavailable longitudinal cells stay blank."""
from pathlib import Path
import csv
import json
import sys
import pandas as pd
import numpy as np

from backblaze_audit.history import MODELS, digest, write_table

root=Path(__file__).resolve().parents[1]
tables=root/"results/tables"
read=lambda name:list(csv.DictReader((tables/name).open()))
scope="q1_2026_verified_aggregate_only"
models={r["model"]:r for r in read("model_inventory.csv") if r["model"] in MODELS}
coverage={(r["model"],r["column"]):r for r in read("smart_coverage_by_model.csv") if r["model"] in MODELS}
inventory=[r for r in read("historical_model_inventory.csv") if r["evidence_scope"]!=scope]
warning=[r for r in read("smart_warning_feasibility.csv") if r["evidence_scope"]!=scope]
smart9=[r for r in read("smart9_consistency.csv") if r["evidence_scope"]!=scope]
accounting=[r for r in read("cohort_accounting.csv") if r["evidence_scope"]!=scope]
gaps=[r for r in read("gap_exit_audit.csv") if r["evidence_scope"]!=scope]
for model in MODELS:
    m=models[model]
    inventory.append(dict(model=model,evidence_scope=scope,unique_drives=int(m["unique_drives"]),
        drive_days=int(m["drive_days"]),failure_rows=int(m["observed_failure_rows"]),
        unique_failed_drives=int(m["unique_failed_drives"]),earliest_observed_backblaze_date=m["first_date_observed"],
        latest_observed_date=m["last_date_observed"],historical_census_complete=False,q1_linkage_complete=False,
        published_q1_lifetime_failure_rows=2466 if model==MODELS[0] else 360,
        published_q1_lifetime_drive_days=43012820 if model==MODELS[0] else 22472050,
        lifetime_counts_source="Official Q1 report; reporting subset, not independently reproduced"))
    accounting.append(dict(model=model,evidence_scope=scope,baseline="2026-01-01 (proposed)",
        column="smart_197_raw / smart_5_raw",rule="UNAVAILABLE_without_Q1_rows",
        notes="All Q1 unique drives are not the Jan1 risk set; baseline, exclusions, outcomes and gaps unavailable."))
    gaps.append(dict(model=model,evidence_scope=scope,permanence_verified=False,
        q1_boundary_linkage_verified=False,notes="Model-specific Q1 gaps, exits and returns require serial-level rows."))
    for column in ("smart_9_raw","smart_197_raw","smart_5_raw"):
        c=coverage[model,column]
        n,total=int(c["non_null_count"]),int(c["drive_days"])
        zeros=round(n*float(c["zero_fraction_of_reported"]))
        if column=="smart_9_raw":
            smart9.append(dict(model=model,evidence_scope=scope,drive_days=total,reported=n,
                missing=total-n,coverage=c["reporting_fraction"],zero_count=zeros,
                zero_fraction=c["zero_fraction_of_reported"]))
        else:
            warning.append(dict(model=model,evidence_scope=scope,column=column,
                baseline_definition="UNAVAILABLE_without_Q1_rows",baseline_date="2026-01-01 (proposed)",
                drive_days=total,reported=n,missing=total-n,coverage=c["reporting_fraction"],
                zero_rows=zeros,nonzero_rows=n-zeros,nonzero_fraction=(n-zeros)/n,
                notes="Row-level prevalence only. Baseline drives, transitions and failures by state are not recoverable from aggregate tables."))
for name,rows in (("historical_model_inventory.csv",inventory),("smart_warning_feasibility.csv",warning),("smart9_consistency.csv",smart9),("cohort_accounting.csv",accounting),("gap_exit_audit.csv",gaps)):
    write_table(tables/name,rows)
comparison=[
    dict(time_scale="Calendar follow-up from fixed baseline",observed_quantity="Days since fixed baseline snapshot",assumptions="Independent censoring conditional on design; gaps policy needed",censoring="Recorded failure; administrative end; unexplained exit kept distinct",prevalent_cohort="Conditional on survival and observation at baseline",implementation="Low",threat="Informative exits; daily outcome ascertainment",recommendation="Preferred primary scale after Q1 baseline audit",verdict="READY WITH CONDITIONS"),
    dict(time_scale="Time since earliest Backblaze observation",observed_quantity="Earliest date in inspected archives",assumptions="Complete history needed for dataset-first appearance; installation remains unknown",censoring="Unobserved prior lifetime; source-window truncation",prevalent_cohort="Do not assign birth at first observed date",implementation="High",threat="History incomplete; survivor selection if restricted to Q1 survivors",recommendation="Descriptive only at current checkpoint",verdict="BLOCKED"),
    dict(time_scale="SMART 9 powered age",observed_quantity="Raw counter at snapshots",assumptions="Hours interpretation and counter continuity; powered time differs from elapsed life",censoring="Event age measured at daily resolution; gaps complicate intervals",prevalent_cohort="Pre-entry age cannot be treated as observed risk time",implementation="Medium",threat="Counter anomalies; vendor/firmware; missing telemetry",recommendation="Nominal hours supported by Q2 endpoints; Q1 age use unvalidated",verdict="REVISE"),
    dict(time_scale="Delayed entry on SMART 9 age",observed_quantity="Counter at entry and exit",assumptions="Valid common powered-age scale; independent truncation and censoring",censoring="Enter risk set at observed powered age; do not backfill pre-entry exposure",prevalent_cohort="Explicit delayed entry needed",implementation="High",threat="Age-dependent selection; gaps; nonmonotone counters; different deployment eras",recommendation="Defer until longitudinal age integrity and assumptions resolved",verdict="BLOCKED"),
]
write_table(tables/"time_origin_comparison.csv",comparison)
windows=[]
for model in MODELS:
    m=models[model]
    for window,status,reason,burden in (
        ("Q1 only","BLOCKED","Aggregate coverage available; Jan1 warning/event-by-state/gap counts unresolved","90 daily members; existing ZIP 1.313 GB compressed"),
        ("Q1 + last 14 Q4 days","BLOCKED","Supports prespecified prior-state sensitivity; serial linkage missing","104 daily members; Q4 ZIP approximately 1.2 GB but selective range access preferred"),
        ("Q1 + last 14 Q4 days + first 14 Q2 days","BLOCKED","Preferred bounded acquisition plan; boundary return counts unknown","118 daily members; Q2 ZIP approximately 2.1 GB but only 14 members needed"),
        ("Longer historical follow-up","REVISE","Full unique-drive/event census not measured; no demonstrated need to enlarge analysis window","Several quarterly archives; sequential scans; no bulk extraction"),
    ):
        windows.append(dict(model=model,window=window,q1_unique_drives=m["unique_drives"],
            q1_failures=m["observed_failure_rows"],additional_drives=None,additional_events=None,
            verdict=status,rationale=reason,compute_storage=burden))
write_table(tables/"analysis_window_comparison.csv",windows)
path=root/"results/audit/history_manifest.json"
manifest=json.loads(path.read_text())
manifest["gate_verdict"]="BLOCKED"
manifest["gate_scope"]="Q1 2026 baseline SMART 197/5 and age design; bounded historical stage completed"
manifest["access_date"]="2026-10-06"
manifest["runtime"]={"python":sys.version.split()[0],"pandas":pd.__version__,"numpy":np.__version__}
manifest["q1_aggregate_inputs"]={name:digest(tables/name) for name in ("model_inventory.csv","smart_coverage_by_model.csv")}
manifest["prior_q1_manifest_sha256"]=digest(root/"results/audit/data_manifest.json")
manifest["q1_source_metadata_sha256"]=digest(root/"docs/source_q1_2026.json")
manifest["output_hashes"].update({name:digest(tables/name) for name in (
    "historical_model_inventory.csv","smart_warning_feasibility.csv","smart9_consistency.csv",
    "time_origin_comparison.csv","analysis_window_comparison.csv","cohort_accounting.csv","gap_exit_audit.csv")})
manifest["pending_evidence"]=["Earliest Seagate cohort appearance across all prior archives", "Q1 serial history linkage", "Q1 baseline event counts by warning state", "Q1 SMART9 consistency", "Q4 lookback", "Q2 boundary returns", "Independent reproduction of lifetime event inventory"]
path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
print("PASS: Q1 aggregate evidence reused; unavailable baseline/longitudinal cells left blank")
