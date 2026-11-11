from __future__ import annotations

from datetime import date
from pathlib import Path
import argparse
import csv
import hashlib
import io
import json
import urllib.request

from .pipeline import run_audit
from .sources import make_source


DEFAULT_Q1_URL = "https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q1_2026.zip"
CURRENT_SCHEMA_URL = "https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/Drive_Stats_Schema_Current.csv"
SCHEMA_HISTORY_URL = "https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/Drive_Stats_Schema_2018_Onward.csv"


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "asm2-backblaze-audit/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def load_official_schema() -> tuple[list[str], dict]:
    current = fetch_bytes(CURRENT_SCHEMA_URL)
    history = fetch_bytes(SCHEMA_HISTORY_URL)
    rows = list(csv.reader(io.StringIO(current.decode("utf-8-sig"))))
    version = rows[0][0].strip() if rows and rows[0] else "unknown"
    columns = [row[0].strip() for row in rows[1:] if row and row[0].strip()]
    meta = {
        "current_url": CURRENT_SCHEMA_URL,
        "current_sha256": hashlib.sha256(current).hexdigest(),
        "current_version_label": version,
        "history_url": SCHEMA_HISTORY_URL,
        "history_sha256": hashlib.sha256(history).hexdigest(),
        "comparison_note": "The official history CSV ends before Q1 2026; the observed daily headers are therefore the quarter-specific authority and are compared with the published current schema.",
    }
    return columns, meta


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Audit Backblaze Drive Stats without extracting the full archive.")
    group = result.add_mutually_exclusive_group(required=True)
    group.add_argument("--remote-url", help="HTTP ZIP URL; read with byte ranges")
    group.add_argument("--zip-path", help="Local ZIP path")
    group.add_argument("--input-dir", help="Directory containing daily CSVs")
    result.add_argument("--output-root", default=".")
    result.add_argument("--start", default="2026-01-01")
    result.add_argument("--end", default="2026-03-31")
    result.add_argument("--chunksize", type=int, default=50_000)
    result.add_argument("--max-files", type=int, help="Explicit staged smoke-test limit; recorded by reduced member count")
    result.add_argument("--skip-official-schema", action="store_true")
    result.add_argument("--artifact-meta", help="Optional JSON file with HEAD-derived artifact metadata")
    result.add_argument("--checkpoint", help="Ignored local checkpoint used to resume completed daily files")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    source = make_source(input_dir=args.input_dir, zip_path=args.zip_path, remote_url=args.remote_url)
    official_schema: list[str] = []
    schema_meta: dict = {}
    if not args.skip_official_schema:
        official_schema, schema_meta = load_official_schema()
    artifact_meta = {}
    if args.artifact_meta:
        artifact_meta = json.loads(Path(args.artifact_meta).read_text(encoding="utf-8"))
    result = run_audit(
        source=source,
        output_root=args.output_root,
        quarter_start=date.fromisoformat(args.start),
        quarter_end=date.fromisoformat(args.end),
        official_schema=official_schema,
        official_schema_meta=schema_meta,
        artifact_meta=artifact_meta,
        chunksize=args.chunksize,
        max_files=args.max_files,
        checkpoint_path=args.checkpoint,
    )
    print(json.dumps(result.metrics, indent=2, sort_keys=True))
    return 0
