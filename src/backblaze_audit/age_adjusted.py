"""Secondary age-adjusted Cox model (docs/q1_age_adjusted_plan.md). One model only.

Covariates: x (baseline SMART 197 nonzero) and powered_years (baseline SMART 9 raw / 8766,
a powered-on-hours proxy, NOT physical age). Same time/event/censoring as the primary
analysis; same damped fit, statsmodels cross-check and score check as survival.cox.
"""
from __future__ import annotations

import math
import warnings

import numpy as np
import pandas as pd

from .survival import COEF_TOLERANCE, LIFELINES_FIT, SCORE_TOLERANCE, STATSMODELS_FIT, _scalar

HOURS_PER_YEAR = 8766
SMART9_COLUMN = "baseline_smart_9_raw_powered_hours_counter"
COVARIATES = ("x", "powered_years")
REFINE_FIT = dict(step_size=1.0, precision=1e-12, max_steps=50)


def add_powered_years(primary: pd.DataFrame, drives: pd.DataFrame) -> pd.DataFrame:
    """Attach baseline powered years to the primary frame; refuse if any is missing."""
    hours = drives.set_index(drives["serial_number"].astype(str))[SMART9_COLUMN]
    frame = primary.copy()
    frame["smart9_hours"] = frame["serial_number"].map(hours)
    if frame["smart9_hours"].isna().any():
        raise ValueError("Baseline SMART 9 missing for an included drive; plan assumes none")
    if (frame["smart9_hours"] < 0).any():
        raise ValueError("Negative SMART 9 counter")
    frame["powered_years"] = frame["smart9_hours"].astype(float) / HOURS_PER_YEAR
    return frame


def describe_age(frame: pd.DataFrame) -> dict:
    out = {}
    for code, group in ((0, "smart_197_zero"), (1, "smart_197_nonzero")):
        v = frame.loc[frame["x"] == code, "powered_years"]
        out[group] = dict(n=int(len(v)), zero_counters=int((frame.loc[frame["x"] == code, "smart9_hours"] == 0).sum()),
                          **{k: round(float(q), 4) for k, q in
                             zip(("min", "q1", "median", "q3", "max"), v.quantile([0, .25, .5, .75, 1]))})
    return out


def cox_age_adjusted(frame: pd.DataFrame) -> dict:
    from lifelines import CoxPHFitter
    from lifelines.statistics import proportional_hazard_test
    from statsmodels.duration.hazard_regression import PHReg
    df = frame[["duration", "event", *COVARIATES]]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # Damped steps (as in the primary fit) avoid overflow from beta=0 but can stop with
        # |score| ~1e-4 when there are two covariates; a full-Newton refinement started at the
        # damped solution then converges to the same maximum (numerical only, see plan notes).
        damped = CoxPHFitter().fit(df, duration_col="duration", event_col="event", fit_options=LIFELINES_FIT)
        fitter = CoxPHFitter().fit(df, duration_col="duration", event_col="event",
                                   initial_point=(damped.params_.to_numpy() * damped._norm_std.to_numpy()).copy(),
                                   fit_options=REFINE_FIT)  # lifelines starts on the standardised scale
        test = proportional_hazard_test(fitter, df, time_transform="rank")
        model = PHReg(df["duration"], df[list(COVARIATES)].astype(float), status=df["event"], ties="efron")
        sm = model.fit(**STATSMODELS_FIT)
    coefs = np.array([float(fitter.params_[c]) for c in COVARIATES])
    sm_coefs = np.asarray(sm.params, dtype=float)
    diff = float(np.max(np.abs(coefs - sm_coefs)))
    if diff > COEF_TOLERANCE:
        raise ValueError(f"lifelines and statsmodels disagree on coefficients by {diff}")
    score = float(np.max(np.abs(np.asarray(model.score(coefs), dtype=float))))
    if score > SCORE_TOLERANCE:
        raise ValueError(f"Partial-likelihood score {score} at the lifelines solution is not ~0")
    ph = test.summary
    terms = {}
    for c in COVARIATES:
        s = fitter.summary.loc[c]
        terms[c] = dict(coef=round(float(s["coef"]), 8), se=round(float(s["se(coef)"]), 8),
                        hazard_ratio=round(math.exp(float(s["coef"])), 6),
                        hr_ci95=[round(float(s["exp(coef) lower 95%"]), 6), round(float(s["exp(coef) upper 95%"]), 6)],
                        z=round(float(s["z"]), 6), p_value=float(f"{float(s['p']):.6g}"),
                        ph_test=dict(statistic=round(_scalar(ph.loc[c, "test_statistic"]), 8),
                                     p_value=round(_scalar(ph.loc[c, "p"]), 8)))
    return dict(
        model="Cox PH, Efron ties: x (baseline SMART 197 > 0) + powered_years (baseline SMART 9 / 8766, linear)",
        drives=int(len(df)), events=int(df["event"].sum()), terms=terms,
        ph_test_method="scaled Schoenfeld, rank time transform (lifelines proportional_hazard_test)",
        cross_check=dict(engine="statsmodels PHReg (efron), BFGS from 0",
                         coefs=[round(float(v), 8) for v in sm_coefs],
                         max_abs_coef_difference=float(f"{diff:.3g}"), tolerance=COEF_TOLERANCE,
                         max_abs_score_at_solution=float(f"{score:.3g}")),
        numerical_settings=dict(lifelines=LIFELINES_FIT, lifelines_refinement=REFINE_FIT, statsmodels=STATSMODELS_FIT,
                                reason="damped fit from 0, then full-Newton refinement from the damped solution"))
