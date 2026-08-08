from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5e_post_exit_5min_monitoring_data_gate_runner import run_v5e_post_exit_5min_monitoring_data_gate


class V5ePostExit5minMonitoringDataGateRunnerTest(unittest.TestCase):
    def test_runner_uses_medium_monitoring_scope_without_fetch_or_trade_trigger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root)

            summary = run_v5e_post_exit_5min_monitoring_data_gate(root, fetch=False)

            self.assertEqual(summary["status"], "completed_post_exit_5min_monitoring_data_gate")
            self.assertEqual(summary["pm_gate_decision"], "post_exit_5min_monitoring_ready_for_audit_not_trigger")
            self.assertEqual(summary["scope"], "medium_post_exit_to_next_rebalance")
            self.assertFalse(summary["full_holding_period_fetch"])
            self.assertFalse(summary["minute_data_used_for_trigger"])
            self.assertFalse(summary["trade_trigger_allowed"])
            self.assertFalse(summary["accepted"])
            self.assertFalse(summary["v57f_core_modified"])
            self.assertFalse(summary["network_fetch_started"])
            self.assertEqual(summary["required_stock_dates"], 3)
            self.assertEqual(summary["available_stock_dates"], 3)
            self.assertEqual(summary["missing_stock_dates"], 0)
            self.assertEqual(summary["fetch_task_count"], 0)
            self.assertEqual(summary["monitoring_metric_rows"], 3)
            self.assertEqual(summary["fatal_blocker_count"], 0)

            out = root / "v5e_post_exit_5min_monitoring_data_gate" / "current"
            self.assertTrue((out / "v5e_post_exit_5min_requirement.csv").exists())
            self.assertTrue((out / "v5e_post_exit_5min_monitoring_metrics.csv").exists())
            self.assertIn("不得用 5分钟走势触发新交易", (out / "v5e_post_exit_5min_prompt.md").read_text(encoding="utf-8"))

            with (out / "v5e_post_exit_5min_requirement.csv").open("r", encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual({row["trade_date"] for row in rows}, {"2024-01-02", "2024-01-03", "2024-01-04"})
            self.assertTrue(all(row["scope"] == "post_exit_to_next_rebalance_monitoring" for row in rows))
            self.assertTrue(all(row["trade_trigger_allowed"] == "False" for row in rows))

    def _write_fixture(self, root: Path) -> None:
        self._write_json(
            root / "v5e_cash_policy_review" / "current" / "v5e_cash_policy_review_summary.json",
            {"status": "completed_cash_policy_review"},
        )
        self._write_csv(
            root / "v5e_cash_policy_review" / "current" / "v5e_post_exit_5min_monitoring_spec.csv",
            [{"scope": "medium_post_exit_to_next_rebalance"}],
        )
        self._write_csv(
            root / "v5e_limited_engineering_loop" / "current" / "v5e_exit_action_log.csv",
            [
                {
                    "version_id": "v5e_profit_lock_main_20pct_sell50",
                    "code": "000001.XSHE",
                    "trigger_date": "2024-01-02",
                    "execution_date": "2024-01-03",
                }
            ],
        )
        run_dir = (
            root
            / "v5_startup_warmup_price_repair"
            / "current"
            / "runs"
            / "v57f_warmup_repaired_daily_backtest"
            / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
        )
        self._write_csv(
            run_dir / "daily_returns.csv",
            [{"trade_date": day} for day in ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]],
        )
        self._write_csv(run_dir / "rebalance_signals.csv", [{"trade_date": "2024-01-05"}])

        index_rows = []
        for day in ["2024-01-02", "2024-01-03", "2024-01-04"]:
            minute_path = root / "fixture_minute" / day / "000001_XSHE_5min_standardized.csv"
            self._write_csv(
                minute_path,
                [
                    {"date": day, "time": "09:35", "code": "000001.XSHE", "open": 10, "high": 10.1, "low": 9.9, "close": 10.0, "volume": 100, "amount": 1000},
                    {"date": day, "time": "09:40", "code": "000001.XSHE", "open": 10, "high": 10.2, "low": 9.9, "close": 10.1, "volume": 100, "amount": 1010},
                    {"date": day, "time": "10:00", "code": "000001.XSHE", "open": 10.1, "high": 10.3, "low": 10.0, "close": 10.2, "volume": 100, "amount": 1020},
                    {"date": day, "time": "14:55", "code": "000001.XSHE", "open": 10.2, "high": 10.4, "low": 10.1, "close": 10.3, "volume": 100, "amount": 1030},
                ],
            )
            index_rows.append({"code": "000001.XSHE", "trade_date": day, "path": str(minute_path.relative_to(root))})
        self._write_csv(
            root / "v5e_trigger_day_5min_execution_data_gate" / "current" / "v5e_exit_5min_standardized_index.csv",
            index_rows,
        )

    def _write_json(self, path: Path, data: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def _write_csv(self, path: Path, rows: list[dict[str, object]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
