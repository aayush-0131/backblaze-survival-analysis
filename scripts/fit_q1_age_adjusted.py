#!/usr/bin/env python3
"""Fit the single pre-specified age-adjusted secondary Cox model (docs/q1_age_adjusted_plan.md).

Refuses unless the plan is committed and unmodified and the cohort outputs match their
recorded hashes. Writes aggregate output only: results/survival/cox_age_adjusted.json.

  PYTHONPATH=src python scripts/fit_q1_age_adjusted.py           # write
  PYTHONPATH=src python scripts/fit_q1_age_adjusted.py --check   # compare with committed
"""
import argparse
import json
import subprocess
import sys
from datetime import date
from importlib.metadata import version
from pathlib import Path

from backblaze_audit.age_adjusted import add_powered_years, cox_age_adjusted, describe_age
from backblaze_audit.cohort_summary import load_verified
from backblaze_audit.survival import primary_frame

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--cohort-dir", type=Path, default=root / "data/processed/q1_cohort")
p.add_argument("--output", type=Path, default=root / "results/survival/cox_age_adjusted.json")
p.add_argument("--check", action="store_true")
a = p.parse_args()

plan = "docs/q1_age_adjusted_plan.md"
git = lambda *args: subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
if git("ls-files", "--error-unmatch", plan).returncode or git("diff", "--quiet", "HEAD", "--", plan).returncode:
    sys.exit(f"Refusing: {plan} must be committed and unmodified before fitting")
plan_commit = git("log", "--diff-filter=A", "-1", "--format=%H %cI", "--", plan).stdout.split()

drives, manifest = load_verified(a.cohort_dir)
window = (date.fromisoformat(manifest["window_end"]) - date.fromisoformat(manifest["baseline"])).days
frame = add_powered_years(primary_frame(drives, window), drives)
primary = json.loads((root / "results/survival/cox_summary.json").read_text(encoding="utf-8"))
result = dict(
    status="secondary analysis added after the primary plan, at the owner's direction (option b); primary results unchanged",
    plan=dict(file=plan, commit=plan_commit[0], committed_at=plan_commit[1]),
    cohort_output_sha256=manifest["output_sha256"],
    software={k: version(k) for k in ("lifelines", "statsmodels", "pandas", "numpy")},
    powered_years_by_group=describe_age(frame),
    unadjusted_primary=dict(hazard_ratio=primary["results"]["P"]["cox"]["hazard_ratio"],
                            hr_ci95=primary["results"]["P"]["cox"]["hr_ci95"]),
    age_adjusted=cox_age_adjusted(frame))
text = json.dumps(result, indent=2, sort_keys=True) + "\n"
if a.check:
    stored = json.loads(a.output.read_text(encoding="utf-8"))
    stored["plan"] = result["plan"]
    if json.dumps(stored, indent=2, sort_keys=True) + "\n" != text:
        sys.exit(f"FAIL: regenerated result differs from {a.output}")
    print("PASS: age-adjusted model reproduces the committed result")
else:
    a.output.write_text(text, encoding="utf-8")
    print(text)
