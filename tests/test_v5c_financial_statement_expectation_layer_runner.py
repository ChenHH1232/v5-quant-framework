from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from v5.v5c_financial_statement_expectation_layer_runner import (
    OUT_DIR,
    run_v5c_financial_statement_expectation_layer,
)


class V5cFinancialStatementExpectationLayerRunnerTest(unittest.TestCase):
    def test_runner_builds_observe_only_expectation_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fixture(root)
            summary = run_v5c_financial_statement_expectation_layer(root)

            self.assertEqual(summary["status"], "completed_financial_statement_expectation_layer")
            self.assertEqual(summary["pm_gate_decision"], "expectation_layer_observation_ready_not_trading")
            self.assertGreater(summary["expectation_rows"], 0)
            self.assertGreater(summary["realized_rows"], 0)
            self.assertFalse(summary["accepted"])
            self.assertFalse(summary["v57f_core_modified"])
            self.assertFalse(summary["v5f_primary_modified"])
            self.assertFalse(summary["trade_rule_added"])
            self.assertFalse(summary["weight_change_added"])
            self.assertFalse(summary["formal_backtest_used_as_validation"])
            self.assertEqual(summary["fatal_blocker_count"], 0)

            out = root / OUT_DIR
            expected = [
                "v5c_financial_expectation_summary.json",
                "v5c_financial_expectation_report.md",
                "v5c_financial_expectation_schema.csv",
                "v5c_financial_expectation_knowledge_driver_usage.csv",
                "v5c_financial_expectation_historical_panel.csv",
                "v5c_financial_expectation_realized_next_change_panel.csv",
                "v5c_financial_expectation_accuracy_audit.csv",
                "v5c_financial_expectation_coverage_audit.csv",
                "v5c_financial_expectation_governance_audit.csv",
                "v5c_financial_expectation_pm_gate_decision.csv",
                "v5c_financial_expectation_next_agent_queue.csv",
                "v5c_financial_expectation_blockers.csv",
                "v5c_financial_expectation_agent_execution_rules.md",
            ]
            for name in expected:
                self.assertTrue((out / name).exists(), name)

            decision = _read_csv(out / "v5c_financial_expectation_pm_gate_decision.csv")[0]
            self.assertEqual(decision["admit_forward_observation"], "True")
            self.assertEqual(decision["admit_weight_change"], "False")
            self.assertEqual(decision["admit_trading_rule"], "False")

            governance = _read_csv(out / "v5c_financial_expectation_governance_audit.csv")
            self.assertTrue(all(row["audit_status"] == "pass" for row in governance))


