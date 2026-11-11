"""Pre-specified Q1 survival analysis (docs/q1_analysis_plan.md).

Kaplan-Meier by baseline SMART 197 group and ONE Cox model with a single binary
covariate (197 nonzero vs zero, Efron ties), on the primary data (P) and two
sensitivity variants: S1 (exits verified to reappear Apr 1-14 censored at the
window end) and S2 (gap days removed from the risk set via start/stop intervals).
lifelines fits; statsmodels PHReg is an independent cross-check.

Interval convention for S2: a drive observed on day d contributes (d-1, d]; a gap
from last-seen day L to return day R removes (L, R-1], so an event flagged on the
return day stays in the risk set.
"""
from __future__ import annotations

from datetime import date
import math
import warnings

import numpy as np
import pandas as pd

GROUP_COLUMN = "baseline_smart_197_raw_state"
GROUPS = ("zero", "nonzero")
LANDMARKS = (30, 60, 89)
AT_RISK_DAYS = (0, 30, 60, 89)
COEF_TOLERANCE = 1e-6
# Undamped Newton from beta=0 overshoots and overflows here (rare exposure, strong effect);
# the partial likelihood is concave, so damping changes the path, not the maximum.
LIFELINES_FIT = dict(step_size=0.1, precision=1e-10, max_steps=500)
STATSMODELS_FIT = dict(method="bfgs", gtol=1e-10, maxiter=1000, disp=0)  # from beta=0
SCORE_TOLERANCE = 1e-4


def primary_frame(drives: pd.DataFrame, window_days: int) -> pd.DataFrame:
    """One row per included drive: duration (days), event (0/1), x (197 nonzero)."""
    inc = drives[drives["inclusion"] == "included"].copy()
    states = set(inc[GROUP_COLUMN])
    if not states <= set(GROUPS):
        raise ValueError(f"Unexpected baseline 197 states {sorted(states - set(GROUPS))}; plan covers zero/nonzero only")
    frame = pd.DataFrame(dict(
        serial_number=inc["serial_number"].astype(str).to_numpy(),
        duration=inc["followup_days"].astype(int).to_numpy(),
        event=(inc["outcome"] == "recorded_failure").astype(int).to_numpy(),
        x=(inc[GROUP_COLUMN] == "nonzero").astype(int).to_numpy(),
        outcome=inc["outcome"].to_numpy()))
    if not frame["duration"].between(0, window_days).all():
        raise ValueError("Follow-up outside the window")
    if (frame.loc[frame["event"] == 1, "duration"] < 1).any():
        raise ValueError("Event at or before baseline in an included drive")
    if not (frame.loc[frame["outcome"] == "administrative_censoring", "duration"] == window_days).all():
        raise ValueError("Administrative censoring not at the window end")
    return frame


def s1_frame(primary: pd.DataFrame, linkage: pd.DataFrame, window_days: int) -> pd.DataFrame:
    """D3 sensitivity: exits verified to reappear are censored at the window end."""
    exits = set(primary.loc[primary["outcome"] == "unexplained_exit", "serial_number"])
    linked = set(linkage["serial_number"].astype(str))
    if linked != exits:
        raise ValueError("Linkage records do not match the cohort's unexplained exits")
    back = set(linkage.loc[linkage["linkage_status"] == "reappeared_verified", "serial_number"].astype(str))
    frame = primary.copy()
    moved = frame["serial_number"].isin(back)
    frame.loc[moved, "duration"] = window_days
    frame.loc[moved, "event"] = 0
    return frame


