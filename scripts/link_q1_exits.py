#!/usr/bin/env python3
"""Link verified Q1 unexplained exits to a bounded run of later daily files. No models fitted.

Reads only the daily ZIP members in the window (default 2026-04-01..14) through
HTTP byte ranges or a local ZIP. The Q1 cohort outputs must match their recorded
hashes. Serial-level output goes to the Git-ignored data/processed tree; the
aggregate summary contains no serials and no baseline SMART group breakdown.

  PYTHONPATH=src python scripts/link_q1_exits.py \
    --remote-url https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q2_2026.zip
"""
import argparse
import json
from datetime import date
from pathlib import Path

from backblaze_audit.linkage import LINK_END, LINK_START, run_linkage
from backblaze_audit.sources import make_source

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
g = p.add_mutually_exclusive_group(required=True)
g.add_argument("--zip-path")
g.add_argument("--remote-url")
p.add_argument("--cohort-dir", type=Path, default=root / "data/processed/q1_cohort")
p.add_argument("--output-dir", type=Path, default=root / "data/processed/q1_exit_linkage")
p.add_argument("--summary", type=Path, default=root / "docs/q1_exit_linkage_summary.json")
p.add_argument("--start", type=date.fromisoformat, default=LINK_START)
p.add_argument("--end", type=date.fromisoformat, default=LINK_END)
p.add_argument("--max-compressed-bytes", type=int, default=400_000_000,
               help="Refuse to start if the selected members exceed this compressed size")
a = p.parse_args()

source = make_source(zip_path=a.zip_path, remote_url=a.remote_url)
try:
    selected = [m for m in source.members() if a.start <= date.fromisoformat(m.date_text) <= a.end]
    planned = sum(m.compressed_size or 0 for m in selected)
    print(f"selected {len(selected)} members, {planned} compressed bytes")
    if planned > a.max_compressed_bytes:
        raise SystemExit(f"Refusing: {planned} bytes exceeds --max-compressed-bytes {a.max_compressed_bytes}")
    summary = run_linkage(source, a.cohort_dir, a.output_dir, a.start, a.end)
finally:
    source.close()
a.summary.write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
print(json.dumps({k: summary[k] for k in ("all_exits", "by_exit_group")}, indent=2, default=str))
