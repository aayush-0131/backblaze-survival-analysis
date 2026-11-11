"""Per-drive fixed-baseline cohort construction skeleton. No estimators.

Builds one descriptive record per drive for a single exact candidate model:
baseline inclusion, first recorded failure versus non-failure exit, and
observation-gap flags. It reuses ``HistoryAudit`` for row validation
(binary failure, unique serial/date, filename date, alias guard, SMART 9
pair flags) and the existing ``Source`` readers.

Conventions are deliberately conservative and are *proposals* until the owner
and group approve them:

* Calendar follow-up only. SMART 9 is carried as a raw powered-hours counter
  descriptor; it is never converted to physical or installation age.
* Baseline SMART state comes only from the baseline-date row; later values
  never reclassify baseline. Missing is a separate state, never zero.
* Only ``failure == 1`` is an event. A drive that stops appearing without a
  failure flag is ``unexplained_exit`` -- never a failure.
* A failure flag on the baseline date is excluded from the subsequent-event
  risk set (same convention as ``history.py``).
* Post-failure rows and repeated flags are counted, not dropped or recounted.
* Boundary linkage beyond the window is not attempted here.

Nothing in this module fits Kaplan-Meier, Cox or any other model.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
import io
import json

import pandas as pd

from .history import (CORE, MODELS, PROSPECTIVE_ALIAS, Q1_END, Q1_START, SMART,
                      HashReader, HistoryAudit, digest, write_table)
from .sources import Source

SEAGATE = MODELS[0]
WARNING_COLUMNS = ("smart_197_raw", "smart_5_raw")  # 197 predeclared lead, 5 alternative
OUTCOMES = ("recorded_failure", "administrative_censoring", "unexplained_exit")
INCLUSIONS = ("included", "excluded_later_arrival", "excluded_failure_on_or_before_baseline")


class CohortAudit(HistoryAudit):
    """Single-model ``HistoryAudit`` that also keeps per-drive gap episodes."""

    def __init__(self, model: str, baseline: date, window_end: date):
        if model not in MODELS:
            raise ValueError(f"Cohort must use one exact candidate model from {MODELS}")
        if window_end < baseline:
            raise ValueError("Window end precedes baseline")
        super().__init__(baseline, window_end, aliases={model: model})
        self.model = model
        self.gap_episodes = defaultdict(list)   # serial -> [(last_seen, returned)]
        self.post_failure = defaultdict(int)

    def ingest(self, frame: pd.DataFrame, expected_date: date):
        if not self.baseline <= expected_date <= self.end:
            raise ValueError("Source date outside the cohort window")
        own = frame[frame["model"].isin({self.model, PROSPECTIVE_ALIAS})]
        prior = {}
        for serial in own["serial_number"]:
            key = str(serial)
            if key in self.drives:
                prior[key] = (self.drives[key]["last"], list(self.drives[key]["failures"]))
        super().ingest(own, expected_date)  # validates and raises before we record anything
        for key, (last, failures) in prior.items():
            if (expected_date - last).days > 1:
                self.gap_episodes[key].append((last, expected_date))
            if failures and expected_date > failures[0]:
                self.post_failure[key] += 1


def _require(condition: bool, message: str):
    """Reconciliation guard that, unlike ``assert``, still runs under ``python -O``."""
    if not condition:
        raise ValueError("Cohort accounting does not reconcile: " + message)


def _shareable_source(source: Source) -> str:
    """URL for remote sources; file/directory name only for local ones (no home paths)."""
    if source.source_type == "remote_zip_range":
        return source.source_value
    return Path(source.source_value).name


def _state(value) -> str:
    return "missing" if value is None else "zero" if value == 0 else "nonzero"


def drive_records(audit: CohortAudit) -> list[dict]:
    """One row per observed drive of the cohort model, sorted by serial."""
    expected = {audit.baseline + timedelta(days=i) for i in range((audit.end - audit.baseline).days + 1)}
    if audit.dates != expected:
        raise ValueError("Incomplete source calendar; absences cannot be classified as drive gaps")
    rows = []
    for serial, d in sorted(audit.drives.items()):
        first_failure = d["failures"][0] if d["failures"] else None
        if d["first"] > audit.baseline:
            inclusion = "excluded_later_arrival"
        elif first_failure is not None and first_failure <= audit.baseline:
            inclusion = "excluded_failure_on_or_before_baseline"
        else:
            inclusion = "included"
        if first_failure is not None:
            outcome, outcome_date = "recorded_failure", first_failure
        elif d["last"] >= audit.end:
            outcome, outcome_date = "administrative_censoring", audit.end
        else:
            outcome, outcome_date = "unexplained_exit", d["last"]
        episodes = audit.gap_episodes.get(serial, [])
        lengths = [(back - last).days - 1 for last, back in episodes]
        baseline = d["baseline"] or {}
        rows.append(dict(
            serial_number=serial, model=d["model"], raw_models="|".join(sorted(d["raw_labels"])),
            baseline_date=audit.baseline, window_end=audit.end, inclusion=inclusion,
            first_observed_date=d["first"], last_observed_date=d["last"], observed_drive_days=d["rows"],
            baseline_capacity_bytes=d["baseline_capacity"],
            baseline_capacity_valid=bool(d["baseline_capacity"] and d["baseline_capacity"] > 0),
            **{f"baseline_{c}_state": _state(baseline.get(c)) if d["baseline"] is not None else None
               for c in WARNING_COLUMNS},
            baseline_smart_9_raw_powered_hours_counter=baseline.get("smart_9_raw"),
            smart9_review_flag_in_window=d["anomaly"],
            outcome=outcome, outcome_date=outcome_date,
            followup_days=(outcome_date - audit.baseline).days if inclusion == "included" else None,
            first_failure_date=first_failure,
            repeated_failure_flags=len(d["failures"]) > 1,
            post_failure_rows=audit.post_failure.get(serial, 0),
            days_unobserved_before_window_end=(audit.end - d["last"]).days,
            gap_episodes=len(episodes), missing_days_in_gaps=sum(lengths),
            longest_gap_days=max(lengths, default=0),
            gap_before_first_failure=(None if first_failure is None
                                      else any(back <= first_failure for _, back in episodes)),
            gap_after_first_failure=(None if first_failure is None
                                     else any(last >= first_failure for last, _ in episodes)),
            boundary_linkage="not_attempted",
        ))
    return rows


def cohort_accounting(records: list[dict]) -> list[dict]:
    """Reconciled counts overall and by baseline 197 / 5 state. Descriptive only."""
    included = [r for r in records if r["inclusion"] == "included"]

    def summary(group):
        out = {k: sum(r["outcome"] == k for r in group) for k in OUTCOMES}
        out.update(included=len(group), intermittent_gap_drives=sum(r["gap_episodes"] > 0 for r in group),
                   post_failure_row_drives=sum(r["post_failure_rows"] > 0 for r in group))
        _require(sum(out[k] for k in OUTCOMES) == len(group), "outcomes do not sum to included drives")
        return out

    total = dict(attribute="all", stratum="all", drives_observed=len(records),
                 **{k: sum(r["inclusion"] == k for r in records) for k in INCLUSIONS[1:]},
                 **summary(included))
    _require(total["included"] + total["excluded_later_arrival"] +
             total["excluded_failure_on_or_before_baseline"] == total["drives_observed"],
             "inclusion classes do not sum to observed drives")
    rows = [total]
    for column in WARNING_COLUMNS:
        for state in ("zero", "nonzero", "missing"):
            group = [r for r in included if r[f"baseline_{column}_state"] == state]
            rows.append(dict(attribute=column, stratum=state, **summary(group)))
    return rows


def run_cohort(source: Source, output_dir: Path, model: str = SEAGATE,
               baseline: date = Q1_START, end: date = Q1_END, chunksize: int = 50_000,
               expected_crc32: dict[str, str] | None = None) -> list[dict]:
    """Stream daily members in [baseline, end], keep one model's rows, write outputs.

    ``expected_crc32`` maps ISO date -> recorded member CRC32 (for example from
    ``results/audit/data_manifest.json``); any mismatch or unverifiable member
    is refused before reading. Outputs are serial-level; keep them ignored.
    """
    audit, evidence = stream_cohort(source, model, baseline, end, chunksize, expected_crc32)
    records = drive_records(audit)
    accounting = cohort_accounting(records)
    output_dir = Path(output_dir)
    write_table(output_dir / "cohort_drives.csv", records)
    write_table(output_dir / "cohort_accounting.csv", accounting)
    manifest = dict(
        model=model, baseline=baseline.isoformat(), window_end=end.isoformat(),
        source_type=source.source_type, source=_shareable_source(source), member_evidence=evidence,
        time_scale="calendar days from fixed baseline; SMART 9 is a descriptor, not age",
        boundary_linkage="not_attempted", models_fitted="none",
        crc32_checked_against_recorded_manifest=expected_crc32 is not None,
        output_sha256={n: digest(output_dir / n) for n in ("cohort_drives.csv", "cohort_accounting.csv")})
    (output_dir / "cohort_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return accounting


def stream_cohort(source: Source, model: str = SEAGATE, baseline: date = Q1_START, end: date = Q1_END,
                  chunksize: int = 50_000, expected_crc32: dict[str, str] | None = None
                  ) -> tuple[CohortAudit, list[dict]]:
    """Validated streaming pass shared by ``run_cohort`` and later analyses; writes nothing."""
    members = [m for m in source.members()
               if baseline <= date.fromisoformat(m.date_text) <= end and not m.name.startswith("__MACOSX/")]
    dates = sorted(date.fromisoformat(m.date_text) for m in members)
    if len(dates) != len(set(dates)):
        raise ValueError("Overlapping source dates; refuse double counting")
    if dates != [baseline + timedelta(days=i) for i in range((end - baseline).days + 1)]:
        raise ValueError("Incomplete source calendar; absences cannot be classified as drive gaps")
    if expected_crc32 is not None:
        for m in members:
            if m.crc32 is None or expected_crc32.get(m.date_text) != m.crc32:
                raise ValueError(f"Member {m.name} CRC32 {m.crc32} does not match recorded provenance")
    audit = CohortAudit(model, baseline, end)
    evidence = []
    for member in sorted(members, key=lambda m: m.date_text):
        day = date.fromisoformat(member.date_text)
        parts = [pd.DataFrame(columns=list(CORE + SMART))]
        with source.open(member) as handle:
            hashed = HashReader(handle)
            with io.BufferedReader(hashed) as buffered:
                for chunk in pd.read_csv(buffered, usecols=lambda c: c in CORE + SMART, chunksize=chunksize,
                                         encoding="utf-8-sig", low_memory=False,
                                         dtype={"serial_number": "string", "model": "string", "date": "string"}):
                    if not set(CORE) <= set(chunk.columns):
                        raise ValueError(f"Missing core columns in {member.name}")
                    parts.append(chunk[chunk["model"].isin({model, PROSPECTIVE_ALIAS})])
            sha = hashed.hash.hexdigest()
        selected = pd.concat(parts, ignore_index=True)
        audit.ingest(selected, day)
        evidence.append(dict(date=day.isoformat(), member=member.name, crc32=member.crc32,
                             sha256=sha, candidate_rows=len(selected)))
    return audit, evidence
