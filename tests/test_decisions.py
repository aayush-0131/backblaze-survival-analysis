"""Synthetic checks for the recorded D1 rule. All counts are invented."""
import pytest

from backblaze_audit.decisions import D1_MIN_EVENTS, apply_d1, validated_group_counts


def accounting(lead_nonzero_failures):
    """Invented accounting: 100 included drives, 20 failures, 70 censored, 10 exits."""
    f = lead_nonzero_failures
    def row(attribute, stratum, included, failure, censored, exits):
        return dict(attribute=attribute, stratum=stratum, included=str(included), recorded_failure=str(failure),
                    administrative_censoring=str(censored), unexplained_exit=str(exits),
                    intermittent_gap_drives="0", post_failure_row_drives="0", drives_observed="",
                    excluded_later_arrival="", excluded_failure_on_or_before_baseline="")
    return [
        {**row("all", "all", 100, 20, 70, 10), "drives_observed": "103",
         "excluded_later_arrival": "2", "excluded_failure_on_or_before_baseline": "1"},
        row("smart_197_raw", "zero", 70, 20 - f, 45 + f, 5),
        row("smart_197_raw", "nonzero", 30, f, 25 - f, 5),
        row("smart_197_raw", "missing", 0, 0, 0, 0),
        row("smart_5_raw", "zero", 60, 8, 48, 4),
        row("smart_5_raw", "nonzero", 40, 12, 22, 6),
        row("smart_5_raw", "missing", 0, 0, 0, 0),
    ]


def test_threshold_is_the_recorded_value():
    assert D1_MIN_EVENTS == 10


@pytest.mark.parametrize("events, chosen", [(10, "smart_197_raw"), (11, "smart_197_raw"), (9, "smart_5_raw"),
                                            (0, "smart_5_raw")])
def test_d1_keeps_197_only_at_or_above_threshold(events, chosen):
    d = apply_d1(accounting(events))
    assert d["chosen_attribute"] == chosen
    assert d["lead_nonzero_recorded_failures"] == events and d["lead_nonzero_included"] == 30
    assert d["lead_meets_rule"] is (events >= 10)


def test_d1_sets_no_minimum_for_smart_5():
    rows = accounting(3)
    rows[5]["recorded_failure"], rows[5]["administrative_censoring"] = "0", "34"   # 5-nonzero: 0 failures
    rows[4]["recorded_failure"], rows[4]["administrative_censoring"] = "20", "36"  # 5-zero: all 20
    assert apply_d1(rows)["chosen_attribute"] == "smart_5_raw"  # rule as written; no fallback invented


def test_unreconciled_accounting_is_refused():
    rows = accounting(10)
    rows[2]["recorded_failure"] = "11"
    with pytest.raises(ValueError, match="do not sum"):
        validated_group_counts(rows)
    with pytest.raises(ValueError, match="strata"):
        validated_group_counts([r for r in accounting(10) if r["stratum"] != "missing"])
