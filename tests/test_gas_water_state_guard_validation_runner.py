from __future__ import annotations

from v5.gas_water_state_guard_validation_runner import _quantile, _run_case


def test_quantile_uses_supplied_history_only() -> None:
    assert _quantile([1.0, 2.0, 100.0], 0.75) == 2.0


def test_state_guard_blocks_only_after_min_history() -> None:
    by_date = {
        "2025-01-01": [{"code": "A", "future_return": 0.1, "risk": "1"}],
        "2025-04-01": [{"code": "A", "future_return": 0.1, "risk": "2"}],
        "2025-07-01": [{"code": "A", "future_return": 0.1, "risk": "100"}],
    }
    raw = {
        "signals": {
            "factors": [{"name": "risk", "direction": "lower_is_better"}],
            "scoring": {"method": "weighted_composite", "weights": {"risk": 1.0}, "min_factor_count": 1},
        },
        "portfolio": {"selection_count": 1},
    }

    result = _run_case("test", by_date, raw, guard_field="risk", quantile=0.75, min_history=2)

    assert [row["blocked"] for row in result["decisions"]] == [0, 0, 1]
    assert result["summary"]["blocked_periods"] == 1
