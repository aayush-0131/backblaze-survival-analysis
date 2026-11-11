"""Bounded forward linkage of Q1 unexplained exits into later daily files. No estimators.

Asks one descriptive question: does a serial that was an *unexplained exit* in
the verified Q1 cohort appear again in a short, complete run of later daily
files (by default 2026-04-01..2026-04-14)?

Deliberately limited:

* It never edits the Q1 cohort, its outcome classes, censoring dates or failure
  dates. Results go to separate files.
* A reappearance is the *verified* observation of a row with the same serial.
  A serial not seen by the horizon is **unresolved**, never "retired" or
  "failed": a longer gap, retirement, an unflagged failure or a relabelled
  serial are indistinguishable here.
* Matching is by serial across *all* model labels, so a relabelled drive is
  found and flagged rather than missed. Failure flags seen after the window are
  counted descriptively and never become Q1 events.
* Nothing is reported by baseline SMART group.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
import io
import json

import pandas as pd

from .cohort_summary import load_verified
from .history import CORE, HashReader, digest, numeric, write_table
from .sources import Source

LINK_START, LINK_END = date(2026, 4, 1), date(2026, 4, 14)
# Descriptive split already used in docs/q1_cohort_feasibility.md: exits absent
# only on the last 1-3 days of the window versus earlier ("deep") exits.
NEAR_END_MAX_UNOBSERVED_DAYS = 3


def exit_targets(drives: pd.DataFrame) -> dict[str, dict]:
    """Included Q1 unexplained exits, keyed by serial, with their descriptive exit group."""
    exits = drives[(drives["inclusion"] == "included") & (drives["outcome"] == "unexplained_exit")]
    if exits["serial_number"].duplicated().any():
        raise ValueError("Duplicate serial among Q1 exits")
    return {str(r.serial_number): dict(
                last_observed=date.fromisoformat(str(r.last_observed_date)),
                exit_group=("near_end" if int(r.days_unobserved_before_window_end) <= NEAR_END_MAX_UNOBSERVED_DAYS
                            else "earlier"))
            for r in exits.itertuples()}


class ExitLinkage:
    """Scan complete later daily files for the target serials only."""

    def __init__(self, targets: dict[str, dict], model: str, start: date = LINK_START, end: date = LINK_END):
        if end < start:
            raise ValueError("Linkage window end precedes start")
        if any(t["last_observed"] >= start for t in targets.values()):
            raise ValueError("Linkage window must start after every exit's last observed date")
        self.targets, self.model, self.start, self.end = targets, model, start, end
        self.dates: set[date] = set()
        self.seen = defaultdict(list)          # serial -> [observed dates]
        self.labels = defaultdict(set)         # serial -> {raw model labels}
        self.failures = defaultdict(list)      # serial -> [failure-flag dates]
        self.day_rows = Counter()
        self.day_model_rows = Counter()
        self.duplicate_keys = Counter()

    def ingest(self, frame: pd.DataFrame, expected_date: date, all_rows: int | None = None,
               model_rows: int | None = None, duplicate_keys: int = 0):
        """``frame`` holds the day's rows for target serials (any model label)."""
        if not self.start <= expected_date <= self.end:
            raise ValueError("Source date outside the linkage window")
        if expected_date in self.dates:
            raise ValueError("Duplicate source date")
        if (frame["date"].astype(str) != expected_date.isoformat()).any():
            raise ValueError("Source filename/date mismatch")
        serials = frame["serial_number"].astype(str)
        if serials.duplicated().any():
            raise ValueError("Duplicate target serial within one daily file")
        unknown = set(serials) - set(self.targets)
        if unknown:
            raise ValueError("Non-target serial passed to linkage")
        self.dates.add(expected_date)
        self.day_rows[expected_date] = len(frame) if all_rows is None else all_rows
        self.day_model_rows[expected_date] = model_rows or 0
        self.duplicate_keys[expected_date] = duplicate_keys
        for serial, label, failure in zip(serials, frame["model"].astype(str), frame["failure"]):
            flag = numeric(failure)
            if flag not in (0, 1):
                raise ValueError("Invalid failure flag for a linked serial")
            self.seen[serial].append(expected_date)
            self.labels[serial].add(label)
            if flag:
                self.failures[serial].append(expected_date)

    def complete(self) -> bool:
        return self.dates == {self.start + timedelta(days=i) for i in range((self.end - self.start).days + 1)}

    def records(self) -> list[dict]:
        if not self.complete():
            raise ValueError("Incomplete linkage calendar; non-observation cannot be assessed")
        rows = []
        for serial, t in sorted(self.targets.items()):
            seen = sorted(self.seen.get(serial, []))
            first = seen[0] if seen else None
            rows.append(dict(
                serial_number=serial, exit_group=t["exit_group"], q1_last_observed_date=t["last_observed"],
                linkage_window=f"{self.start}..{self.end}",
                linkage_status="reappeared_verified" if first else "not_observed_through_window_end",
                first_reappearance_date=first,
                days_absent_before_reappearance=(first - t["last_observed"]).days - 1 if first else None,
                days_observed_in_window=len(seen), observed_on_window_end=self.end in seen,
                model_labels_in_window="|".join(sorted(self.labels.get(serial, ()))),
                model_label_differs=bool(self.labels.get(serial)) and self.labels[serial] != {self.model},
                failure_flags_in_window=len(self.failures.get(serial, [])),
                first_failure_flag_in_window=min(self.failures[serial]) if self.failures.get(serial) else None,
            ))
        return rows