def s2_intervals(primary: pd.DataFrame, missing_days: dict[str, int],
                 episodes: dict[str, list[tuple[date, date]]], baseline: date) -> pd.DataFrame:
    """D4 sensitivity: start/stop rows with gap days removed. Checks total length per drive."""
    rows = []
    for r in primary.itertuples():
        start = 0
        for last, back in sorted(episodes.get(r.serial_number, [])):
            stop, returned = (last - baseline).days, (back - baseline).days
            # last-seen day after the current start, at least one missing day, return within follow-up
            if not (start <= stop and returned - stop >= 2 and returned <= r.duration):
                raise ValueError("Gap episode outside follow-up for a drive")
            if stop > start:
                rows.append((r.serial_number, start, stop, 0, r.x))
            start = returned - 1
        if r.duration <= start:
            raise ValueError("Empty final interval")
        rows.append((r.serial_number, start, r.duration, r.event, r.x))
    out = pd.DataFrame(rows, columns=["serial_number", "start", "stop", "event", "x"])
    length = (out["stop"] - out["start"]).groupby(out["serial_number"]).sum()
    expected = primary.set_index("serial_number")["duration"] - pd.Series(missing_days).reindex(
        primary["serial_number"]).fillna(0).astype(int).to_numpy()
    if not (length.reindex(expected.index) == expected).all():
        raise ValueError("Interval lengths do not equal follow-up minus gap days")
    if out.groupby("serial_number")["event"].sum().max() > 1:
        raise ValueError("More than one event per drive")
    return out


def _scalar(value) -> float:
    return float(np.asarray(value, dtype=float).ravel()[0])


def _step(series: pd.Series, t: float) -> float:
    return float(series[series.index <= t].iloc[-1])


def kaplan_meier(data: pd.DataFrame, analysis: str, counting: bool) -> tuple[list[dict], dict]:
    """KM per group. Returns full step rows and landmark/at-risk summary."""
    from lifelines import KaplanMeierFitter
    steps, summary = [], {}
    for code, group in enumerate(GROUPS):
        g = data[data["x"] == code]
        stop = g["stop"] if counting else g["duration"]
        entry = g["start"] if counting else None
        kmf = KaplanMeierFitter(alpha=0.05).fit(stop, g["event"], entry=entry, label=group)
        sf = kmf.survival_function_[group]
        lo, hi = kmf.confidence_interval_.iloc[:, 0], kmf.confidence_interval_.iloc[:, 1]
        table = kmf.event_table
        start = g["start"] if counting else pd.Series(0, index=g.index)
        # Risk set at t is start < t <= stop (lifelines' event_table at_risk also counts entrants at t).
        risk = {t: int(((start < t) & (stop >= t)).sum()) for t in table.index}
        check = 1.0
        for t, row in table.iterrows():
            if row["observed"]:
                check *= 1 - row["observed"] / risk[t]
            if abs(check - float(sf.loc[t])) > 1e-12:
                raise ValueError("Kaplan-Meier estimate disagrees with the strict-risk-set product limit")
            if t == 0 and row["observed"] == 0 and row["censored"] == 0:
                continue
            steps.append(dict(analysis=analysis, group=f"smart_197_{group}", time_days=int(t),
                              at_risk=risk[t], events=int(row["observed"]),
                              censored=int(row["censored"]), survival=round(float(sf.loc[t]), 10),
                              ci_lower=round(float(lo.loc[t]), 10), ci_upper=round(float(hi.loc[t]), 10)))
        summary[f"smart_197_{group}"] = dict(
            drives=int(g["serial_number"].nunique()), events=int(g["event"].sum()),
            at_risk={str(d): int(g["serial_number"].nunique()) if d == 0
                     else int(g.loc[(start < d) & (stop >= d), "serial_number"].nunique())
                     for d in AT_RISK_DAYS},
            survival_at={str(d): dict(estimate=round(_step(sf, d), 10), ci_lower=round(_step(lo, d), 10),
                                      ci_upper=round(_step(hi, d), 10)) for d in LANDMARKS})
    return steps, summary


