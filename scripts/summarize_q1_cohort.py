#!/usr/bin/env python3
"""Verify ignored run_cohort outputs and write an outcome-blinded aggregate summary. No models fitted.

Refuses outputs whose hashes differ from cohort_manifest.json, or that fail to
reconcile with the recorded Q1 audit (results/tables/model_inventory.csv).
Event counts by baseline 197/5 group are sealed; see backblaze_audit.cohort_summary.

  PYTHONPATH=src python scripts/summarize_q1_cohort.py            # write summary
  PYTHONPATH=src python scripts/summarize_q1_cohort.py --check    # compare with committed summary
"""
import argparse
import csv
import json
import sys
from pathlib import Path

from backblaze_audit.cohort_summary import blinded_summary, load_verified

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--cohort-dir", type=Path, default=root / "data/processed/q1_cohort")
p.add_argument("--inventory", type=Path, default=root / "results/tables/model_inventory.csv")
p.add_argument("--output", type=Path, default=root / "docs/q1_cohort_feasibility_summary.json")
p.add_argument("--check", action="store_true", help="Fail unless the regenerated summary equals --output")
a = p.parse_args()

drives, manifest = load_verified(a.cohort_dir)
row = next(r for r in csv.DictReader(a.inventory.open(encoding="utf-8")) if r["model"] == manifest["model"])
reference = dict(source="results/tables/model_inventory.csv (Q1 2026 data audit)",
                 unique_drives=int(row["unique_drives"]), drive_days=int(row["drive_days"]),
                 failure_rows=int(row["observed_failure_rows"]))
summary = blinded_summary(drives, manifest, reference)
text = json.dumps(summary, indent=2, sort_keys=True) + "\n"
if a.check:
    if a.output.read_text(encoding="utf-8") != text:
        sys.exit(f"FAIL: regenerated summary differs from {a.output}")
    print("PASS: cohort outputs match manifest hashes, reconcile with the Q1 audit, and reproduce the committed summary")
else:
    a.output.write_text(text, encoding="utf-8")
    print(f"wrote {a.output}")