def _write_fixture(root: Path) -> None:
    p1 = root / "v5c_p1_financial_quality_pit_panel" / "current"
    p1.mkdir(parents=True)
    (p1 / "v5c_p1_financial_quality_summary.json").write_text("{}", encoding="utf-8")

    rows = []
    for code in [f"6000{i:02d}.XSHG" for i in range(1, 11)]:
        rows.extend(_p1_rows(code, "bank"))
    for code in [f"6001{i:02d}.XSHG" for i in range(1, 11)]:
        rows.extend(_p1_rows(code, "utilities_electricity"))
    for code in [f"6002{i:02d}.XSHG" for i in range(1, 11)]:
        rows.extend(_p1_rows(code, "port_rail_infrastructure"))
    _write_csv(p1 / "v5c_p1_financial_quality_pit_panel.csv", rows)

    p2 = root / "v5c_p2_valuation_and_crowding_state_panel" / "current"
    p2.mkdir(parents=True)
    _write_csv(p2 / "v5c_p2_valuation_state_panel.csv", [_valuation_row(row) for row in rows])
    _write_csv(p2 / "v5c_p2_crowding_state_panel.csv", [_crowding_row(row) for row in rows])
    _write_csv(
        p2 / "v5c_p2_sleeve_overheat_state_panel.csv",
        [
            {
                "trade_date": date,
                "sleeve_id": sleeve,
                "avg_valuation_overheat_score": 0.2,
                "avg_money_percentile_252d": 0.4,
                "sleeve_benchmark_return_60d": 0.03,
                "sleeve_overheat_state": "normal",
                "pit_status": "pass",
            }
            for date in ["2021-05-06", "2021-07-01", "2021-10-08"]
            for sleeve in ["bank", "utilities_electricity", "port_rail_infrastructure"]
        ],
    )

    knowledge = root / "knowledge" / "research_agent" / "v5c_industry_bank_power_p0"
    knowledge.mkdir(parents=True)
    _write_csv(
        knowledge / "v5c_bank_driver_metric_map.csv",
        [
            {
                "industry": "bank",
                "driver": "asset_quality_cycle",
                "metric_or_observation": "NPL and provision",
                "proposed_state_tag": "bank_asset_quality_watch",
                "coverage_status": "available",
            },
            {
                "industry": "bank",
                "driver": "dividend_sustainability",
                "metric_or_observation": "CET1 and ROE",
                "proposed_state_tag": "bank_dividend_watch",
                "coverage_status": "available",
            },
        ],
    )
    _write_csv(
        knowledge / "v5c_power_driver_metric_map.csv",
        [
            {
                "industry": "utilities_electricity",
                "driver": "capex_debt_cashflow",
                "metric_or_observation": "OCF and capex",
                "proposed_state_tag": "power_cashflow_watch",
                "coverage_status": "available",
            }
        ],
    )

    v5f = root / "v5f_structural_rough_screen" / "current"
    v5f.mkdir(parents=True)
    _write_csv(
        v5f / "v5f_structural_rough_screen_metrics.csv",
        [{"version_id": "internal_subsleeve_mom12_70_30", "strategy_return": 1.2}],
    )


def _p1_rows(code: str, sleeve: str) -> list[dict[str, object]]:
    base = {"bank": 1.0, "utilities_electricity": 0.2, "port_rail_infrastructure": 0.1}[sleeve]
    rows = []
    for idx, date in enumerate(["2021-05-06", "2021-07-01", "2021-10-08"]):
        step = idx * 0.1
        rows.append(
            {
                "trade_date": date,
                "code": code,
                "sleeve_id": sleeve,
                "selected_rank": 1,
                "target_weight_signal": 0.03,
                "actual_weight": 0.03,
                "financial_visible_date": date,
                "visible_date_status": "pass",
                "factor_visible_date": date,
                "dividend_yield_decimal": 0.03,
                "operating_cash_flow_yield": base + step,
                "cash_collection_quality": base + step,
                "operating_cash_flow_to_net_profit": base + step,
                "return_on_equity_ttm": 10 + idx,
                "net_profit_margin": 5 + idx,
                "non_performing_loan_ratio": 1.5 - step,
                "provision_coverage_ratio": 200 + idx * 5,
                "core_tier_1_capital_adequacy_ratio": 10 + idx,
                "capex_burden": 0.4 - step * 0.1,
                "asset_liability_ratio": 0.6 - step * 0.1,
                "quality_status": "pass",
            }
        )
    return rows


def _valuation_row(row: dict[str, object]) -> dict[str, object]:
    return {
        "trade_date": row["trade_date"],
        "code": row["code"],
        "sleeve_id": row["sleeve_id"],
        "valuation_state": "neutral",
        "valuation_cheapness_score": 0.5,
        "valuation_overheat_score": 0.2,
        "pit_status": "pass",
    }


def _crowding_row(row: dict[str, object]) -> dict[str, object]:
    return {
        "trade_date": row["trade_date"],
        "code": row["code"],
        "sleeve_id": row["sleeve_id"],
        "money_percentile_252d": 0.5,
        "price_return_20d": 0.01,
        "price_return_60d": 0.03,
        "crowding_state": "normal",
        "pit_status": "pass",
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
