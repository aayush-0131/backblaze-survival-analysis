"""Synthetic checks for the age-adjusted secondary model. All drives and values are invented."""
import numpy as np
import pandas as pd
import pytest

from backblaze_audit.age_adjusted import HOURS_PER_YEAR, add_powered_years, cox_age_adjusted, describe_age
from backblaze_audit.survival import primary_frame

W = 89


def synthetic(n=400, seed=7):
    rng = np.random.default_rng(seed)
    x = (rng.random(n) < 0.3).astype(int)
    years = rng.uniform(3, 7, n)
    rate = 0.002 * np.exp(1.2 * x + 0.3 * (years - 5))
    t = rng.exponential(1 / rate)
    event = t <= W
    rows = [dict(serial_number=f"s{i}", inclusion="included",
                 outcome="recorded_failure" if event[i] else "administrative_censoring",
                 followup_days=int(max(1, np.ceil(t[i]))) if event[i] else W,
                 baseline_smart_197_raw_state="nonzero" if x[i] else "zero",
                 baseline_smart_9_raw_powered_hours_counter=int(years[i] * HOURS_PER_YEAR)) for i in range(n)]
    return pd.DataFrame(rows)


def test_powered_years_mapping_and_guards():
    d = synthetic(20)
    f = add_powered_years(primary_frame(d, W), d)
    assert f["powered_years"].iloc[0] == pytest.approx(d[ "baseline_smart_9_raw_powered_hours_counter"].iloc[0] / HOURS_PER_YEAR)
    desc = describe_age(f)
    assert desc["smart_197_zero"]["n"] + desc["smart_197_nonzero"]["n"] == 20
    bad = d.copy(); bad.loc[0, "baseline_smart_9_raw_powered_hours_counter"] = None
    with pytest.raises(ValueError, match="missing"):
        add_powered_years(primary_frame(bad, W), bad)


def test_two_covariate_fit_cross_checks_and_recovers_direction():
    d = synthetic()
    r = cox_age_adjusted(add_powered_years(primary_frame(d, W), d))
    assert r["cross_check"]["max_abs_coef_difference"] <= 1e-6
    assert r["terms"]["x"]["hazard_ratio"] > 1 and r["terms"]["powered_years"]["hazard_ratio"] > 1
    assert set(r["terms"]) == {"x", "powered_years"}
