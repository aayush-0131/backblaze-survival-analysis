#!/usr/bin/env python3
"""Run the pre-specified Q1 survival analysis (docs/q1_analysis_plan.md). Owner-approved under D9.

Refuses to run unless docs/q1_decisions.json and docs/q1_analysis_plan.md are
committed and unmodified and D9 is signed, and unless every input matches its
recorded hash. Gap episode dates are re-derived by re-streaming the verified Q1
ZIP through the unchanged cohort builder, whose per-drive output must reproduce
cohort_drives.csv byte-for-byte. Serial-level frames stay in the ignored
data/processed/q1_survival/; committed outputs are aggregate.

  PYTHONPATH=src python scripts/fit_q1_survival.py --zip-path data/raw/data_Q1_2026.zip
  PYTHONPATH=src python scripts/fit_q1_survival.py --check
"""
import argparse
import csv
import json
import subprocess
import sys
from datetime import date
from importlib.metadata import version
from pathlib import Path

import pandas as pd

from backblaze_audit.cohort import drive_records, stream_cohort
from backblaze_audit.cohort_summary import load_verified
from backblaze_audit.history import digest, write_table
from backblaze_audit.sources import LocalZipSource
from backblaze_audit.survival import analyse, plot_primary, primary_frame, s1_frame, s2_intervals

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--cohort-dir", type=Path, default=root / "data/processed/q1_cohort")
p.add_argument("--linkage-dir", type=Path, default=root / "data/processed/q1_exit_linkage")
p.add_argument("--zip-path", type=Path, help="Verified Q1 ZIP; needed only if gap episodes are not cached")
p.add_argument("--work-dir", type=Path, default=root / "data/processed/q1_survival")
p.add_argument("--out-dir", type=Path, default=root / "results/survival")
p.add_argument("--check", action="store_true", help="Fail unless regenerated CSV/JSON equal the committed ones")
a = p.parse_args()

git = lambda *args: subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
commits = {}
for rel in ("docs/q1_decisions.json", "docs/q1_analysis_plan.md"):
    if git("ls-files", "--error-unmatch", rel).returncode or git("diff", "--quiet", "HEAD", "--", rel).returncode:
        sys.exit(f"Refusing: {rel} must be committed and unmodified")
    commits[rel] = git("log", "--diff-filter=A", "-1", "--format=%H %cI", "--", rel).stdout.split()
decisions = json.loads((root / "docs/q1_decisions.json").read_text(encoding="utf-8"))
if not decisions.get("D9", {}).get("signed"):
    sys.exit("Refusing: D9 (lift the gate) is not signed")

drives, manifest = load_verified(a.cohort_dir)
baseline, end = date.fromisoformat(manifest["baseline"]), date.fromisoformat(manifest["window_end"])
window = (end - baseline).days
link_summary = json.loads((root / "docs/q1_exit_linkage_summary.json").read_text(encoding="utf-8"))
link_path = a.linkage_dir / "exit_linkage_drives.csv"
if digest(link_path) != link_summary["serial_level_output_sha256"]:
    sys.exit("Refusing: linkage records differ from docs/q1_exit_linkage_summary.json")
linkage = pd.read_csv(link_path, dtype={"serial_number": "string"})

a.work_dir.mkdir(parents=True, exist_ok=True)
episodes_path, meta_path = a.work_dir / "gap_episodes.csv", a.work_dir / "gap_episodes_meta.json"
cohort_sha = manifest["output_sha256"]["cohort_drives.csv"]
meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
if meta.get("cohort_drives_sha256") != cohort_sha or digest(episodes_path) != meta.get("episodes_sha256"):
    if a.zip_path is None:
        sys.exit("Gap episodes not cached; pass --zip-path to the verified Q1 ZIP")
    recorded = json.loads((root / "results/audit/data_manifest.json").read_text())["source"]["members"]
    source = LocalZipSource(a.zip_path)
    try:
        audit, _ = stream_cohort(source, manifest["model"], baseline, end,
                                 expected_crc32={m["date"]: m["crc32"] for m in recorded})
    finally:
        source.close()
    write_table(a.work_dir / "rerun_cohort_drives.csv", drive_records(audit))
    if digest(a.work_dir / "rerun_cohort_drives.csv") != cohort_sha:
        sys.exit("Refusing: re-streamed builder output differs from the verified cohort_drives.csv")
    write_table(episodes_path, [dict(serial_number=s, last_seen=l, returned=r)
                                for s, eps in sorted(audit.gap_episodes.items()) for l, r in eps])
    meta = dict(cohort_drives_sha256=cohort_sha, rerun_reproduced_cohort_drives=True,
                episodes_sha256=digest(episodes_path))
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
ep = pd.read_csv(episodes_path, dtype={"serial_number": "string"})
episodes = {}
for r in ep.itertuples():
    episodes.setdefault(str(r.serial_number), []).append((date.fromisoformat(r.last_seen), date.fromisoformat(r.returned)))

