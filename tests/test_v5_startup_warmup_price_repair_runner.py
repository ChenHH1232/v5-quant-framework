from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from v5.v5_startup_warmup_data_repair_runner import run_v5_startup_warmup_price_repair


class StartupWarmupPriceRepairRunnerTest(unittest.TestCase):
    def test_missing_local_warmup_prices_outputs_blocker_without_external_api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_workspace(root)

            summary = run_v5_startup_warmup_price_repair(root)

            self.assertEqual(summary["status"], "blocked_requires_user_authorized_warmup_daily_price_data")
            self.assertFalse(summary["local_warmup_data_found"])
            self.assertFalse(summary["repaired_price_files_generated"])
            self.assertFalse(summary["joinquant_started"])
            self.assertFalse(summary["baostock_started"])
            self.assertFalse(summary["tushare_started"])
            self.assertFalse(summary["v57f_core_logic_modified"])
            blocker_text = (
                root
                / "v5_startup_warmup_price_repair"
                / "current"
                / "v5_warmup_missing_price_blockers.csv"
            ).read_text(encoding="utf-8-sig")
            self.assertIn("local_predeployment_warmup_daily_prices_not_found", blocker_text)
            self.assertIn("external_data_authorization_required", blocker_text)


def _write_minimal_workspace(root: Path) -> None:
    for path in [
        root / "config",
        root / "src" / "v5",
        root / "validation_formal_v57f_etf_constructor",
        root / "local_daily_backtests_v57f_etf" / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f",
        root / "v5_startup_preload_repair" / "current",
        root / "data",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    for source_name in [
        "startup_preload.py",
        "low_volatility_factor_runner.py",
        "basket_constructor_runner.py",
        "basket_daily_backtest_runner.py",
        "v5_startup_preload_repair_runner.py",
    ]:
        (root / "src" / "v5" / source_name).write_text("# placeholder\n", encoding="utf-8")

    panel = root / "data" / "panel.csv"
    panel.write_text(
        "trade_date,code,dividend_yield,low_vol_score,volatility_120d,max_drawdown_120d,operating_cash_flow_yield\n"
        "2021-05-06,A,1,,,,1\n"
        "2021-10-08,A,1,1,0.1,0.1,1\n",
        encoding="utf-8",
    )
    prices = root / "data" / "prices.csv"
    prices.write_text(
        "date,code,open,close,high,low,volume,money,high_limit,low_limit,paused,price_adjustment,source\n"
        "2021-05-06,A,10,10,10,10,100,1000,11,9,0,raw,fixture\n"
        "2021-10-08,A,10,10,10,10,100,1000,11,9,0,raw,fixture\n",
        encoding="utf-8",
    )
    dividends = root / "data" / "dividends.csv"
    dividends.write_text("code,ex_date,pay_date,net_cash_per_share,stock_dividend_ratio\n", encoding="utf-8")
    config = {
        "project": "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f",
        "sectors": [
            {
                "sector_id": "bank",
                "strategy_id": "fixture",
                "panel_csv": str(panel),
                "price_csv": str(prices),
                "dividend_csv": str(dividends),
            }
        ],
        "signals": {
            "factors": [{"name": "operating_cash_flow_yield", "direction": "higher_is_better"}],
            "scoring": {"method": "weighted_composite", "min_factor_count": 1, "weights": {"operating_cash_flow_yield": 1}},
        },
        "portfolio": {
            "start_date": "2021-05-01",
            "end_date": "2021-10-08",
            "required_fields": ["low_vol_score", "volatility_120d", "dividend_yield"],
            "target_count": 1,
            "sector_weight_cap": 1.0,
            "single_stock_weight_cap": 1.0,
        },
        "governance": {"status": "sector_neutral_research_candidate_not_accepted"},
    }
    (root / "config" / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json").write_text(
        json.dumps(config),
        encoding="utf-8",
    )
    (root / "validation_formal_v57f_etf_constructor" / "basket_rebalance_signals.csv").write_text(
        "trade_date,code,sector_id,selected_rank,selected_count,target_weight\n"
        "2021-10-08,A,bank,1,1,1\n",
        encoding="utf-8",
    )
    summary = {
        "metrics": {"strategy_return": 0.1, "max_drawdown": 0.02},
        "trade_count": 1,
        "rebalance_order_health": {
            "first_executed_order_date": "2021-10-08",
            "first_position_date": "2021-10-08",
            "blocked_or_unfilled_rebalance_count": 0,
        },
    }
    (root / "local_daily_backtests_v57f_etf" / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f" / "summary.json").write_text(
        json.dumps(summary),
        encoding="utf-8",
    )
    for name in [
        "v5_startup_preload_repair_summary.json",
        "v5_startup_preload_repair_report.md",
        "v5_startup_data_coverage_audit.csv",
        "v5_startup_required_field_audit.csv",
        "v5_startup_blockers.csv",
    ]:
        path = root / "v5_startup_preload_repair" / "current" / name
        if name.endswith(".json"):
            path.write_text(json.dumps({"status": "blocked"}), encoding="utf-8")
        elif name.endswith(".csv"):
            path.write_text("status\nblocked\n", encoding="utf-8")
        else:
            path.write_text("# blocked\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
