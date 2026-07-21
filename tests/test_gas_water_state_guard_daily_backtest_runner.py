from __future__ import annotations

from v5.gas_water_state_guard_daily_backtest_runner import _annotate_guard_order_health, apply_state_guard_to_signals


def test_daily_state_guard_uses_prior_history_only() -> None:
    signals = {
        "2021-01-01": ["A"],
        "2021-04-01": ["A"],
        "2021-07-01": ["A"],
    }
    panel = {
        "2021-01-01": [{"code": "A", "risk": "1"}],
        "2021-04-01": [{"code": "A", "risk": "2"}],
        "2021-07-01": [{"code": "A", "risk": "100"}],
    }

    guarded, decisions = apply_state_guard_to_signals(signals, panel, guard_field="risk", guard_quantile=0.75, min_history=2)

    assert [row["blocked"] for row in decisions] == [0, 0, 1]
    assert guarded["2021-01-01"] == ["A"]
    assert guarded["2021-04-01"] == ["A"]
    assert guarded["2021-07-01"] == []
    assert decisions[2]["history_count_before_decision"] == 2
    assert decisions[2]["expanding_threshold"] == 1.0


def test_guard_blocked_cash_dates_are_not_unexpected_order_failures() -> None:
    rows = [
        {
            "trade_date": "2021-01-01",
            "order_health_status": "no_selected_stocks",
            "executed_order_count": 0,
            "diagnosis": "Signal exists but selected universe is empty.",
        },
        {
            "trade_date": "2021-04-01",
            "order_health_status": "normal_ordered",
            "executed_order_count": 2,
            "diagnosis": "At least one order executed and holdings exist after rebalance.",
        },
        {
            "trade_date": "2021-07-01",
            "order_health_status": "no_order_no_position",
            "executed_order_count": 0,
            "diagnosis": "Signal exists but no order executed and no selected holding exists after rebalance.",
        },
    ]
    decisions = [
        {"trade_date": "2021-01-01", "blocked": 1, "base_selected_count": 1, "decision_source": "test"},
        {"trade_date": "2021-04-01", "blocked": 0, "base_selected_count": 1, "decision_source": "test"},
        {"trade_date": "2021-07-01", "blocked": 0, "base_selected_count": 1, "decision_source": "test"},
    ]

    annotated, summary = _annotate_guard_order_health(
        rows,
        decisions,
        {
            "rebalance_signal_count": 3,
            "missing_daily_rebalance_count": 0,
            "needs_review": True,
        },
    )

    assert annotated[0]["order_health_status"] == "intentional_guard_cash_block_no_order_needed"
    assert annotated[2]["order_health_status"] == "no_order_no_position"
    assert summary["intentional_guard_cash_block_count"] == 1
    assert summary["unexpected_rebalance_issue_count"] == 1
    assert summary["needs_review"] is True
