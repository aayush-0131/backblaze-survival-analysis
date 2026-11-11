from __future__ import annotations

from datetime import date
from pathlib import Path
import csv

from backblaze_audit.pipeline import run_audit
from backblaze_audit.sources import DirectorySource


FIELDS_DAY_1 = [
    "date", "serial_number", "model", "capacity_bytes", "failure",
    "datacenter", "smart_9_normalized", "smart_9_raw", "smart_5_raw",
]
FIELDS_DAY_2 = FIELDS_DAY_1 + ["smart_197_raw"]


def write_csv(path: Path, fields: list[str], rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(fields)
        writer.writerows(rows)


def fixture_dir(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir(parents=True)
    write_csv(source / "2026-01-01.csv", FIELDS_DAY_1, [
        ["2026-01-01", "A", "ST_TEST", 1000, 0, "dc1", 99, 100, 0],
        ["2026-01-01", "B", "WDC TEST", 2000, 0, "dc1", "", "", 0],
    ])
    write_csv(source / "2026-01-02.csv", FIELDS_DAY_2, [
        ["2026-01-02", "A", "ST_TEST", 1000, 1, "dc1", 99, 124, 1, 0],
        ["2026-01-02", "B", "WDC TEST", 2000, 0, "dc1", "", "", 0, ""],
        ["2026-01-02", "B", "WDC TEST", 2000, 0, "dc1", "", "", 0, ""],
    ])
    return source


def run_fixture(tmp_path: Path, output_name: str = "out"):
    source = fixture_dir(tmp_path)
    output = tmp_path / output_name
    result = run_audit(
        source=DirectorySource(source),
        output_root=output,
        quarter_start=date(2026, 1, 1),
        quarter_end=date(2026, 1, 2),
        official_schema=FIELDS_DAY_2,
        official_schema_meta={"fixture": True},
        chunksize=2,
        progress=False,
    )
    return result, output


def test_core_reconciliation_and_duplicate_detection(tmp_path: Path):
    result, _ = run_fixture(tmp_path)
    assert result.metrics["drive_days"] == 5
    assert result.metrics["unique_drives"] == 2
    assert result.metrics["failure_rows"] == 1
    assert result.metrics["unique_failed_drives"] == 1
    checks = {row["check"]: row for row in result.tables["observation_checks.csv"]}
    assert checks["drive_day_key_duplicates"]["value"] == 1
    assert checks["invalid_date_rows"]["status"] == "PASS"
    assert checks["invalid_failure_rows"]["status"] == "PASS"


def test_schema_drift_and_missing_smart_are_safe(tmp_path: Path):
    result, _ = run_fixture(tmp_path)
    assert result.metrics["schema_variants"] == 2
    smart = {row["column"]: row for row in result.tables["smart_coverage_overall.csv"]}
    assert smart["smart_197_raw"]["non_null_count"] == 1
    assert smart["smart_9_raw"]["non_null_count"] == 2
    schema = {row["column"]: row for row in result.tables["schema_inventory.csv"]}
    assert schema["smart_197_raw"]["daily_files_present"] == 1


def test_failure_count_reconciles_by_model(tmp_path: Path):
    result, _ = run_fixture(tmp_path)
    model_failure_rows = sum(row["observed_failure_rows"] for row in result.tables["model_inventory.csv"])
    assert model_failure_rows == result.metrics["failure_rows"]


def test_summary_tables_are_deterministic(tmp_path: Path):
    result_a, output_a = run_fixture(tmp_path / "a", "out")
    result_b, output_b = run_fixture(tmp_path / "b", "out")
    for name in result_a.tables:
        left = (output_a / "results" / "tables" / name).read_bytes()
        right = (output_b / "results" / "tables" / name).read_bytes()
        assert left == right, name
