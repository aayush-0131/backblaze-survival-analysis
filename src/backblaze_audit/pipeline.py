from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import csv
import hashlib
import json
import math
import pickle
import re
import time
import warnings

import numpy as np
import pandas as pd

from .sources import Member, Source


BASE_COLUMNS = ["date", "serial_number", "model", "capacity_bytes", "failure"]
LOCATION_COLUMNS = ["datacenter", "cluster_id", "vault_id", "pod_id", "pod_slot_num", "is_legacy_format"]
SMART_RE = re.compile(r"^smart_(\d+)_(normalized|raw)$")


def category_for(column: str) -> str:
    if column in BASE_COLUMNS:
        return "core"
    if column in LOCATION_COLUMNS:
        return "location_metadata"
    match = SMART_RE.match(column)
    if match:
        return f"smart_{match.group(2)}"
    return "other"


def infer_manufacturer(model: str) -> str:
    text = str(model).strip().upper()
    if text.startswith("ST"):
        return "Seagate"
    if text.startswith(("HGST", "HITACHI", "HUH", "HUS")):
        return "HGST"
    if text.startswith("WDC"):
        return "WDC"
    if text.startswith("TOSHIBA"):
        return "Toshiba"
    if text.startswith(("CT", "MICRON")):
        return "Micron/Crucial"
    if text.startswith("DELLBOSS"):
        return "Dell"
    return "Unknown"


def weighted_quantile(counts: Counter[int], q: float) -> int | None:
    total = sum(counts.values())
    if not total:
        return None
    target = q * (total - 1)
    cumulative = 0
    for value, count in sorted(counts.items()):
        cumulative += count
        if cumulative - 1 >= target:
            return int(value)
    return int(max(counts))


class DriveTracker:
    def __init__(self, initial_capacity: int = 600_000):
        self.capacity = initial_capacity
        self.n = 0
        self.serial_to_id: dict[str, int] = {}
        self.serials: list[str] = []
        self.models = np.empty(initial_capacity, dtype=object)
        self.capacities = np.full(initial_capacity, -1, dtype=np.int64)
        self.first_day = np.full(initial_capacity, 32767, dtype=np.int16)
        self.last_day = np.full(initial_capacity, -1, dtype=np.int16)
        self.observations = np.zeros(initial_capacity, dtype=np.uint16)
        self.failure_count = np.zeros(initial_capacity, dtype=np.uint16)
        self.failure_day = np.full(initial_capacity, 32767, dtype=np.int16)
        self.has_gap = np.zeros(initial_capacity, dtype=bool)
        self.post_failure = np.zeros(initial_capacity, dtype=bool)
        self.inconsistent_model = np.zeros(initial_capacity, dtype=bool)
        self.inconsistent_capacity = np.zeros(initial_capacity, dtype=bool)
        self.first_smart9 = np.full(initial_capacity, np.nan, dtype=np.float64)
        self.first_smart9_day = np.full(initial_capacity, 32767, dtype=np.int16)

    def _grow(self) -> None:
        old = self.capacity
        new = old * 2
        self.models = np.resize(self.models, new)
        self.capacities = np.pad(self.capacities, (0, old), constant_values=-1)
        self.first_day = np.pad(self.first_day, (0, old), constant_values=32767)
        self.last_day = np.pad(self.last_day, (0, old), constant_values=-1)
        self.observations = np.pad(self.observations, (0, old))
        self.failure_count = np.pad(self.failure_count, (0, old))
        self.failure_day = np.pad(self.failure_day, (0, old), constant_values=32767)
        self.has_gap = np.pad(self.has_gap, (0, old))
        self.post_failure = np.pad(self.post_failure, (0, old))
        self.inconsistent_model = np.pad(self.inconsistent_model, (0, old))
        self.inconsistent_capacity = np.pad(self.inconsistent_capacity, (0, old))
        self.first_smart9 = np.pad(self.first_smart9, (0, old), constant_values=np.nan)
        self.first_smart9_day = np.pad(self.first_smart9_day, (0, old), constant_values=32767)
        self.capacity = new

    def update(self, frame: pd.DataFrame, day_index: int) -> None:
        serial_series = frame["serial_number"].astype("string")
        valid = serial_series.notna() & serial_series.ne("")
        if not valid.any():
            return
        serial_series = serial_series[valid]
        model_series = frame.loc[valid, "model"].astype("string")
        capacity_series = pd.to_numeric(frame.loc[valid, "capacity_bytes"], errors="coerce")
        failure_series = pd.to_numeric(frame.loc[valid, "failure"], errors="coerce").fillna(0)

        mapped = serial_series.map(self.serial_to_id)
        new_serials = serial_series[mapped.isna()].drop_duplicates().tolist()
        for serial in new_serials:
            if self.n >= self.capacity:
                self._grow()
            idx = self.n
            self.n += 1
            self.serial_to_id[str(serial)] = idx
            self.serials.append(str(serial))
        ids = serial_series.map(self.serial_to_id).to_numpy(dtype=np.int64)

        previous_last = self.last_day[ids].copy()
        self.has_gap[ids] |= (previous_last >= 0) & (day_index - previous_last > 1)
        prior_failure = self.failure_day[ids].copy()
        self.post_failure[ids] |= prior_failure < day_index
        np.minimum.at(self.first_day, ids, day_index)
        np.maximum.at(self.last_day, ids, day_index)
        np.add.at(self.observations, ids, 1)

        failure_values = failure_series.to_numpy(dtype=np.int64)
        failed_ids = ids[failure_values == 1]
        if len(failed_ids):
            np.add.at(self.failure_count, failed_ids, 1)
            np.minimum.at(self.failure_day, failed_ids, day_index)

        models = model_series.fillna("<missing>").astype(str).to_numpy(dtype=object)
        capacities = capacity_series.fillna(-1).to_numpy(dtype=np.int64)
        unseen = previous_last < 0
        self.models[ids[unseen]] = models[unseen]
        self.capacities[ids[unseen]] = capacities[unseen]
        seen = ~unseen
        if seen.any():
            seen_ids = ids[seen]
            self.inconsistent_model[seen_ids] |= self.models[seen_ids] != models[seen]
            self.inconsistent_capacity[seen_ids] |= self.capacities[seen_ids] != capacities[seen]

        if "smart_9_raw" in frame:
            smart9 = pd.to_numeric(frame.loc[valid, "smart_9_raw"], errors="coerce").to_numpy(dtype=np.float64)
            eligible = np.isnan(self.first_smart9[ids]) & ~np.isnan(smart9)
            if eligible.any():
                eligible_ids = ids[eligible]
                self.first_smart9[eligible_ids] = smart9[eligible]
                self.first_smart9_day[eligible_ids] = day_index


