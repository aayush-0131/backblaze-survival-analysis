#!/usr/bin/env python3
import argparse
from datetime import date
from pathlib import Path
import json

from backblaze_audit.history import run_history

p=argparse.ArgumentParser(description="Bounded descriptive history/SMART audit from local ZIPs")
p.add_argument("--zip", action="append", required=True, type=Path)
p.add_argument("--output-root", type=Path, default=Path("."))
p.add_argument("--baseline", type=date.fromisoformat, required=True)
p.add_argument("--end", type=date.fromisoformat, required=True)
p.add_argument("--chunksize", type=int, default=50000)
p.add_argument("--provenance", type=Path)
p.add_argument("--checkpoint", type=Path, help="Trusted local checkpoint; never use a downloaded pickle")
a=p.parse_args()
run_history(a.zip,a.output_root,a.baseline,a.end,a.chunksize,
            json.loads(a.provenance.read_text()) if a.provenance else None,a.checkpoint)
