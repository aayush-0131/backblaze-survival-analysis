#!/usr/bin/env python3
"""Unseal the Q1 per-group accounting and apply the recorded D1 rule. No models fitted.

Refuses to run unless:
  * the builder outputs match their recorded hashes;
  * docs/q1_decisions.json is tracked, unmodified relative to HEAD, and records
    the same D1 threshold as backblaze_audit.decisions (i.e. the rule was
    committed before this script reads the sealed counts).

Writes descriptive counts only: docs/q1_group_counts.json.

  PYTHONPATH=src python scripts/unseal_q1_group_counts.py           # write
  PYTHONPATH=src python scripts/unseal_q1_group_counts.py --check   # compare
"""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

from backblaze_audit.cohort_summary import load_verified
from backblaze_audit.decisions import D1_MIN_EVENTS, apply_d1, validated_group_counts

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--cohort-dir", type=Path, default=root / "data/processed/q1_cohort")
p.add_argument("--decisions", type=Path, default=root / "docs/q1_decisions.json")
p.add_argument("--output", type=Path, default=root / "docs/q1_group_counts.json")
p.add_argument("--check", action="store_true")
a = p.parse_args()

rel = str(a.decisions.resolve().relative_to(root))
git = lambda *args: subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
if git("ls-files", "--error-unmatch", rel).returncode or git("diff", "--quiet", "HEAD", "--", rel).returncode:
    sys.exit(f"Refusing: {rel} must be committed and unmodified before the sealed counts are read")
decisions = json.loads(a.decisions.read_text(encoding="utf-8"))
if decisions["D1"]["min_events"] != D1_MIN_EVENTS:
    sys.exit("Refusing: D1 threshold in code differs from the recorded decision")
recorded_in = git("log", "-1", "--format=%H %cI", "--", rel).stdout.split()

_, manifest = load_verified(a.cohort_dir)  # hash check of both builder outputs
accounting = list(csv.DictReader((a.cohort_dir / "cohort_accounting.csv").open(encoding="utf-8")))
result = dict(
    status="descriptive counts only; no model fitted; gate D9 not signed",
    decision_record=dict(file=rel, commit=recorded_in[0], committed_at=recorded_in[1]),
    cohort_accounting_sha256=manifest["output_sha256"]["cohort_accounting.csv"],
    d1=apply_d1(accounting),
    accounting=validated_group_counts(accounting))
text = json.dumps(result, indent=2, sort_keys=True) + "\n"
if a.check:
    stored = json.loads(a.output.read_text(encoding="utf-8"))
    stored["decision_record"] = result["decision_record"]  # later commits may touch the file's history
    if json.dumps(stored, indent=2, sort_keys=True) + "\n" != text:
        sys.exit(f"FAIL: regenerated counts differ from {a.output}")
    print("PASS: sealed accounting matches its hash and reproduces the committed group counts and D1 choice")
else:
    a.output.write_text(text, encoding="utf-8")
    print(f"wrote {a.output}")