P = primary_frame(drives, window)
S1 = s1_frame(P, linkage, window)
inc = drives[drives["inclusion"] == "included"]
missing = dict(zip(inc["serial_number"].astype(str), inc["missing_days_in_gaps"].astype(int)))
S2 = s2_intervals(P, missing, {s: e for s, e in episodes.items() if s in missing}, baseline)
for name, frame in (("P", P), ("S1", S1), ("S2", S2)):
    frame.to_csv(a.work_dir / f"frame_{name}.csv", index=False)  # serial-level, ignored

steps, results = analyse({"P": (P, False), "S1": (S1, False), "S2": (S2, True)})
excluded = drives[drives["inclusion"] != "included"]
summary = dict(
    plan="docs/q1_analysis_plan.md", gate="D9 signed by the owner (Aayush), 2026-11-10",
    plan_and_decisions_first_committed={k: dict(commit=v[0], committed_at=v[1]) for k, v in commits.items()},
    model=manifest["model"], baseline=manifest["baseline"], window_end=manifest["window_end"],
    time_scale="calendar days since baseline", exposure="baseline SMART 197 raw nonzero vs zero (D1)",
    inputs=dict(cohort_drives_sha256=cohort_sha, linkage_sha256=link_summary["serial_level_output_sha256"],
                gap_episodes_rederived_and_cohort_reproduced=meta["rerun_reproduced_cohort_drives"]),
    excluded_by_design=dict(
        later_arrivals=int((excluded["inclusion"] == "excluded_later_arrival").sum()),
        later_arrival_failures=int(((excluded["inclusion"] == "excluded_later_arrival")
                                    & excluded["first_failure_date"].notna()).sum()),
        failure_on_baseline_date=int((excluded["inclusion"] == "excluded_failure_on_or_before_baseline").sum())),
    analyses=dict(P="primary (D2, D3 primary, D4 primary, D5, D6)",
                  S1="D3 sensitivity: 93 linkage-verified exits censored at day 89",
                  S2="D4 sensitivity: gap days removed via start/stop intervals"),
    results=results,
    software={k: version(k) for k in ("lifelines", "statsmodels", "pandas", "numpy", "scipy", "matplotlib")},
    not_done="no log-rank test, SMART 5 model, covariate adjustment, interaction or model selection")

a.out_dir.mkdir(parents=True, exist_ok=True)
km_text_rows = steps
cox_text = json.dumps(summary, indent=2, sort_keys=True) + "\n"
if a.check:
    tmp = a.work_dir / "check_km_estimates.csv"
    write_table(tmp, km_text_rows)
    stored = json.loads((a.out_dir / "cox_summary.json").read_text())
    if tmp.read_text() != (a.out_dir / "km_estimates.csv").read_text() or stored != json.loads(cox_text):
        sys.exit("FAIL: regenerated survival outputs differ from results/survival")
    print("PASS: gate, input hashes and cohort reproduction verified; KM and Cox outputs reproduce")
else:
    write_table(a.out_dir / "km_estimates.csv", km_text_rows)
    (a.out_dir / "cox_summary.json").write_text(cox_text)
    plot_primary(steps, a.out_dir / "km_primary.png",
                 "Q1 2026 ST12000NM0008: Kaplan–Meier by baseline SMART 197 (primary analysis)",
                 counts=results["P"]["kaplan_meier"])
    print(json.dumps({k: dict(events=v["events"], drives=v["drives"], cox=dict(
        hr=v["cox"]["hazard_ratio"], ci=v["cox"]["hr_ci95"], p=v["cox"]["p_value"])) for k, v in results.items()}, indent=1))