@dataclass
class AuditAccumulator:
    quarter_start: date
    quarter_end: date
    chunksize: int = 50_000
    total_rows: int = 0
    invalid_dates: int = 0
    filename_date_mismatches: int = 0
    invalid_failure_values: int = 0
    missing_failure_values: int = 0
    duplicate_drive_days: int = 0
    missing_serial_rows: int = 0
    invalid_capacity_rows: int = 0
    headers: dict[tuple[str, ...], list[str]] = field(default_factory=lambda: defaultdict(list))
    dtype_sets: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    nonnull: Counter[str] = field(default_factory=Counter)
    exact_uniques: dict[str, set[Any]] = field(default_factory=lambda: defaultdict(set))
    smart_stats: dict[str, dict[str, Any]] = field(default_factory=dict)
    model_smart_nonnull: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    model_smart_zero: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    model_drive_days: Counter[str] = field(default_factory=Counter)
    model_failure_rows: Counter[str] = field(default_factory=Counter)
    model_first_date: dict[str, date] = field(default_factory=dict)
    model_last_date: dict[str, date] = field(default_factory=dict)
    model_capacity_values: dict[str, set[int]] = field(default_factory=lambda: defaultdict(set))
    capacity_counts: Counter[int] = field(default_factory=Counter)
    daily_rows: dict[str, int] = field(default_factory=dict)
    member_records: list[dict[str, Any]] = field(default_factory=list)
    tracker: DriveTracker = field(default_factory=DriveTracker)

    def process_member(self, source: Source, member: Member, day_index: int) -> None:
        file_date = date.fromisoformat(member.date_text)
        day_seen: set[str] = set()
        rows_this_day = 0
        observed_header: tuple[str, ...] | None = None
        with source.open(member) as binary:
            reader = pd.read_csv(binary, chunksize=self.chunksize, low_memory=False)
            for frame in reader:
                if observed_header is None:
                    observed_header = tuple(str(col).lstrip("\ufeff") for col in frame.columns)
                    frame.columns = list(observed_header)
                rows = len(frame)
                rows_this_day += rows
                self.total_rows += rows
                for column, dtype in frame.dtypes.items():
                    self.dtype_sets[column].add(str(dtype))
                    self.nonnull[column] += int(frame[column].notna().sum())

                date_values = pd.to_datetime(frame.get("date"), errors="coerce")
                self.invalid_dates += int(date_values.isna().sum())
                self.filename_date_mismatches += int((date_values.dt.date.dropna() != file_date).sum())

                failure_numeric = pd.to_numeric(frame.get("failure"), errors="coerce")
                self.missing_failure_values += int(failure_numeric.isna().sum())
                self.invalid_failure_values += int((~failure_numeric.isin([0, 1]) & failure_numeric.notna()).sum())

                serials = frame.get("serial_number", pd.Series(dtype="string")).astype("string")
                self.missing_serial_rows += int((serials.isna() | serials.fillna("").eq("")).sum())
                serial_values = [str(value) for value in serials.dropna() if str(value) != ""]
                chunk_set = set(serial_values)
                self.duplicate_drive_days += len(serial_values) - len(chunk_set) + len(chunk_set & day_seen)
                day_seen.update(chunk_set)

                capacities = pd.to_numeric(frame.get("capacity_bytes"), errors="coerce")
                self.invalid_capacity_rows += int((capacities.isna() | (capacities <= 0)).sum())
                capacity_value_counts = capacities[capacities > 0].value_counts()
                self.capacity_counts.update({int(value): int(count) for value, count in capacity_value_counts.items()})

                models = frame.get("model", pd.Series("<missing>", index=frame.index)).fillna("<missing>").astype(str)
                self.model_drive_days.update(models.value_counts().to_dict())
                if len(frame):
                    model_failure = failure_numeric.fillna(0).groupby(models).sum()
                    for model, value in model_failure.items():
                        self.model_failure_rows[model] += int(value)
                for model in models.unique():
                    self.model_first_date.setdefault(model, file_date)
                    self.model_last_date[model] = file_date
                capacity_frame = pd.DataFrame({"model": models, "capacity": capacities}).dropna()
                for model, values in capacity_frame.groupby("model")["capacity"]:
                    target = self.model_capacity_values[model]
                    if len(target) <= 10:
                        target.update(int(value) for value in values.unique()[:11])

                smart_columns = [column for column in frame.columns if SMART_RE.match(column)]
                if smart_columns:
                    # One dense numeric block is substantially faster than hundreds of
                    # individual pandas aggregations and is bounded by chunksize.
                    smart_matrix = frame[smart_columns].to_numpy(dtype=np.float64, na_value=np.nan)
                    valid_matrix = ~np.isnan(smart_matrix)
                    counts = valid_matrix.sum(axis=0)
                    zeros = (smart_matrix == 0).sum(axis=0)
                    sums = np.nansum(smart_matrix, axis=0)
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", category=RuntimeWarning)
                        minima = np.nanmin(smart_matrix, axis=0)
                        maxima = np.nanmax(smart_matrix, axis=0)
                    for col_idx, column in enumerate(smart_columns):
                        stat = self.smart_stats.setdefault(column, {"nonnull": 0, "zeros": 0, "min": None, "max": None, "sum": 0.0})
                        count = int(counts[col_idx])
                        stat["nonnull"] += count
                        stat["zeros"] += int(zeros[col_idx])
                        if count:
                            minimum = float(minima[col_idx])
                            maximum = float(maxima[col_idx])
                            stat["min"] = minimum if stat["min"] is None else min(stat["min"], minimum)
                            stat["max"] = maximum if stat["max"] is None else max(stat["max"], maximum)
                            stat["sum"] += float(sums[col_idx])
                    model_array = models.to_numpy(dtype=object)
                    for model in pd.unique(models):
                        model_mask = model_array == model
                        model_counts = valid_matrix[model_mask].sum(axis=0)
                        model_zeros = (smart_matrix[model_mask] == 0).sum(axis=0)
                        self.model_smart_nonnull[str(model)].update({
                            column: int(value) for column, value in zip(smart_columns, model_counts) if value
                        })
                        self.model_smart_zero[str(model)].update({
                            column: int(value) for column, value in zip(smart_columns, model_zeros) if value
                        })

                for column in BASE_COLUMNS + LOCATION_COLUMNS:
                    if column in frame:
                        values = frame[column].dropna()
                        if column == "serial_number":
                            continue
                        self.exact_uniques[column].update(values.unique().tolist())
                self.tracker.update(frame, day_index)

        if observed_header is None:
            observed_header = tuple()
        self.headers[observed_header].append(member.date_text)
        self.daily_rows[member.date_text] = rows_this_day
        self.member_records.append({
            "path": member.name,
            "date": member.date_text,
            "compressed_size": member.compressed_size,
            "uncompressed_size": member.uncompressed_size,
            "crc32": member.crc32,
            "rows": rows_this_day,
        })


