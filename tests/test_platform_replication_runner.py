from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.platform_replication_runner import run_platform_replication_packet


class PlatformReplicationRunnerTests(unittest.TestCase):
    def test_missing_platform_rebalance_date_blocks_as_data_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = root / "local" / "strategy"
            local.mkdir(parents=True)
            self._write_local_run(local, signal_dates=["2026-01-05"])
            panel = root / "panel.csv"
            self._write_csv(panel, ["trade_date", "code"], [{"trade_date": "2026-01-05", "code": "A"}])
            jq_daily = root / "daily.csv"
            self._write_joinquant_daily(jq_daily)
            jq_tx = root / "tx.csv"
            self._write_joinquant_transactions(jq_tx, dates=["2026-01-05", "2026-04-01"])

            report = run_platform_replication_packet(
                local,
                jq_daily,
                root / "packet",
                "test_strategy",
                panel_csv=panel,
                joinquant_transaction_csv=jq_tx,
            )
            packet = json.loads((report.parent / "platform_replication_packet.json").read_text(encoding="utf-8"))

        self.assertEqual(packet["status"], "data_gap")
        self.assertIn("2026-04-01", packet["coverage"]["missing_signal_dates"])

    def test_complete_small_packet_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = root / "local" / "strategy"
            local.mkdir(parents=True)
            self._write_local_run(local, signal_dates=["2026-01-05", "2026-04-01"])
            panel = root / "panel.csv"
            self._write_csv(
                panel,
                ["trade_date", "code"],
                [
                    {"trade_date": "2026-01-05", "code": "A"},
                    {"trade_date": "2026-04-01", "code": "A"},
                ],
            )
            jq_daily = root / "daily.csv"
            self._write_joinquant_daily(jq_daily)
            jq_tx = root / "tx.csv"
            self._write_joinquant_transactions(jq_tx, dates=["2026-01-05", "2026-04-01"])
            jq_pos = root / "pos.csv"
            self._write_joinquant_positions(jq_pos)

            report = run_platform_replication_packet(
                local,
                jq_daily,
                root / "packet",
                "test_strategy",
                panel_csv=panel,
                joinquant_transaction_csv=jq_tx,
                joinquant_position_csv=jq_pos,
            )
            packet = json.loads((report.parent / "platform_replication_packet.json").read_text(encoding="utf-8"))

        self.assertEqual(packet["status"], "platform_replication_passed")
        self.assertEqual(packet["coverage"]["latest_expected_rebalance_date"], "2026-04-01")
        self.assertTrue(packet["local_rebalance_order_health"]["passed"])
        self.assertEqual(packet["local_rebalance_order_health"]["rebalance_signal_count"], 2)
        self.assertEqual(packet["position_rebalance_summary"]["code_mismatch_dates"], 0)

    def test_missing_rebalance_order_health_blocks_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = root / "local" / "strategy"
            local.mkdir(parents=True)
            self._write_local_run(local, signal_dates=["2026-01-05", "2026-04-01"], include_order_health=False)
            panel = root / "panel.csv"
            self._write_csv(
                panel,
                ["trade_date", "code"],
                [
                    {"trade_date": "2026-01-05", "code": "A"},
                    {"trade_date": "2026-04-01", "code": "A"},
                ],
            )
            jq_daily = root / "daily.csv"
            self._write_joinquant_daily(jq_daily)
            jq_tx = root / "tx.csv"
            self._write_joinquant_transactions(jq_tx, dates=["2026-01-05", "2026-04-01"])
            jq_pos = root / "pos.csv"
            self._write_joinquant_positions(jq_pos)

            report = run_platform_replication_packet(
                local,
                jq_daily,
                root / "packet",
                "test_strategy",
                panel_csv=panel,
                joinquant_transaction_csv=jq_tx,
                joinquant_position_csv=jq_pos,
            )
            packet = json.loads((report.parent / "platform_replication_packet.json").read_text(encoding="utf-8"))

        self.assertEqual(packet["status"], "data_gap")
        self.assertFalse(packet["local_rebalance_order_health"]["passed"])
        self.assertEqual(packet["local_rebalance_order_health"]["reason"], "missing rebalance_order_health.csv")

    def test_unhealthy_rebalance_order_health_blocks_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = root / "local" / "strategy"
            local.mkdir(parents=True)
            self._write_local_run(local, signal_dates=["2026-01-05", "2026-04-01"], unhealthy_order_health=True)
            panel = root / "panel.csv"
            self._write_csv(
                panel,
                ["trade_date", "code"],
                [
                    {"trade_date": "2026-01-05", "code": "A"},
                    {"trade_date": "2026-04-01", "code": "A"},
                ],
            )
            jq_daily = root / "daily.csv"
            self._write_joinquant_daily(jq_daily)
            jq_tx = root / "tx.csv"
            self._write_joinquant_transactions(jq_tx, dates=["2026-01-05", "2026-04-01"])
            jq_pos = root / "pos.csv"
            self._write_joinquant_positions(jq_pos)

            report = run_platform_replication_packet(
                local,
                jq_daily,
                root / "packet",
                "test_strategy",
                panel_csv=panel,
                joinquant_transaction_csv=jq_tx,
                joinquant_position_csv=jq_pos,
            )
            packet = json.loads((report.parent / "platform_replication_packet.json").read_text(encoding="utf-8"))

        self.assertEqual(packet["status"], "data_gap")
        self.assertFalse(packet["local_rebalance_order_health"]["passed"])
        self.assertEqual(packet["local_rebalance_order_health"]["blocker_count"], 1)

    def _write_local_run(
        self,
        local: Path,
        signal_dates: list[str],
        include_order_health: bool = True,
        unhealthy_order_health: bool = False,
    ) -> None:
        self._write_csv(
            local / "daily_returns.csv",
            ["trade_date", "strategy_nav", "benchmark_nav", "cash_weight"],
            [
                {"trade_date": "2026-01-05", "strategy_nav": "1.00", "benchmark_nav": "1.00", "cash_weight": "0.1"},
                {"trade_date": "2026-04-01", "strategy_nav": "1.05", "benchmark_nav": "1.04", "cash_weight": "0.1"},
            ],
        )
        self._write_csv(
            local / "rebalance_signals.csv",
            ["trade_date", "selected_codes"],
            [{"trade_date": date, "selected_codes": "000001.XSHE"} for date in signal_dates],
        )
        self._write_csv(
            local / "trades.csv",
            ["trade_date", "code", "side", "amount", "price", "value", "commission"],
            [
                {"trade_date": "2026-01-05", "code": "000001.XSHE", "side": "buy", "amount": "100", "price": "10", "value": "1000", "commission": "5"},
                {"trade_date": "2026-04-01", "code": "000001.XSHE", "side": "buy", "amount": "100", "price": "10", "value": "1000", "commission": "5"},
            ],
        )
        self._write_csv(
            local / "holdings.csv",
            ["trade_date", "code", "amount", "close", "actual_weight"],
            [
                {"trade_date": "2026-01-05", "code": "000001.XSHE", "amount": "100", "close": "10", "actual_weight": "0.1"},
                {"trade_date": "2026-04-01", "code": "000001.XSHE", "amount": "200", "close": "10", "actual_weight": "0.2"},
            ],
        )
        self._write_csv(local / "dividends.csv", ["trade_date", "code", "dividend_cash"], [])
        if include_order_health:
            rows = [
                {
                    "trade_date": date,
                    "order_health_status": "normal_ordered",
                    "selected_count": "1",
                    "selected_codes": "000001.XSHE",
                    "executed_order_count": "1",
                    "buy_order_count": "1",
                    "sell_order_count": "0",
                    "skipped_order_count": "0",
                    "buy_skipped_count": "0",
                    "sell_skipped_count": "0",
                    "buy_turnover": "1000",
                    "sell_turnover": "0",
                    "holding_count_after_rebalance": "1",
                    "cash_weight_after_rebalance": "0.1",
                    "portfolio_value_after_rebalance": "100000",
                    "diagnosis": "ok",
                }
                for date in signal_dates
            ]
            if unhealthy_order_health:
                rows[0]["order_health_status"] = "no_order_no_position"
                rows[0]["executed_order_count"] = "0"
                rows[0]["holding_count_after_rebalance"] = "0"
                rows[0]["buy_turnover"] = "0"
            self._write_csv(
                local / "rebalance_order_health.csv",
                list(rows[0].keys()),
                rows,
            )

    def _write_joinquant_daily(self, path: Path) -> None:
        self._write_csv(
            path,
            ["时间", "基准收益", "策略收益"],
            [
                {"时间": "2026-01-05 16:00:00", "基准收益": "0", "策略收益": "0"},
                {"时间": "2026-04-01 16:00:00", "基准收益": "4", "策略收益": "5"},
            ],
        )

    def _write_joinquant_transactions(self, path: Path, dates: list[str]) -> None:
        rows = []
        for date in dates:
            rows.append(
                {
                    "日期": date,
                    "委托时间": "09:40:00",
                    "品种": "股票",
                    "标的": "平安银行(000001.XSHE)",
                    "交易类型": "买",
                    "下单类型": "市价单",
                    "成交数量": "100股",
                    "成交价": "10",
                    "成交额": "1000",
                    "委托数量": "100股",
                    "委托价格": "-",
                    "平仓盈亏": "0",
                    "手续费": "5",
                    "状态": "全部成交",
                    "最后更新时间": f"{date} 09:40:00",
                }
            )
        self._write_csv(path, list(rows[0].keys()), rows)

    def _write_joinquant_positions(self, path: Path) -> None:
        fieldnames = [
            "日期",
            "品种",
            "标的",
            "多空",
            "数量",
            "可用数量",
            "收盘价/结算价",
            "市值/价值",
            "盈亏/逐笔浮盈",
            "开仓均价",
            "持仓均价（期货）",
            "保证金",
            "当日盈亏",
            "今手数",
            "盈亏占比",
            "仓位占比",
        ]
        rows = [
            {"日期": "2026-01-05", "标的": "平安银行(000001.XSHE)", "数量": "100", "收盘价/结算价": "10", "市值/价值": "1000", "仓位占比": "10"},
            {"日期": "2026-04-01", "标的": "平安银行(000001.XSHE)", "数量": "200", "收盘价/结算价": "10", "市值/价值": "2000", "仓位占比": "20"},
        ]
        normalized = [{name: row.get(name, "") for name in fieldnames} for row in rows]
        self._write_csv(path, fieldnames, normalized)

    def _write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
