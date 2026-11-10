"""Synthetic checks for the pre-specified survival analysis. All drives and dates are invented."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from backblaze_audit.survival import analyse, cox, kaplan_meier, primary_frame, s1_frame, s2_intervals

B = date(2026, 1, 1)
W = 89


def drives():
    def r(serial, outcome, days, state, inclusion="included"):
        return dict(serial_number=serial, inclusion=inclusion, outcome=outcome, followup_days=days,
                    baseline_smart_197_raw_state=state)
    return pd.DataFrame([
        r("a", "recorded_failure", 1, "nonzero"), r("b", "recorded_failure", 2, "nonzero"),
        r("c", "administrative_censoring", W, "nonzero"), r("d", "unexplained_exit", 2, "nonzero"),
        r("e", "recorded_failure", 40, "zero"), r("f", "unexplained_exit", 86, "zero"),
        r("g", "administrative_censoring", W, "zero"), r("h", "unexplained_exit", 5, "zero"),
        r("late", "recorded_failure", 10, "zero", inclusion="excluded_later_arrival"),
    ])


def test_primary_frame_maps_outcomes_and_excludes_non_included():
    f = primary_frame(drives(), W)
    assert list(f.serial_number) == list("abcdefgh")
    assert f.event.tolist() == [1, 1, 0, 0, 1, 0, 0, 0]
    assert f.x.tolist() == [1, 1, 1, 1, 0, 0, 0, 0]
    bad = drives(); bad.loc[0, "baseline_smart_197_raw_state"] = "missing"
    with pytest.raises(ValueError, match="states"):
        primary_frame(bad, W)
    bad = drives(); bad.loc[2, "followup_days"] = 50
    with pytest.raises(ValueError, match="window end"):
        primary_frame(bad, W)


def test_km_matches_hand_calculation():
    # nonzero group: events at 1 and 2, exit censored at 2, admin censored at 89.
    # S(1) = 3/4; at t=2 risk set is 3 (b, c, d), one event: S(2) = 3/4 * 2/3 = 0.5
    steps, summary = kaplan_meier(primary_frame(drives(), W), "P", counting=False)
    nz = {r["time_days"]: r for r in steps if r["group"] == "smart_197_nonzero"}
    assert nz[1]["survival"] == pytest.approx(0.75) and nz[1]["at_risk"] == 4
    assert nz[2]["survival"] == pytest.approx(0.5) and nz[2]["censored"] == 1
    assert summary["smart_197_nonzero"]["survival_at"]["89"]["estimate"] == pytest.approx(0.5)
    assert summary["smart_197_nonzero"]["at_risk"] == {"0": 4, "30": 1, "60": 1, "89": 1}
    # zero group: exit at 5, event at 40 (risk 3), so S(40) = 2/3
    assert summary["smart_197_zero"]["survival_at"]["60"]["estimate"] == pytest.approx(2 / 3)


def test_s1_moves_only_reappeared_exits_to_window_end():
    p = primary_frame(drives(), W)
    link = pd.DataFrame(dict(serial_number=["d", "f", "h"],
                             linkage_status=["reappeared_verified", "reappeared_verified",
                                             "not_observed_through_window_end"]))
    s1 = s1_frame(p, link, W).set_index("serial_number")
    assert s1.loc["d", "duration"] == W and s1.loc["f", "duration"] == W and s1.loc["h", "duration"] == 5
    assert s1.event.sum() == p.event.sum()  # exits never become events
    with pytest.raises(ValueError, match="do not match"):
        s1_frame(p, link.iloc[:2], W)


def test_s2_removes_gap_days_and_keeps_return_day_event():
    p = primary_frame(drives(), W)
    # e: seen days 0..9, missing 10..19, back day 20, fails day 40 -> (0,9], (19,40]
    # a: seen day 0 only, missing nothing else (fails day 1) -> no gap
    # g: seen day 0, missing days 1-2, back day 3 -> first segment (0,0] dropped, then (2,89]
    episodes = {"e": [(date(2026, 1, 10), date(2026, 1, 21))], "g": [(B, date(2026, 1, 4))]}
    iv = s2_intervals(p, {"e": 10, "g": 2}, episodes, B)
    e = iv[iv.serial_number == "e"][["start", "stop", "event"]].values.tolist()
    assert e == [[0, 9, 0], [19, 40, 1]]
    assert iv[iv.serial_number == "g"][["start", "stop"]].values.tolist() == [[2, 89]]
    # return-day event: gap ends on the failure day itself
    ret = {"b": [(B, date(2026, 1, 3))]}  # seen day 0, missing day 1, back and fails day 2
    rb = s2_intervals(p, {"b": 1}, ret, B)
    assert rb[rb.serial_number == "b"][["start", "stop", "event"]].values.tolist() == [[1, 2, 1]]
    with pytest.raises(ValueError, match="minus gap days"):
        s2_intervals(p, {"e": 9}, episodes, B)


def test_cox_cross_check_and_no_gap_s2_equals_primary():
    rng = np.random.default_rng(7)
    n = 600
    x = rng.integers(0, 2, n)
    t = np.ceil(rng.exponential(120 / np.exp(1.0 * x)))
    p = pd.DataFrame(dict(serial_number=[f"s{i}" for i in range(n)], duration=np.minimum(t, W).astype(int),
                          event=(t <= W).astype(int), x=x, outcome="x"))
    primary = cox(p, counting=False)
    assert primary["cross_check"]["abs_coef_difference"] <= 1e-6
    assert 1.5 < primary["hazard_ratio"] < 4.5 and primary["ph_test"]["p_value"] >= 0
    iv = p.assign(start=0, stop=p.duration)[["serial_number", "start", "stop", "event", "x"]]
    counting = cox(iv, counting=True)
    assert counting["coef"] == pytest.approx(primary["coef"], abs=1e-6)
    assert counting["se"] == pytest.approx(primary["se"], rel=1e-5)
    steps, results = analyse({"P": (p, False), "S2": (iv, True)})
    assert results["P"]["kaplan_meier"] == results["S2"]["kaplan_meier"]


def test_counting_process_uses_strict_risk_set_at_reentry():
    # A (0,5] event; B (0,5] censored; C re-enters (5,10]; D (0,10]. Strict: risk set at t=5 is {A,B,D}.
    iv = pd.DataFrame(dict(serial_number=["A", "B", "C", "D"], start=[0, 0, 5, 0], stop=[5, 5, 10, 10],
                           event=[1, 0, 0, 0], x=[1, 1, 1, 1]))
    steps, summary = kaplan_meier(pd.concat([iv, iv.assign(serial_number=iv.serial_number + "0", x=0)]),
                                  "S2", counting=True)
    row = next(r for r in steps if r["group"] == "smart_197_nonzero" and r["time_days"] == 5)
    assert row["at_risk"] == 3 and row["survival"] == pytest.approx(2 / 3)


def test_cox_engines_agree_when_reentries_coincide_with_event_times():
    rng = np.random.default_rng(11)
    rows = []
    for i in range(500):
        x = int(rng.integers(0, 2))
        t = int(min(np.ceil(rng.exponential(150 / np.exp(0.9 * x))), W))
        event = int(t < W)
        if t > 20 and rng.random() < 0.4:           # gap: drive missing days 9..14
            rows += [(f"s{i}", 0, 8, 0, x), (f"s{i}", 14, t, event, x)]
        else:
            rows.append((f"s{i}", 0, t, event, x))
    rows += [(f"e{k}", 0, 14, 1, k % 2) for k in range(6)]  # events on the re-entry day 14
    iv = pd.DataFrame(rows, columns=["serial_number", "start", "stop", "event", "x"])
    assert (iv.start == 14).any() and ((iv.stop == 14) & (iv.event == 1)).sum() >= 6
    out = cox(iv, counting=True)
    assert out["cross_check"]["abs_coef_difference"] <= 1e-6
