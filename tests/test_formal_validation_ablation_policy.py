from __future__ import annotations

from v5.formal_validation_runner import _scoring_case_raw


def _raw_spec() -> dict:
    return {
        "signals": {
            "factors": [
                {"name": "factor_a", "direction": "higher_is_better"},
                {"name": "factor_b", "direction": "higher_is_better"},
                {"name": "factor_c", "direction": "lower_is_better"},
            ],
            "scoring": {
                "method": "weighted_composite",
                "min_factor_count": 3,
                "weights": {"factor_a": 1.0, "factor_b": 1.0, "factor_c": 1.0},
            },
        }
    }


def test_scoring_case_raw_lowers_min_factor_count_after_ablation_drop() -> None:
    raw = _raw_spec()
    factors = [factor for factor in raw["signals"]["factors"] if factor["name"] != "factor_c"]

    case_raw = _scoring_case_raw(raw, factors=factors, weights=raw["signals"]["scoring"]["weights"])

    assert case_raw["signals"]["scoring"]["min_factor_count"] == 2
    assert set(case_raw["signals"]["scoring"]["weights"]) == {"factor_a", "factor_b"}


def test_scoring_case_raw_lowers_min_factor_count_for_single_factor_common_sample() -> None:
    raw = _raw_spec()
    factors = [raw["signals"]["factors"][0]]

    case_raw = _scoring_case_raw(raw, factors=factors, weights=raw["signals"]["scoring"]["weights"])

    assert case_raw["signals"]["scoring"]["min_factor_count"] == 1
