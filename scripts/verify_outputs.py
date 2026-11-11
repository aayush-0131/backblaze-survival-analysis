#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json


ROOT = Path(__file__).resolve().parents[1]


def rows(name: str) -> list[dict[str, str]]:
    with (ROOT / "results" / "tables" / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    manifest = json.loads((ROOT / "results" / "audit" / "data_manifest.json").read_text(encoding="utf-8"))
    metrics = manifest["metrics"]
    daily = rows("daily_inventory.csv")
    models = rows("model_inventory.csv")
    schema = rows("schema_inventory.csv")
    smart = rows("smart_coverage_overall.csv")
    candidates = rows("candidate_cohorts.csv")
    checks = {row["check"]: row for row in rows("observation_checks.csv")}
    published = {row["measure"]: row for row in rows("published_reconciliation.csv")}

    assert len(daily) == metrics["daily_csv_files"] == 90
    assert sum(int(row["rows"]) for row in daily) == metrics["drive_days"] == 30_597_484
    assert sum(int(row["observed_failure_rows"]) for row in models) == metrics["failure_rows"] == 1_030
    assert metrics["failure_rows"] == metrics["unique_failed_drives"]
    assert len(schema) == metrics["observed_columns"] == 197
    assert len(smart) == metrics["observed_smart_columns"] == 186
    assert 2 <= len(candidates) <= 4
    assert checks["drive_day_key_duplicates"]["status"] == "PASS"
    assert checks["invalid_date_rows"]["status"] == "PASS"
    assert checks["invalid_failure_rows"]["status"] == "PASS"
    assert checks["schema_variants_within_quarter"]["value"] == "1"
    assert published["raw_end_drive_count"]["status"] == "PASS"
    assert published["failure_rows"]["status"] == "PASS"

    for relative, expected in manifest["output_sha256"].items():
        actual = sha256(ROOT / relative)
        assert actual == expected, f"hash mismatch for {relative}: {actual} != {expected}"

    print("PASS: output hashes, row/failure reconciliation, schema, key, date, and candidate checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
