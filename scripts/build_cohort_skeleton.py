#!/usr/bin/env python3
"""Build per-drive fixed-baseline cohort records for ONE exact model. No models fitted.

Outputs are serial-level and default to the Git-ignored data/processed/ tree.
Review cohort_accounting.csv with the group before copying any aggregate into results/.
"""
import argparse
from datetime import date
from pathlib import Path
import json

from backblaze_audit.cohort import SEAGATE, run_cohort
from backblaze_audit.history import MODELS, Q1_END, Q1_START
from backblaze_audit.sources import make_source

p = argparse.ArgumentParser(description=__doc__)
g = p.add_mutually_exclusive_group(required=True)
g.add_argument("--zip-path", help="Local official quarterly ZIP (recommended)")
g.add_argument("--input-dir", help="Directory of daily YYYY-MM-DD.csv files (may be candidate-only)")
g.add_argument("--remote-url", help="Official ZIP URL, read with HTTP byte ranges")
p.add_argument("--model", choices=MODELS, default=SEAGATE)
p.add_argument("--baseline", type=date.fromisoformat, default=Q1_START)
p.add_argument("--end", type=date.fromisoformat, default=Q1_END)
p.add_argument("--output-dir", type=Path, default=Path("data/processed/q1_cohort"))
p.add_argument("--chunksize", type=int, default=50_000)
p.add_argument("--expect-manifest", type=Path,
               help="Audit manifest whose source.members CRC32 values every member must match "
                    "(e.g. results/audit/data_manifest.json for Q1 2026)")
a = p.parse_args()
expected = None
if a.expect_manifest:
    recorded = json.loads(a.expect_manifest.read_text(encoding="utf-8"))["source"]["members"]
    expected = {m["date"]: m["crc32"] for m in recorded}
source = make_source(input_dir=a.input_dir, zip_path=a.zip_path, remote_url=a.remote_url)
try:
    accounting = run_cohort(source, a.output_dir, a.model, a.baseline, a.end, a.chunksize, expected)
finally:
    source.close()
print(json.dumps(accounting, indent=2, default=str))