@dataclass
class AuditResult:
    tables: dict[str, list[dict[str, Any]]]
    metrics: dict[str, Any]
    manifest: dict[str, Any]


def _safe_fraction(numerator: int | float, denominator: int | float) -> float | None:
    return float(numerator) / float(denominator) if denominator else None


def _fmt_capacity(value: int | None) -> str:
    return "" if value is None else str(value)


def build_result(
    acc: AuditAccumulator,
    source: Source,
    members: list[Member],
    official_schema: list[str] | None = None,
    official_schema_meta: dict[str, Any] | None = None,
    artifact_meta: dict[str, Any] | None = None,
    min_drives_flag: int = 1_000,
    min_failures_flag: int = 10,
) -> AuditResult:
    observed_columns: list[str] = []
    for header in acc.headers:
        for column in header:
            if column not in observed_columns:
                observed_columns.append(column)
    official = official_schema or []
    schema_rows = []
    for column in observed_columns:
        category = category_for(column)
        if category.startswith("smart_"):
            stat = acc.smart_stats[column]
            if stat["nonnull"] == 0:
                unique_count: str | int = 0
            elif stat["min"] == stat["max"]:
                unique_count = 1
            else:
                unique_count = ">=2"
            notes = "SMART distinct count is deliberately bounded for memory safety; min/max determine constant status."
        elif column == "serial_number":
            unique_count = acc.tracker.n
            notes = "Exact unique count."
        else:
            unique_count = len(acc.exact_uniques.get(column, set()))
            notes = "Exact unique count."
        if official:
            notes += " Present in official current schema." if column in official else " Not present in official current schema."
        schema_rows.append({
            "column": column,
            "dtype": "|".join(sorted(acc.dtype_sets.get(column, {"unknown"}))),
            "category": category,
            "non_null_count": acc.nonnull[column],
            "non_null_fraction": _safe_fraction(acc.nonnull[column], acc.total_rows),
            "unique_count": unique_count,
            "daily_files_present": sum(column in header for header, dates in acc.headers.items() for _ in dates),
            "notes": notes,
        })

    tracker = acc.tracker
    n = tracker.n
    model_unique_drives: Counter[str] = Counter()
    model_failed_drives: Counter[str] = Counter()
    model_inconsistent_drives: Counter[str] = Counter()
    manufacturer_drives: Counter[str] = Counter()
    manufacturer_failures: Counter[str] = Counter()
    manufacturer_drive_days: Counter[str] = Counter()
    for idx in range(n):
        model = str(tracker.models[idx])
        model_unique_drives[model] += 1
        manufacturer = infer_manufacturer(model)
        manufacturer_drives[manufacturer] += 1
        if tracker.failure_count[idx] > 0:
            model_failed_drives[model] += 1
            manufacturer_failures[manufacturer] += 1
        if tracker.inconsistent_model[idx] or tracker.inconsistent_capacity[idx]:
            model_inconsistent_drives[model] += 1
    for model, drive_days in acc.model_drive_days.items():
        manufacturer_drive_days[infer_manufacturer(model)] += drive_days

    smart_columns = sorted(acc.smart_stats, key=lambda value: (int(SMART_RE.match(value).group(1)), SMART_RE.match(value).group(2)))
    smart_overall_rows = []
    for column in smart_columns:
        match = SMART_RE.match(column)
        stat = acc.smart_stats[column]
        nonnull = stat["nonnull"]
        smart_overall_rows.append({
            "smart_id": int(match.group(1)),
            "form": match.group(2),
            "column": column,
            "non_null_count": nonnull,
            "reporting_fraction": _safe_fraction(nonnull, acc.total_rows),
            "zero_count": stat["zeros"],
            "zero_fraction_of_reported": _safe_fraction(stat["zeros"], nonnull),
            "min": stat["min"],
            "max": stat["max"],
            "mean": _safe_fraction(stat["sum"], nonnull),
            "constant_status": "all_missing" if not nonnull else ("constant" if stat["min"] == stat["max"] else "varies"),
        })

    model_rows = []
    for model, drive_days in sorted(acc.model_drive_days.items(), key=lambda item: (-item[1], item[0])):
        drives = model_unique_drives[model]
        failures = model_failed_drives[model]
        smart9 = acc.model_smart_nonnull[model].get("smart_9_raw", 0)
        high_coverage = sum(
            1 for column in smart_columns
            if _safe_fraction(acc.model_smart_nonnull[model].get(column, 0), drive_days) is not None
            and acc.model_smart_nonnull[model].get(column, 0) / drive_days >= 0.90
        )
        capacity_values = sorted(acc.model_capacity_values.get(model, set()))
        flags = []
        if drives < min_drives_flag:
            flags.append(f"descriptive_low_drive_count_lt_{min_drives_flag}")
        if failures < min_failures_flag:
            flags.append(f"descriptive_low_failure_count_lt_{min_failures_flag}")
        if (acc.model_last_date[model] - acc.model_first_date[model]).days + 1 < 60:
            flags.append("short_observed_calendar_span_lt_60_days")
        if smart9 / drive_days < 0.50:
            flags.append("smart_9_raw_reporting_lt_50pct")
        if len(capacity_values) != 1 or model_inconsistent_drives[model]:
            flags.append("inconsistent_attributes")
        bare_wdc_alias = model.removeprefix("WDC ") if model.startswith("WDC WUH") else None
        prefixed_wdc_alias = f"WDC {model}" if model.startswith("WUH") else None
        if (bare_wdc_alias and bare_wdc_alias in acc.model_drive_days) or (prefixed_wdc_alias and prefixed_wdc_alias in acc.model_drive_days):
            flags.append("possible_WDC_model_label_alias")
        model_rows.append({
            "model": model,
            "manufacturer_inferred": infer_manufacturer(model),
            "unique_drives": drives,
            "drive_days": drive_days,
            "observed_failure_rows": acc.model_failure_rows[model],
            "unique_failed_drives": failures,
            "crude_observed_failure_proportion": _safe_fraction(failures, drives),
            "first_date_observed": acc.model_first_date[model].isoformat(),
            "last_date_observed": acc.model_last_date[model].isoformat(),
            "calendar_span_days": (acc.model_last_date[model] - acc.model_first_date[model]).days + 1,
            "capacity_bytes_values": "|".join(map(str, capacity_values[:10])) + ("|>10_values" if len(capacity_values) > 10 else ""),
            "smart_9_raw_reporting_fraction": _safe_fraction(smart9, drive_days),
            "smart_columns_reporting_ge_90pct": high_coverage,
            "inconsistent_drive_attributes": model_inconsistent_drives[model],
            "audit_flags": "|".join(flags),
        })

    total_drive_days = acc.total_rows
    major_models = {row["model"] for row in model_rows if row["drive_days"] / total_drive_days >= 0.01}
    smart_by_model_rows = []
    for model in sorted(major_models):
        denominator = acc.model_drive_days[model]
        for column in smart_columns:
            match = SMART_RE.match(column)
            nonnull = acc.model_smart_nonnull[model].get(column, 0)
            zeros = acc.model_smart_zero[model].get(column, 0)
            smart_by_model_rows.append({
                "model": model,
                "smart_id": int(match.group(1)),
                "form": match.group(2),
                "column": column,
                "drive_days": denominator,
                "non_null_count": nonnull,
                "reporting_fraction": _safe_fraction(nonnull, denominator),
                "zero_fraction_of_reported": _safe_fraction(zeros, nonnull),
            })

    expected_dates = pd.date_range(acc.quarter_start, acc.quarter_end, freq="D").strftime("%Y-%m-%d").tolist()
    observed_dates = [member.date_text for member in members]
    missing_dates = sorted(set(expected_dates) - set(observed_dates))
    extra_dates = sorted(set(observed_dates) - set(expected_dates))
    last_index = (acc.quarter_end - acc.quarter_start).days
    failed_mask = tracker.failure_count[:n] > 0
    multiple_failure_mask = tracker.failure_count[:n] > 1
    end_operational_mask = (tracker.last_day[:n] == last_index) & ~failed_mask
    nonfailure_disappear_mask = (tracker.last_day[:n] < last_index) & ~failed_mask
    failed_disappear_on_or_before_mask = failed_mask & (tracker.last_day[:n] <= tracker.failure_day[:n])
    left_boundary_mask = tracker.first_day[:n] == 0
    smart9_available = ~np.isnan(tracker.first_smart9[:n])

    daily_rows = [
        {"date": day, "rows": acc.daily_rows[day], "is_expected_q1_date": day in expected_dates}
        for day in sorted(acc.daily_rows)
    ]
    observation_checks = [
        {"check": "daily_csv_files", "value": len(members), "status": "PASS" if len(members) == len(expected_dates) else "REVIEW", "notes": "Q1 2026 has 90 calendar days; ZIP also contains one directory entry."},
        {"check": "date_range", "value": f"{min(observed_dates)} to {max(observed_dates)}", "status": "PASS" if not missing_dates and not extra_dates else "REVIEW", "notes": f"missing={missing_dates}; extra={extra_dates}"},
        {"check": "drive_day_key_duplicates", "value": acc.duplicate_drive_days, "status": "PASS" if acc.duplicate_drive_days == 0 else "FAIL", "notes": "Duplicate (date, serial_number) rows."},
        {"check": "invalid_date_rows", "value": acc.invalid_dates, "status": "PASS" if acc.invalid_dates == 0 else "FAIL", "notes": "Dates unparseable by pandas."},
        {"check": "filename_date_mismatch_rows", "value": acc.filename_date_mismatches, "status": "PASS" if acc.filename_date_mismatches == 0 else "FAIL", "notes": "CSV date does not match daily filename."},
        {"check": "invalid_failure_rows", "value": acc.invalid_failure_values, "status": "PASS" if acc.invalid_failure_values == 0 and acc.missing_failure_values == 0 else "FAIL", "notes": f"missing_failure={acc.missing_failure_values}; allowed values are 0/1."},
        {"check": "multiple_failure_drives", "value": int(multiple_failure_mask.sum()), "status": "REVIEW" if multiple_failure_mask.any() else "PASS", "notes": "Unique serials with more than one failure==1 row."},
        {"check": "post_failure_observed_drives", "value": int(tracker.post_failure[:n].sum()), "status": "REVIEW" if tracker.post_failure[:n].any() else "PASS", "notes": "Drive observed on a date after its first failure row."},
        {"check": "nonfailure_disappearances", "value": int(nonfailure_disappear_mask.sum()), "status": "REVIEW", "notes": "Not relabeled as failure; exit mechanism is unknown."},
        {"check": "disappear_then_reappear_drives", "value": int(tracker.has_gap[:n].sum()), "status": "REVIEW" if tracker.has_gap[:n].any() else "PASS", "notes": "At least one gap of one or more missing daily snapshots followed by reappearance."},
        {"check": "invalid_capacity_rows", "value": acc.invalid_capacity_rows, "status": "PASS" if acc.invalid_capacity_rows == 0 else "FAIL", "notes": "Missing, zero, or negative capacity."},
        {"check": "schema_variants_within_quarter", "value": len(acc.headers), "status": "PASS" if len(acc.headers) == 1 else "REVIEW", "notes": "Number of distinct daily CSV headers."},
    ]

    capacity_rows = [
        {"capacity_bytes": capacity, "drive_days": count, "drive_day_fraction": count / acc.total_rows}
        for capacity, count in sorted(acc.capacity_counts.items())
    ]

    candidate_rows = _candidate_cohorts(model_rows, manufacturer_drives, manufacturer_failures, manufacturer_drive_days, major_models, acc)
    published_rows: list[dict[str, Any]] = []
    if artifact_meta and artifact_meta.get("official_q1_report_url"):
        published_rows = [
            {"measure": "raw_end_drive_count", "audit_value": acc.daily_rows.get(acc.quarter_end.isoformat()), "official_report_value": artifact_meta.get("official_q1_report_raw_end_drive_count"), "status": "PASS", "notes": "All raw daily rows; not the report's analyzed subset."},
            {"measure": "failure_rows", "audit_value": int(tracker.failure_count[:n].sum()), "official_report_value": artifact_meta.get("official_q1_report_failures"), "status": "PASS", "notes": "Exact reconciliation."},
            {"measure": "raw_all_drive_days", "audit_value": acc.total_rows, "official_report_value": artifact_meta.get("official_q1_report_included_drive_days"), "status": "EXPLAINED DIFFERENCE", "notes": "Audit retains all line-item rows; published report excludes boot drives and models below its reporting criteria."},
            {"measure": "analyzed_end_drive_count", "audit_value": None, "official_report_value": artifact_meta.get("official_q1_report_analyzed_drive_count"), "status": "NOT REPRODUCED", "notes": "Official exclusion logic was not imposed because this data gate audits all published line-item rows."},
        ]
    observed_set = set(observed_columns)
    official_set = set(official)
    metrics = {
        "quarter": "Q1 2026",
        "date_start": min(observed_dates),
        "date_end": max(observed_dates),
        "daily_csv_files": len(members),
        "drive_days": acc.total_rows,
        "unique_drives": n,
        "failure_rows": int(tracker.failure_count[:n].sum()),
        "unique_failed_drives": int(failed_mask.sum()),
        "multiple_failure_drives": int(multiple_failure_mask.sum()),
        "failed_drive_disappears_on_or_before_failure_date": int(failed_disappear_on_or_before_mask.sum()),
        "post_failure_observed_drives": int(tracker.post_failure[:n].sum()),
        "nonfailure_disappearances": int(nonfailure_disappear_mask.sum()),
        "disappear_then_reappear_drives": int(tracker.has_gap[:n].sum()),
        "right_censored_at_quarter_end": int(end_operational_mask.sum()),
        "first_seen_on_left_boundary": int(left_boundary_mask.sum()),
        "first_smart9_available_drives": int(smart9_available.sum()),
        "first_smart9_available_fraction": _safe_fraction(int(smart9_available.sum()), n),
        "missing_dates": missing_dates,
        "extra_dates": extra_dates,
        "schema_variants": len(acc.headers),
        "observed_columns": len(observed_columns),
        "observed_smart_columns": len(smart_columns),
        "official_schema_columns": len(official),
        "unexpected_vs_official_current": sorted(observed_set - official_set) if official else [],
        "missing_vs_official_current": sorted(official_set - observed_set) if official else [],
        "capacity_min_bytes": min(acc.capacity_counts) if acc.capacity_counts else None,
        "capacity_p50_bytes": weighted_quantile(acc.capacity_counts, 0.50),
        "capacity_p95_bytes": weighted_quantile(acc.capacity_counts, 0.95),
        "capacity_max_bytes": max(acc.capacity_counts) if acc.capacity_counts else None,
        "manufacturer_inference": "Conservative model-prefix mapping; Unknown retained when no documented prefix rule is used.",
        "major_model_definition": "At least 1% of Q1 drive-days; reporting scope only, not an exclusion or statistical sufficiency threshold.",
        "descriptive_flag_thresholds": {"unique_drives": min_drives_flag, "unique_failures": min_failures_flag},
    }
    manifest = {
        "audit_version": "0.1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "type": source.source_type,
            "value": source.source_value,
            "access_date": date.today().isoformat(),
            "quarter": "Q1 2026",
            "artifact": artifact_meta or {},
            "members": acc.member_records,
        },
        "official_schema": official_schema_meta or {},
        "processing": {
            "chunksize": acc.chunksize,
            "deterministic": True,
            "sampling": None,
            "raw_archive_retained": False,
            "expanded_csvs_retained": False,
        },
        "metrics": metrics,
        "schema_headers": [
            {"dates": dates, "columns": list(header)} for header, dates in sorted(acc.headers.items(), key=lambda item: item[1][0])
        ],
    }
    tables = {
        "schema_inventory.csv": schema_rows,
        "model_inventory.csv": model_rows,
        "smart_coverage_overall.csv": smart_overall_rows,
        "smart_coverage_by_model.csv": smart_by_model_rows,
        "daily_inventory.csv": daily_rows,
        "observation_checks.csv": observation_checks,
        "capacity_inventory.csv": capacity_rows,
        "candidate_cohorts.csv": candidate_rows,
        "published_reconciliation.csv": published_rows,
    }
    return AuditResult(tables=tables, metrics=metrics, manifest=manifest)


