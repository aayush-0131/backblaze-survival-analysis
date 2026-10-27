"""Descriptive, exact, bounded historical audit. No inferential estimators.

Input archives stay compressed; only selected columns in candidate rows are held.
All serial dates are observation dates, never installation dates.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
import csv
import hashlib
import io
import json
import math
import pickle
import zipfile

import pandas as pd

MODELS = ("ST12000NM0008", "WDC WUH722222ALE6L4")
# Only verified exact labels are accepted by default. A prospective prefix variant
# is reported separately; a supplied explicit map is needed to combine it.
ALIASES = {m: m for m in MODELS}
PROSPECTIVE_ALIAS = "WUH722222ALE6L4"
CORE = ("date", "serial_number", "model", "capacity_bytes", "failure")
SMART = ("smart_9_raw", "smart_197_raw", "smart_5_raw")
Q1_START, Q1_END = date(2026, 1, 1), date(2026, 3, 31)


def digest(path: Path, algorithm="sha256") -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def quantile(counts: Counter, q: float):
    """Exact inverse empirical CDF (nearest rank); no sampling/interpolation."""
    n = sum(counts.values())
    if not n:
        return None
    rank, cum = max(1, math.ceil(q * n)), 0
    for value, count in sorted(counts.items()):
        cum += count
        if cum >= rank:
            return value


def pair_flags(previous: int, current: int, days: int) -> dict:
    if days <= 0:
        raise ValueError("SMART pair must move forward in calendar time")
    delta, hours = current - previous, days * 24
    # A two-hour tolerance addresses integer rounding and unknown snapshot times.
    # The 48-hour screen is a review flag, not proof of physical impossibility.
    return dict(delta=delta, elapsed_hours=hours, rate=delta / hours,
                increase=delta > 0, unchanged=delta == 0, decrease=delta < 0,
                reset_candidate=delta < 0 and current <= 24 and previous > 48,
                excess_48h=delta > hours + 48,
                calendar_like=abs(delta - hours) <= 2,
                gap=days > 1,
                gap_class=("decrease" if delta < 0 else
                           "calendar_like" if abs(delta - hours) <= 2 else
                           "unchanged" if delta == 0 else
                           "partial_powered_time" if 0 < delta < hours - 2 else
                           "excess_or_ambiguous"))


def numeric(value):
    if pd.isna(value) or value == "":
        return None
    x = float(value)
    if not math.isfinite(x) or x < 0 or x != int(x):
        raise ValueError(f"Invalid nonnegative integer telemetry: {value!r}")
    return int(x)


def write_table(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class HashReader(io.RawIOBase):
    def __init__(self, stream):
        self.stream, self.hash = stream, hashlib.sha256()

    def readable(self):
        return True

    def readinto(self, buffer):
        data = self.stream.read(len(buffer))
        self.hash.update(data)
        buffer[:len(data)] = data
        return len(data)


class HistoryAudit:
    def __init__(self, baseline: date, window_end: date, aliases=None):
        self.baseline, self.end = baseline, window_end
        self.aliases = dict(ALIASES if aliases is None else aliases)
        if any(v not in MODELS for v in self.aliases.values()):
            raise ValueError("Alias mapping must target a requested model")
        self.drives = {}
        self.raw_labels = defaultdict(lambda: dict(days=0, serials=set(), dates=set(), failures=0))
        self.hist = defaultdict(Counter)
        self.counts = defaultdict(Counter)
        self.gaps = defaultdict(Counter)
        self.anomalies = []
        self.dates = set()
        self.members = []

    def ingest(self, frame: pd.DataFrame, expected_date: date):
        if expected_date in self.dates:
            raise ValueError("Duplicate source date")
        self.dates.add(expected_date)
        for row in frame.sort_values(["serial_number", "model"]).to_dict("records"):
            raw = row["model"]
            if raw not in self.aliases:
                if raw == PROSPECTIVE_ALIAS:
                    raise ValueError("Unapproved model prefix alias encountered; inspect and map explicitly")
                continue
            model, serial = self.aliases[raw], str(row["serial_number"])
            if pd.isna(row["serial_number"]) or not serial:
                raise ValueError("Missing candidate serial")
            day = date.fromisoformat(str(row["date"]))
            if day != expected_date:
                raise ValueError("Source filename/date mismatch")
            capacity = None if pd.isna(row["capacity_bytes"]) else float(row["capacity_bytes"])
            if capacity is not None and (not math.isfinite(capacity) or capacity != int(capacity)):
                raise ValueError("Nonintegral/nonfinite capacity")
            capacity = None if capacity is None else int(capacity)
            failure = numeric(row["failure"])
            if failure not in (0, 1):
                raise ValueError("Invalid candidate failure")
            smart = {c: numeric(row.get(c)) for c in SMART}
            labels = self.raw_labels[raw]
            labels["days"] += 1
            labels["serials"].add(serial)
            labels["dates"].add(day)
            labels["failures"] += failure
            stats = self.counts[model]
            stats["invalid_capacity_rows"] += capacity is None or capacity <= 0
            stats["drive_days"] += 1
            stats["failure_rows"] += failure
            key = serial
            d = self.drives.get(key)
            if d is None:
                d = dict(model=model, raw_labels=set(), first=day, last=day,
                         capacity=capacity, rows=0, failures=[], gaps=0,
                         anomaly=False, inconsistent_capacity=False,
                         first_smart=smart.copy(), last_smart={}, baseline=None, baseline_capacity=None,
                         first_q1=None, last_q1=None, q1_rows=0)
                self.drives[key] = d
            elif d["model"] != model:
                raise ValueError("Serial crosses canonical candidate models")
            elif day <= d["last"]:
                raise ValueError("Duplicate or unordered serial/date")
            d["raw_labels"].add(raw)
            d["inconsistent_capacity"] |= capacity != d["capacity"]
            if d["failures"] and day > d["failures"][0]:
                stats["post_failure_rows"] += 1
            days = (day - d["last"]).days if d["rows"] else None
            if days and days > 1:
                d["gaps"] += 1
                self.gaps[model][days - 1] += 1
                stats["gap_pairs"] += 1
            for column, value in smart.items():
                stats[column + "_missing"] += value is None
                if value is not None:
                    self.hist[(model, column)][value] += 1
                previous = d["last_smart"].get(column)
                if days is not None:
                    if previous is None or value is None:
                        stats[column + "_missing_pairs"] += 1
                    elif column == "smart_9_raw":
                        flags = pair_flags(previous, value, days)
                        stats["smart9_pairs"] += 1
                        for flag in ("increase", "unchanged", "decrease", "reset_candidate", "excess_48h", "calendar_like"):
                            stats[flag] += flags[flag]
                        self.hist[(model, "rate")][flags["rate"]] += 1
                        if days == 1:
                            stats["adjacent_pairs"] += 1
                            self.hist[(model, "adjacent_delta")][flags["delta"]] += 1
                        if days > 1:
                            stats["gap_smart9_pairs"] += 1
                            stats["gap_" + flags["gap_class"]] += 1
                        if flags["decrease"] or flags["excess_48h"]:
                            d["anomaly"] = True
                            self.anomalies.append(dict(model=model, serial_number=serial,
                                previous_date=d["last"], date=day, previous=previous,
                                current=value, delta=flags["delta"], elapsed_hours=flags["elapsed_hours"],
                                reset_candidate=flags["reset_candidate"], excess_48h=flags["excess_48h"]))
                    else:
                        kind = "adjacent" if days == 1 else "gap"
                        stats[column + "_" + kind + "_pairs"] += 1
                        stats[column + "_" + kind + "_state_changes"] += (previous > 0) != (value > 0)
                        stats[column + "_" + kind + "_value_changes"] += previous != value
            d["last"], d["last_smart"] = day, smart
            d["rows"] += 1
            if day == self.baseline:
                d["baseline"] = smart.copy()
                d["baseline_capacity"] = capacity
            if failure:
                d["failures"].append(day)
            if Q1_START <= day <= Q1_END:
                d["first_q1"] = d["first_q1"] or day
                d["last_q1"] = day
                d["q1_rows"] += 1

    def tables(self):
        inventory, consistency, warning, accounting, gap_rows = [], [], [], [], []
        scope = "observed_daily_files_only"
        for model in MODELS:
            ds = [d for d in self.drives.values() if d["model"] == model]
            s = self.counts[model]
            failed = [d for d in ds if d["failures"]]
            times = [t for d in ds for t in d["failures"]]
            inventory.append(dict(model=model, evidence_scope=scope, unique_drives=len(ds),
                drive_days=s["drive_days"], failure_rows=s["failure_rows"], unique_failed_drives=len(failed),
                earliest_observed_backblaze_date=min((d["first"] for d in ds), default=None),
                latest_observed_date=max((d["last"] for d in ds), default=None),
                earliest_failure=min(times, default=None), latest_failure=max(times, default=None),
                historical_census_complete=False, q1_linkage_complete=all(Q1_START + timedelta(days=i) in self.dates for i in range(90)),
                q1_linked_drives=sum(d["q1_rows"] > 0 for d in ds),
                q1_traced_pre_entry=sum(bool(d["q1_rows"]) and d["first"] < Q1_START for d in ds),
                drives_with_repeated_observations=sum(d["rows"] > 1 for d in ds),
                smart9_anomalous_drives=sum(d["anomaly"] for d in ds),
                inconsistent_capacity_drives=sum(d["inconsistent_capacity"] for d in ds),
                invalid_capacity_rows=s["invalid_capacity_rows"],
                post_failure_drives=sum(bool(d["failures"]) and d["last"] > d["failures"][0] for d in ds),
                post_failure_rows=s["post_failure_rows"], repeated_failure_drives=sum(len(d["failures"]) > 1 for d in ds)))
            h = self.hist[(model, "smart_9_raw")]
            n = sum(h.values())
            endpoints = Counter()
            for d in ds:
                first, last = d["first_smart"]["smart_9_raw"], d["last_smart"]["smart_9_raw"]
                if d["last"] > d["first"] and first is not None and last is not None:
                    endpoints[(last-first)/((d["last"]-d["first"]).days*24)] += 1
            consistency.append(dict(model=model, evidence_scope=scope, drive_days=s["drive_days"],
                reported=n, missing=s["smart_9_raw_missing"], coverage=n/s["drive_days"] if s["drive_days"] else None,
                zero_count=h[0], zero_fraction=h[0]/n if n else None,
                min=min(h, default=None), p05=quantile(h,.05), p25=quantile(h,.25), median=quantile(h,.5),
                p75=quantile(h,.75), p95=quantile(h,.95), p99=quantile(h,.99), max=max(h, default=None),
                pairs=s["smart9_pairs"], missing_endpoint_pairs=s["smart_9_raw_missing_pairs"],
                increases=s["increase"], unchanged=s["unchanged"], decreases=s["decrease"],
                reset_candidates=s["reset_candidate"], excess_48h_pairs=s["excess_48h"],
                calendar_like_pairs=s["calendar_like"], calendar_like_fraction=s["calendar_like"]/s["smart9_pairs"] if s["smart9_pairs"] else None,
                ratio_p05=quantile(self.hist[(model,"rate")],.05), ratio_median=quantile(self.hist[(model,"rate")],.5),
                ratio_p95=quantile(self.hist[(model,"rate")],.95), adjacent_pairs=s["adjacent_pairs"],
                adjacent_delta_median=quantile(self.hist[(model,"adjacent_delta")],.5),
                endpoint_drives=sum(endpoints.values()), endpoint_ratio_p05=quantile(endpoints,.05),
                endpoint_ratio_median=quantile(endpoints,.5), endpoint_ratio_p95=quantile(endpoints,.95),
                gap_pairs=s["gap_pairs"], gap_smart9_pairs=s["gap_smart9_pairs"],
                **{"gap_"+k:s["gap_"+k] for k in ("calendar_like","unchanged","partial_powered_time","decrease","excess_or_ambiguous")}))
            for column in ("smart_197_raw", "smart_5_raw"):
                h = self.hist[(model,column)]
                n = sum(h.values())
                for definition in ("fixed_snapshot", "first_observed_snapshot"):
                    eligible = [(d, self.baseline if definition == "fixed_snapshot" else d["first"],
                                 d["baseline"] if definition == "fixed_snapshot" else d["first_smart"]) for d in ds]
                    eligible = [(d,b,v) for d,b,v in eligible if v is not None]
                    same_day = sum(bool(d["failures"]) and d["failures"][0] <= b for d,b,v in eligible)
                    selected = [(d,b,v) for d,b,v in eligible if not d["failures"] or d["failures"][0] > b]
                    row = dict(model=model, evidence_scope=scope, column=column, baseline_definition=definition,
                        baseline_date=self.baseline if definition == "fixed_snapshot" else "drive_first_observation",
                        drive_days=s["drive_days"], reported=n, missing=s["drive_days"]-n,
                        coverage=n/s["drive_days"] if s["drive_days"] else None, zero_rows=h[0], nonzero_rows=n-h[0],
                        nonzero_fraction=(n-h[0])/n if n else None, baseline_drives=len(eligible),
                        excluded_failure_at_or_before_baseline=same_day,
                        **{k:s[column+"_"+k] for k in ("adjacent_pairs","adjacent_state_changes","adjacent_value_changes","gap_pairs","gap_state_changes")})
                    for state in ("zero", "nonzero", "missing"):
                        group = [(d,b) for d,b,v in selected if ("missing" if v[column] is None else "zero" if v[column] == 0 else "nonzero") == state]
                        row[state+"_baseline_drives"] = len(group)
                        row[state+"_subsequent_failure_drives"] = sum(bool(d["failures"]) and b < d["failures"][0] <= self.end for d,b in group)
                    warning.append(row)
                baseline_ds = [d for d in ds if d["baseline"] is not None]
                prefailed = [d for d in baseline_ds if d["failures"] and d["failures"][0] <= self.baseline]
                risk = [d for d in baseline_ds if d not in prefailed]
                for rule in ("all_baseline", "complete_warning", "complete_warning_and_age", "no_gap_sensitivity"):
                    retained = [d for d in risk if rule == "all_baseline" or
                                (d["baseline"][column] is not None and d["baseline_capacity"] is not None and d["baseline_capacity"] > 0 and
                                 (rule == "complete_warning" or d["baseline"]["smart_9_raw"] is not None) and
                                 (rule != "no_gap_sensitivity" or not d["gaps"]))]
                    events = sum(bool(d["failures"]) and self.baseline < d["failures"][0] <= self.end for d in retained)
                    survivors = sum(not d["failures"] and d["last"] >= self.end for d in retained)
                    exits = sum(not d["failures"] and d["last"] < self.end for d in retained)
                    assert events + survivors + exits == len(retained)
                    accounting.append(dict(model=model, evidence_scope=scope, baseline=self.baseline,
                        column=column, rule=rule, drives_present=len(baseline_ds),
                        later_arrivals=sum(d["first"] > self.baseline for d in ds),
                        excluded_failure_at_or_before_baseline=len(prefailed),
                        excluded_by_rule=len(risk)-len(retained), retained=len(retained),
                        subsequent_recorded_failures=events, administrative_survivors=survivors,
                        unexplained_exits_within_observed_window=exits,
                        intermittent_gap_drives=sum(d["gaps"]>0 for d in retained)))
            gaps = self.gaps[model]
            exits = [d for d in ds if not d["failures"] and d["last"] < self.end]
            # Each unique dated post-event record can fill at most one calendar
            # day. If every possible post-event day is filled, no observed gap
            # can be after the first flag: any gap on a failed drive precedes it
            # or ends on that flag date. Otherwise chronology is left unknown.
            post_event_calendar_days = sum((d["last"]-d["failures"][0]).days for d in failed)
            return_order_verified = s["post_failure_rows"] == post_event_calendar_days
            gap_failed = sum(d["gaps"]>0 and bool(d["failures"]) for d in ds)
            gap_rows.append(dict(model=model, evidence_scope=scope,
                intermittent_gap_drives=sum(d["gaps"]>0 for d in ds), gap_episodes=sum(gaps.values()),
                missing_days_min=min(gaps,default=None), missing_days_median=quantile(gaps,.5),
                missing_days_p95=quantile(gaps,.95), missing_days_max=max(gaps,default=None),
                failed_drives_with_any_gap=gap_failed,
                failures_after_return=gap_failed if return_order_verified else None,
                failures_after_return_order_verified=return_order_verified,
                unflagged_exits_before_end=len(exits),
                exits_within_7_days_of_end=sum((self.end-d["last"]).days<=7 for d in exits),
                permanence_verified=False, q1_boundary_linkage_verified=False))
        aliases = [dict(raw_model=raw, canonical_model=self.aliases[raw], drive_days=v["days"],
                        unique_drives=len(v["serials"]), failure_rows=v["failures"],
                        first_date=min(v["dates"]), last_date=max(v["dates"])) for raw,v in sorted(self.raw_labels.items())]
        return {"historical_model_inventory.csv":inventory, "smart9_consistency.csv":consistency,
                "smart_warning_feasibility.csv":warning, "cohort_accounting.csv":accounting,
                "gap_exit_audit.csv":gap_rows, "history_model_aliases.csv":aliases}


def run_history(archives: list[Path], output_root: Path, baseline: date, window_end: date,
                chunksize=50000, provenance=None, checkpoint: Path | None=None):
    audit = HistoryAudit(baseline, window_end)
    sources, members = [], []
    for archive in archives:
        source = dict(path=archive.name, bytes=archive.stat().st_size,
                      sha256=digest(archive), sha1=digest(archive,"sha1"))
        sources.append(source)
        if provenance and len(archives)==1:
            for key, expected_key in (("bytes","content_length_bytes"),("sha256","local_sha256"),("sha1","local_sha1")):
                if expected_key in provenance and source[key] != provenance[expected_key]:
                    raise ValueError("Archive differs from recorded provenance: " + key)
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                from .sources import DAILY_CSV_RE
                match = DAILY_CSV_RE.search(info.filename)
                if match and not info.filename.startswith("__MACOSX/"):
                    members.append((date.fromisoformat(match.group(1)), archive, info))
    members.sort(key=lambda x:x[0])
    dates = [m[0] for m in members]
    if len(dates) != len(set(dates)):
        raise ValueError("Overlapping source dates; refuse double counting")
    if baseline not in dates or window_end not in dates:
        raise ValueError("Baseline and end must be observed source dates")
    # Gaps require a complete observed calendar window. Missing source days must
    # be repaired before interpreting absence of a serial as a drive-level gap.
    if dates != [dates[0]+timedelta(days=i) for i in range((dates[-1]-dates[0]).days+1)]:
        raise ValueError("Incomplete source calendar; cannot classify drive gaps")
    if baseline != dates[0] or window_end != dates[-1]:
        raise ValueError("This audit uses the complete selected window; boundary linkage needs a separate pass")
    identity=dict(version=2, sources=sources, baseline=str(baseline), end=str(window_end))
    if checkpoint and checkpoint.exists():
        # Checkpoints are trusted local pipeline products, never downloaded pickle.
        with checkpoint.open("rb") as f:
            saved=pickle.load(f)
        if saved["identity"] != identity:
            raise ValueError("Checkpoint identity does not match source bytes/window/version")
        audit.__dict__.update(saved["state"])
        audit.raw_labels=defaultdict(lambda:dict(days=0,serials=set(),dates=set(),failures=0),audit.raw_labels)
    for day, archive, info in members:
        if day in audit.dates:
            continue
        candidates = []
        with zipfile.ZipFile(archive) as z:
            with z.open(info) as f:
                header = next(csv.reader(io.TextIOWrapper(f,encoding="utf-8-sig")))
            if len(header) != len(set(header)) or not set(CORE).issubset(header):
                raise ValueError("Missing/duplicate core header")
            with z.open(info) as f:
                hashed = HashReader(f)
                with io.BufferedReader(hashed) as buffered:
                    for frame in pd.read_csv(buffered, usecols=lambda c:c in CORE+SMART,
                                             chunksize=chunksize, low_memory=False,
                                             dtype={"serial_number":"string", "model":"string", "date":"string"}):
                        selected = frame[frame.model.isin(set(audit.aliases)|{PROSPECTIVE_ALIAS})].copy()
                        for column in SMART:
                            if column not in selected:
                                selected[column] = None
                        candidates.append(selected)
                sha = hashed.hash.hexdigest()
        audit.ingest(pd.concat(candidates,ignore_index=True),day)
        audit.members.append(dict(date=day.isoformat(), archive=archive.name, member=info.filename,
            crc32=f"{info.CRC:08x}", sha256=sha, compressed_bytes=info.compress_size,
            uncompressed_bytes=info.file_size, candidate_rows=sum(len(f) for f in candidates),
            header=header, missing_smart_columns=[c for c in SMART if c not in header]))
        print(f"{day}: {audit.members[-1]['candidate_rows']} candidate rows",flush=True)
        if checkpoint:
            checkpoint.parent.mkdir(parents=True,exist_ok=True)
            state=audit.__dict__.copy()
            state["raw_labels"]=dict(audit.raw_labels)
            temporary=checkpoint.with_suffix(".tmp")
            with temporary.open("wb") as f:
                pickle.dump(dict(identity=identity,state=state),f,protocol=5)
            temporary.replace(checkpoint)
    tables = audit.tables()
    for name, rows in tables.items():
        write_table(output_root/"results/tables"/name,rows)
    processed = output_root/"data/processed"
    processed.mkdir(parents=True,exist_ok=True)
    rows = []
    for serial,d in sorted(audit.drives.items()):
        rows.append(dict(serial_number=serial, model=d["model"], raw_models="|".join(sorted(d["raw_labels"])),
            earliest_observed_backblaze_date=d["first"], latest_observed_date=d["last"],
            historical_census_complete=False, observation_span_days=(d["last"]-d["first"]).days,
            observed_drive_days=d["rows"], first_q1_date=d["first_q1"], last_q1_date=d["last_q1"],
            failure_date=d["failures"][0] if d["failures"] else None,
            smart9_anomaly=d["anomaly"], intermittent_gaps=d["gaps"]))
    write_table(processed/"history_drive_summary.csv",rows)
    write_table(processed/"smart9_anomalies.csv",audit.anomalies)
    manifest = dict(pipeline_version=2, baseline=str(baseline), window_end=str(window_end),
        evidence_scope="complete selected daily window; not a full historical census", source_archives=sources,
        provenance=provenance or {}, aliases=audit.aliases, baseline_q1_commit="0f27a5756af568eef2ed6548b251c5e2ac382420",
        days_processed=len(dates), first_source_date=str(min(dates)), last_source_date=str(max(dates)),
        missing_dates=[str(min(dates)+timedelta(days=i)) for i in range((max(dates)-min(dates)).days+1) if min(dates)+timedelta(days=i) not in audit.dates],
        member_evidence=audit.members, chunksize=chunksize, sampling="none; exact counts and nearest-rank quantiles",
        anomaly_rules=dict(reset_candidate="negative delta; current <=24, previous >48",
                           excess_48h="delta > elapsed calendar hours +48",
                           calendar_like="abs(delta - elapsed calendar hours) <=2"),
        output_hashes={name:digest(output_root/"results/tables"/name) for name in tables},
        private_output_hashes={name:digest(processed/name) for name in ("history_drive_summary.csv","smart9_anomalies.csv")})
    path=output_root/"results/audit/history_manifest.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return audit