def linkage_summary(records: list[dict]) -> dict:
    """Aggregate counts only; no serials and no baseline-group breakdown."""
    def block(rows):
        back = [r for r in rows if r["linkage_status"] == "reappeared_verified"]
        out = dict(exits=len(rows), reappeared_verified=len(back),
                   not_observed_through_window_end=len(rows) - len(back),
                   first_reappearance_by_date=dict(sorted(Counter(str(r["first_reappearance_date"]) for r in back).items())),
                   reappeared_and_observed_on_window_end=sum(r["observed_on_window_end"] for r in back),
                   reappeared_with_different_model_label=sum(r["model_label_differs"] for r in back),
                   reappeared_with_failure_flag_in_window=sum(r["failure_flags_in_window"] > 0 for r in back))
        if out["reappeared_verified"] + out["not_observed_through_window_end"] != out["exits"]:
            raise ValueError("Linkage counts do not reconcile")
        return out
    days = Counter(r["days_absent_before_reappearance"] for r in records if r["days_absent_before_reappearance"] is not None)
    return dict(all_exits=block(records),
                by_exit_group={g: block([r for r in records if r["exit_group"] == g]) for g in ("near_end", "earlier")},
                days_absent_before_reappearance=dict(sorted(days.items())),
                interpretation=("reappeared_verified = a row with the same serial exists in the window; "
                                "not_observed_through_window_end = status unresolved (longer gap, retirement, "
                                "unflagged failure or relabelled serial cannot be distinguished)."))


def run_linkage(source: Source, cohort_dir: Path, output_dir: Path, start: date = LINK_START,
                end: date = LINK_END, chunksize: int = 100_000) -> dict:
    """Read only the daily members in [start, end] and link the verified Q1 exits.

    Each member's decompressed bytes are counted and hashed. With ZIP sources the
    standard library also verifies the member CRC32 at end of stream. Serial-level
    output stays in ``output_dir``; the return value is aggregate only.
    """
    drives, cohort_manifest = load_verified(cohort_dir)
    targets = exit_targets(drives)
    model = cohort_manifest["model"]
    members = [m for m in source.members()
               if start <= date.fromisoformat(m.date_text) <= end and not m.name.startswith("__MACOSX/")]
    dates = sorted(date.fromisoformat(m.date_text) for m in members)
    if dates != [start + timedelta(days=i) for i in range((end - start).days + 1)]:
        raise ValueError("Incomplete or overlapping linkage calendar")
    link = ExitLinkage(targets, model, start, end)
    evidence = []
    for member in sorted(members, key=lambda m: m.date_text):
        day = date.fromisoformat(member.date_text)
        parts, rows, model_rows, keys, header = [], 0, 0, set(), None
        duplicates = 0
        with source.open(member) as handle:
            hashed = HashReader(handle)
            counted = _CountingReader(hashed)
            with io.BufferedReader(counted) as buffered:
                for chunk in pd.read_csv(buffered, usecols=lambda c: c in CORE, chunksize=chunksize,
                                         encoding="utf-8-sig", low_memory=False,
                                         dtype={"serial_number": "string", "model": "string", "date": "string"}):
                    if not set(CORE) <= set(chunk.columns):
                        raise ValueError(f"Missing core columns in {member.name}")
                    if (chunk["date"] != day.isoformat()).any():
                        raise ValueError(f"Source filename/date mismatch in {member.name}")
                    rows += len(chunk)
                    model_rows += int((chunk["model"] == model).sum())
                    serials = chunk["serial_number"].astype(str)
                    before = len(keys)
                    keys.update(serials)
                    duplicates += len(serials) - (len(keys) - before)
                    parts.append(chunk[serials.isin(targets)])
            sha = hashed.hash.hexdigest()
        if member.uncompressed_size is not None and counted.bytes != member.uncompressed_size:
            raise ValueError(f"{member.name}: decompressed {counted.bytes} bytes, directory says {member.uncompressed_size}")
        selected = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=list(CORE))
        link.ingest(selected, day, all_rows=rows, model_rows=model_rows, duplicate_keys=duplicates)
        evidence.append(dict(date=day.isoformat(), member=member.name, crc32=member.crc32,
                             compressed_size=member.compressed_size, uncompressed_size=member.uncompressed_size,
                             decompressed_bytes=counted.bytes, sha256=sha, rows=rows,
                             cohort_model_rows=model_rows, duplicate_serial_keys=duplicates,
                             target_rows=len(selected)))
    records = link.records()
    output_dir = Path(output_dir)
    write_table(output_dir / "exit_linkage_drives.csv", records)
    summary = dict(
        model=model, linkage_window=dict(start=start.isoformat(), end=end.isoformat(), daily_members=len(evidence)),
        q1_cohort_output_sha256=cohort_manifest["output_sha256"], q1_exit_targets=len(targets),
        source_type=source.source_type,
        source=(source.source_value if source.source_type == "remote_zip_range" else Path(source.source_value).name),
        member_evidence=evidence, compressed_bytes_of_members_read=sum(e["compressed_size"] or 0 for e in evidence),
        models_fitted="none", q1_cohort_modified=False, baseline_group_breakdown="not computed",
        **linkage_summary(records),
        serial_level_output_sha256=digest(output_dir / "exit_linkage_drives.csv"))
    return summary


class _CountingReader(io.RawIOBase):
    def __init__(self, stream):
        self.stream, self.bytes = stream, 0

    def readable(self):
        return True

    def readinto(self, buffer):
        n = self.stream.readinto(buffer)
        self.bytes += n or 0
        return n