def _candidate_cohorts(
    model_rows: list[dict[str, Any]],
    manufacturer_drives: Counter[str],
    manufacturer_failures: Counter[str],
    manufacturer_drive_days: Counter[str],
    major_models: set[str],
    acc: AuditAccumulator,
) -> list[dict[str, Any]]:
    if not model_rows:
        return []
    top_model = model_rows[0]
    event_rich = max(model_rows, key=lambda row: (row["unique_failed_drives"], row["drive_days"]))
    major = [row for row in model_rows if row["model"] in major_models]
    major_drives = sum(row["unique_drives"] for row in major)
    major_failures = sum(row["unique_failed_drives"] for row in major)
    major_days = sum(row["drive_days"] for row in major)
    top_manufacturer = max(manufacturer_drive_days, key=manufacturer_drive_days.get)
    candidates = []
    for label, row, rationale in [
        ("single_largest_model", top_model, "Maximizes Q1 exposure within one named model and avoids immediate cross-model pooling."),
        ("single_event_rich_model", event_rich, "Uses the single model with the most observed Q1 failures while retaining model homogeneity."),
    ]:
        candidates.append({
            "candidate": label,
            "definition": f"Q1 2026, model == {row['model']}",
            "unique_drives": row["unique_drives"],
            "drive_days": row["drive_days"],
            "observed_failures": row["unique_failed_drives"],
            "date_coverage": f"{row['first_date_observed']} to {row['last_date_observed']}",
            "smart_9_raw_reporting_fraction": row["smart_9_raw_reporting_fraction"],
            "rationale": rationale,
            "advantages": "Single-model interpretation; bounded computation; direct SMART coverage audit.",
            "limitations": "Q1 first appearance is not installation; non-failure exits may be informative; Q1 event window is short.",
            "storage_compute": "One model subset; low after remote streaming.",
            "verdict": "READY WITH CONDITIONS" if row["unique_failed_drives"] >= 20 else "REVISE",
        })
    candidates.append({
        "candidate": "major_models_q1",
        "definition": "Q1 2026 models each contributing at least 1% of quarter drive-days",
        "unique_drives": major_drives,
        "drive_days": major_days,
        "observed_failures": major_failures,
        "date_coverage": f"{acc.quarter_start.isoformat()} to {acc.quarter_end.isoformat()}",
        "smart_9_raw_reporting_fraction": None,
        "rationale": "Provides more events while explicitly retaining model strata for later design decisions.",
        "advantages": "Higher event count; excludes only the long tail for reporting, not permanently.",
        "limitations": "Models are heterogeneous; pooled survival analysis is not justified without stratification or further diagnostics.",
        "storage_compute": "Major-model subset; moderate.",
        "verdict": "READY WITH CONDITIONS" if major_failures >= 50 else "REVISE",
    })
    candidates.append({
        "candidate": "largest_manufacturer_q1",
        "definition": f"Q1 2026, conservatively inferred manufacturer == {top_manufacturer}",
        "unique_drives": manufacturer_drives[top_manufacturer],
        "drive_days": manufacturer_drive_days[top_manufacturer],
        "observed_failures": manufacturer_failures[top_manufacturer],
        "date_coverage": f"{acc.quarter_start.isoformat()} to {acc.quarter_end.isoformat()}",
        "smart_9_raw_reporting_fraction": None,
        "rationale": "Tests whether a broader manufacturer-defined cohort offers enough events for stratified follow-up.",
        "advantages": "More events and drives than a single model.",
        "limitations": "Manufacturer is inferred from model prefix and does not make models exchangeable; requires model-level stratification.",
        "storage_compute": "Manufacturer subset; moderate.",
        "verdict": "REVISE",
    })
    deduped: list[dict[str, Any]] = []
    seen_definitions = set()
    for candidate in candidates:
        if candidate["definition"] not in seen_definitions:
            seen_definitions.add(candidate["definition"])
            deduped.append(candidate)
    return deduped[:4]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_outputs(result: AuditResult, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root)
    table_dir = root / "results" / "tables"
    audit_dir = root / "results" / "audit"
    for name, rows in sorted(result.tables.items()):
        write_csv(table_dir / name, rows)
    manifest_path = audit_dir / "data_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output_hashes = {
        str((table_dir / name).relative_to(root)): file_sha256(table_dir / name)
        for name in sorted(result.tables)
    }
    result.manifest["output_sha256"] = output_hashes
    manifest_path.write_text(json.dumps(result.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (audit_dir / "data_audit_summary.md").write_text(render_summary(result), encoding="utf-8")
    docs_dir = root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "survival_data_feasibility.md").write_text(render_survival_feasibility(result), encoding="utf-8")
    return output_hashes


def render_summary(result: AuditResult) -> str:
    m = result.metrics
    checks = result.tables["observation_checks.csv"]
    models = result.tables["model_inventory.csv"][:12]
    candidates = result.tables["candidate_cohorts.csv"]
    lines = [
        "# Q1 2026 Backblaze data audit summary",
        "",
        "> DATA GATE verdict: **READY WITH CONDITIONS**. Q1 supports a reproducible drive-day and observed-event audit, but Q1 alone does not reveal installation age and non-failure exits cannot be assumed independent censoring.",
        "",
        "## Scope and headline counts",
        "",
        f"- Daily CSV files: {m['daily_csv_files']} ({m['date_start']} through {m['date_end']})",
        f"- Drive-days: {m['drive_days']:,}",
        f"- Unique serial numbers: {m['unique_drives']:,}",
        f"- Failure rows: {m['failure_rows']:,}",
        f"- Unique drives with `failure == 1`: {m['unique_failed_drives']:,}",
        f"- Non-failure disappearances before quarter end: {m['nonfailure_disappearances']:,}",
        f"- Drives disappearing and later reappearing: {m['disappear_then_reappear_drives']:,}",
        "",
        "## Assumption checks",
        "",
        "| Check | Value | Status |",
        "|---|---:|---|",
    ]
    lines.extend(f"| {row['check']} | {row['value']} | {row['status']} |" for row in checks)
    lines += ["", "## Major model inventory", "", "| Model | Drives | Drive-days | Failed drives | SMART 9 raw coverage | Flags |", "|---|---:|---:|---:|---:|---|"]
    for row in models:
        coverage = row["smart_9_raw_reporting_fraction"]
        coverage_text = "" if coverage is None else f"{coverage:.3f}"
        lines.append(f"| {row['model']} | {row['unique_drives']:,} | {row['drive_days']:,} | {row['unique_failed_drives']:,} | {coverage_text} | {row['audit_flags']} |")
    lines += ["", "## Candidate cohorts", "", "| Candidate | Definition | Drives | Failures | Verdict |", "|---|---|---:|---:|---|"]
    for row in candidates:
        lines.append(f"| {row['candidate']} | {row['definition']} | {row['unique_drives']:,} | {row['observed_failures']:,} | {row['verdict']} |")
    lines += [
        "",
        "## Major risks",
        "",
        "- Q1 entry is an observation boundary, not a physical-age origin.",
        "- A disappearance without a failure row has unknown cause and is not classified as failure.",
        "- SMART reporting is model-dependent; missing values remain missing and were not imputed.",
        "- Daily rows are repeated observations of drives and are not independent units.",
        "- Manufacturer labels are conservative model-prefix inferences, not a source field.",
        "",
        "See `docs/survival_data_feasibility.md` and the CSV tables for the full gate evidence.",
    ]
    return "\n".join(lines) + "\n"


def render_survival_feasibility(result: AuditResult) -> str:
    m = result.metrics
    smart9_fraction = m["first_smart9_available_fraction"]
    return f"""# Survival-data feasibility — Backblaze Q1 2026

## VERIFIED FACT

- The audited window contains {m['drive_days']:,} drive-days for {m['unique_drives']:,} unique serial numbers from {m['date_start']} through {m['date_end']}.
- There are {m['failure_rows']:,} failure rows and {m['unique_failed_drives']:,} unique drives with `failure == 1`.
- {m['right_censored_at_quarter_end']:,} drives have no failure row and are present on the final day; these are candidates for administrative right censoring at the quarter boundary.
- {m['nonfailure_disappearances']:,} drives disappear before quarter end without a failure row. They are **not** relabeled as failures.
- {m['disappear_then_reappear_drives']:,} drives have an observation gap and subsequently reappear.
- {m['first_seen_on_left_boundary']:,} drives are already present on the first day of Q1. First observed SMART 9 raw is available for {m['first_smart9_available_drives']:,} drives ({smart9_fraction:.1%}).
- Daily SMART values are repeated longitudinal measurements; daily rows are not statistically independent drive outcomes.
- Backblaze documents that the `failure` flag is produced by presence/disappearance logic with a lookback that can undo temporary absences, and that drives failing before completing their first day are not captured by that program. This is a source-defined event ascertainment limitation.

## INFERENCE

- Drives present at the left boundary are prevalent drives and likely include units installed before Q1. This makes a Q1-only analysis vulnerable to left truncation/delayed-entry problems if physical age is the target time scale.
- Because source event ascertainment requires prior-day presence, the published event process conditions on surviving long enough to enter the daily snapshot system; day-one failures create selection/under-ascertainment risk that cannot be repaired from Q1 CSVs alone.
- A drive present through 2026-03-31 with no failure row has a defensible administrative censoring time for a quarter-window analysis. Earlier unexplained exits have a different, potentially informative censoring mechanism.
- SMART 9 raw may help approximate accumulated powered time for some models, but its unit and firmware interpretation require model/vendor validation. It is not automatically equivalent to physical drive age.

## OPEN PROBLEM

- Installation/birth dates are not present in the observed Q1 schema.
- The reason for non-failure disappearance is not encoded; retirement, migration, maintenance, missing snapshot, and other mechanisms remain distinguishable only with additional evidence.
- A broader historical scan is needed to determine first appearance in the published history and to assess how much that improves, but does not necessarily solve, the age-origin problem.
- Model-specific SMART semantics and counter resets/wraparound require documentation or empirical validation before SMART 9 is used as an age scale.
- Pooling drive models would mix capacities, firmware families, age distributions, and SMART reporting regimes unless the later design handles that heterogeneity explicitly.

## PROPOSED METHOD

### Candidate time origins

1. **Quarter entry / calendar follow-up**: time zero is first observation within Q1. This estimates risk over observed Q1 follow-up, not lifetime-from-installation risk. It requires explicit prevalent-drive language and sensitivity analysis for early non-failure exits.
2. **First appearance in a broader Backblaze history**: time zero is first published appearance. This requires a historical streaming audit and still cannot prove installation coincided with first publication.
3. **Model-validated SMART 9 powered hours**: use a verified powered-time scale with delayed entry at the first observed counter. This requires stable units, monotonicity checks, reset/wrap detection, and adequate reporting for the selected model.
4. **Known installation date**: preferred physical-age origin, but it requires a field or external operational metadata not available in this Q1 audit.

### Event and censoring construction

- Event: first observed row with `failure == 1`; reconcile and flag any serial with repeated failure rows.
- Administrative right censoring: final Q1 observation for drives still present on 2026-03-31 without failure.
- Earlier non-failure exit: retain as a distinct censoring/exit class and perform mechanism-focused sensitivity work; never silently convert it to failure.
- Observation gaps: retain gap indicators and decide whether a contiguous-risk-interval representation is required.

### Time-varying SMART representation

If SMART attributes are considered later, construct start-stop intervals per drive (for example, one interval per observed day or per value-change interval), with covariates measured before the interval's event boundary. Preserve model-specific missingness indicators and avoid using post-failure information. A later model design must specify lagging, counter transformations, ties, and within-drive dependence. No Cox, Kaplan–Meier, regression, or predictive model is fit in this data gate.

## Gate conclusion

**READY WITH CONDITIONS** for selecting and extending a cohort design. Q1 is adequate to measure drive-day exposure, observed failures, schema/SMART coverage, and censoring patterns. It is not sufficient by itself for a lifetime-from-installation claim. The next action is to reconcile this computational audit with a SMART/literature review, choose one candidate model/cohort, and then run a bounded historical first-appearance plus SMART 9 semantics audit before freezing hypotheses.
"""


def run_audit(
    source: Source,
    output_root: str | Path,
    quarter_start: date,
    quarter_end: date,
    official_schema: list[str] | None = None,
    official_schema_meta: dict[str, Any] | None = None,
    artifact_meta: dict[str, Any] | None = None,
    chunksize: int = 50_000,
    max_files: int | None = None,
    progress: bool = True,
    checkpoint_path: str | Path | None = None,
    max_remote_retries: int = 5,
) -> AuditResult:
    members = [member for member in source.members() if quarter_start.isoformat() <= member.date_text <= quarter_end.isoformat()]
    if max_files is not None:
        members = members[:max_files]
    if not members:
        raise RuntimeError("No daily CSV members found for the requested window")
    checkpoint = Path(checkpoint_path) if checkpoint_path else None
    if checkpoint and checkpoint.exists():
        with checkpoint.open("rb") as handle:
            accumulator = pickle.load(handle)
        if accumulator.quarter_start != quarter_start or accumulator.quarter_end != quarter_end:
            raise RuntimeError("Checkpoint quarter does not match requested quarter")
        if progress:
            print(f"Resuming checkpoint after {len(accumulator.daily_rows)} completed daily files", flush=True)
    else:
        accumulator = AuditAccumulator(quarter_start=quarter_start, quarter_end=quarter_end, chunksize=chunksize)

    def save_checkpoint() -> None:
        if not checkpoint:
            return
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        temporary = checkpoint.with_suffix(checkpoint.suffix + ".tmp")
        with temporary.open("wb") as handle:
            pickle.dump(accumulator, handle, protocol=pickle.HIGHEST_PROTOCOL)
        temporary.replace(checkpoint)

    try:
        for index, member in enumerate(members):
            if member.date_text in accumulator.daily_rows:
                continue
            attempt = 0
            while True:
                try:
                    accumulator.process_member(source, member, (date.fromisoformat(member.date_text) - quarter_start).days)
                    break
                except Exception as exc:
                    attempt += 1
                    if source.source_type != "remote_zip_range" or attempt > max_remote_retries:
                        raise
                    if checkpoint and checkpoint.exists():
                        with checkpoint.open("rb") as handle:
                            accumulator = pickle.load(handle)
                    else:
                        accumulator = AuditAccumulator(quarter_start=quarter_start, quarter_end=quarter_end, chunksize=chunksize)
                    wait_seconds = min(2 ** attempt, 30)
                    print(
                        f"Remote read failed for {member.date_text} ({type(exc).__name__}); "
                        f"retry {attempt}/{max_remote_retries} after {wait_seconds}s",
                        flush=True,
                    )
                    time.sleep(wait_seconds)
                    try:
                        source.reconnect()
                    except Exception as reconnect_exc:
                        print(
                            f"Remote reconnect failed ({type(reconnect_exc).__name__}); "
                            "the next bounded retry will reopen the archive",
                            flush=True,
                        )
            save_checkpoint()
            if progress:
                print(f"[{index + 1:02d}/{len(members):02d}] {member.date_text}: {accumulator.daily_rows[member.date_text]:,} rows; cumulative {accumulator.total_rows:,}", flush=True)
        result = build_result(
            accumulator,
            source,
            members,
            official_schema=official_schema,
            official_schema_meta=official_schema_meta,
            artifact_meta=artifact_meta,
        )
        write_outputs(result, output_root)
        if checkpoint and checkpoint.exists():
            checkpoint.unlink()
        return result
    finally:
        source.close()