def cox(data: pd.DataFrame, counting: bool) -> dict:
    """The single pre-specified Cox model, with a PH test (P/S1) and a statsmodels cross-check."""
    from lifelines import CoxPHFitter, CoxTimeVaryingFitter
    from lifelines.statistics import proportional_hazard_test
    from statsmodels.duration.hazard_regression import PHReg
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if counting:
            fitter = CoxTimeVaryingFitter().fit(data[["serial_number", "start", "stop", "event", "x"]],
                                                id_col="serial_number", event_col="event",
                                                start_col="start", stop_col="stop", fit_options=LIFELINES_FIT)
            ph = None
        else:
            df = data[["duration", "event", "x"]]
            fitter = CoxPHFitter().fit(df, duration_col="duration", event_col="event", fit_options=LIFELINES_FIT)
            test = proportional_hazard_test(fitter, df, time_transform="rank")
            ph = dict(method="scaled Schoenfeld, rank time transform (lifelines proportional_hazard_test)",
                      statistic=round(_scalar(test.test_statistic), 8), p_value=round(_scalar(test.p_value), 8))
        # statsmodels counts a subject entering at t as at risk at t (Stata-style); lifelines and the
        # plan use start < t <= stop. Times are whole days, so entry + 0.5 reproduces the strict rule.
        model = PHReg(data["stop"] if counting else data["duration"], data[["x"]].astype(float),
                      status=data["event"], entry=data["start"] + 0.5 if counting else None, ties="efron")
        sm = model.fit(**STATSMODELS_FIT)
    s = fitter.summary.loc["x"]
    coef, se = float(s["coef"]), float(s["se(coef)"])
    sm_coef, sm_se = _scalar(sm.params), _scalar(sm.bse)
    diff = abs(coef - sm_coef)
    if diff > COEF_TOLERANCE:
        raise ValueError(f"lifelines and statsmodels disagree on the coefficient by {diff}")
    score = _scalar(model.score(np.array([coef])))
    if abs(score) > SCORE_TOLERANCE:
        raise ValueError(f"Partial-likelihood score {score} at the lifelines solution is not ~0")
    return dict(
        covariate="baseline SMART 197 raw nonzero (1) vs zero (0)", ties="efron",
        coef=round(coef, 8), se=round(se, 8), hazard_ratio=round(math.exp(coef), 6),
        hr_ci95=[round(float(s["exp(coef) lower 95%"]), 6), round(float(s["exp(coef) upper 95%"]), 6)],
        z=round(float(s["z"]), 6), p_value=float(f"{float(s['p']):.6g}"),
        ph_test=ph if ph is not None else "not available for start/stop fits in lifelines 0.30.0; not computed",
        cross_check=dict(engine="statsmodels 0.15.0 PHReg (efron), BFGS from 0", coef=round(sm_coef, 8),
                         se=round(sm_se, 8), abs_coef_difference=float(f"{diff:.3g}"),
                         tolerance=COEF_TOLERANCE, score_at_solution=float(f"{score:.3g}")),
        numerical_settings=dict(lifelines=LIFELINES_FIT, statsmodels=STATSMODELS_FIT,
                                reason="undamped Newton from 0 overflows (rare exposure, strong effect); "
                                       "concave likelihood, so the maximum is unchanged"))


def analyse(variants: dict[str, tuple[pd.DataFrame, bool]]) -> tuple[list[dict], dict]:
    steps, results = [], {}
    for name, (data, counting) in variants.items():
        km_steps, km_summary = kaplan_meier(data, name, counting)
        steps.extend(km_steps)
        results[name] = dict(rows=len(data), drives=int(data["serial_number"].nunique()),
                             events=int(data["event"].sum()), kaplan_meier=km_summary, cox=cox(data, counting))
    return steps, results


def plot_primary(steps: list[dict], path, title: str, counts: dict | None = None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=150)
    colours = {"smart_197_zero": "#1f77b4", "smart_197_nonzero": "#d62728"}
    labels = {"smart_197_zero": "SMART 197 = 0 at baseline", "smart_197_nonzero": "SMART 197 > 0 at baseline"}
    for group, colour in colours.items():
        rows = [r for r in steps if r["analysis"] == "P" and r["group"] == group]
        t = [0] + [r["time_days"] for r in rows]
        s = [1.0] + [r["survival"] for r in rows]
        lo = [1.0] + [r["ci_lower"] for r in rows]
        hi = [1.0] + [r["ci_upper"] for r in rows]
        t, s, lo, hi = t + [89], s + [s[-1]], lo + [lo[-1]], hi + [hi[-1]]
        label = labels[group] + (f" (n={counts[group]['drives']:,}; {counts[group]['events']} failures)" if counts else "")
        ax.step(t, s, where="post", color=colour, label=label)
        ax.fill_between(t, lo, hi, step="post", color=colour, alpha=0.15, linewidth=0)
    ax.set_xlim(0, 89)
    ax.set_xlabel("Days since 2026-01-01 (calendar follow-up)")
    ax.set_ylabel("Proportion without a recorded failure")
    ax.set_title(title, fontsize=10)
    ax.legend(loc="lower left", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, metadata={"Software": None})
    plt.close(fig)
