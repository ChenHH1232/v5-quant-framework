from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5c_bank_power_v5f_attribution_runner import run


class V5cBankPowerV5fAttributionRunnerTest(unittest.TestCase):
    def test_generates_bank_power_attribution_without_trading_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_inputs(root)

            summary_path = run(root)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "completed_bank_power_v5f_platform_attribution")
            self.assertGreater(summary["bank_stock_pnl_delta_pct_initial_cash"], 0)
            self.assertGreater(summary["power_stock_pnl_delta_pct_initial_cash"], 0)
            self.assertFalse(summary["direct_v5c_model_lift_tested"])
            self.assertFalse(summary["can_trigger_trade"])
            self.assertFalse(summary["accepted"])
            self.assertEqual(
                summary["pm_gate_decision"],
                "bank_power_attribution_positive_proceed_to_P1_state_panels_observation_only",
            )

            out = root / "v5c_bank_power_v5f_attribution" / "current"
            rows = _read_csv(out / "v5c_bank_power_platform_sleeve_pnl_comparison.csv")
            self.assertIn("bank", {row["sleeve"] for row in rows})
            self.assertIn("utilities_electricity", {row["sleeve"] for row in rows})


def _write_minimal_inputs(root: Path) -> None:
    weights = root / "v5f_structural_rough_screen" / "current"
    weights.mkdir(parents=True)
    _write_csv(
        weights / "v5f_structural_rough_screen_weights.csv",
        [
            {"version_id": "internal_subsleeve_mom12_70_30", "rebalance_date": "2021-05-06", "code": "600000.XSHG", "sleeve": "bank"},
            {"version_id": "internal_subsleeve_mom12_70_30", "rebalance_date": "2021-05-06", "code": "600900.XSHG", "sleeve": "utilities_electricity"},
            {"version_id": "v57f_startup_preload_repaired_baseline", "rebalance_date": "2021-05-06", "code": "600000.XSHG", "sleeve": "bank"},
            {"version_id": "v57f_startup_preload_repaired_baseline", "rebalance_date": "2021-05-06", "code": "600900.XSHG", "sleeve": "utilities_electricity"},
        ],
    )

    attr = root / "v5f_joinquant_platform_attribution" / "current"
    attr.mkdir(parents=True)
    _write_csv(
        attr / "v5f_joinquant_platform_clean_edge_comparison.csv",
        [{"metric": "total_return_pct", "platform_primary": 110.0, "platform_baseline": 104.0, "primary_minus_baseline": 6.0, "unit": "pct_points"}],
    )

    export = root / "data" / "joinquant_exports" / "v5f_internal_subsleeve_mom12_70_30" / "historical_platform_attribution"
    for folder in [
        "position_primary_internal_subsleeve_mom12_70_30",
        "position_baseline_v57f_startup_preload_repaired_baseline",
        "transaction_primary_internal_subsleeve_mom12_70_30",
        "transaction_baseline_v57f_startup_preload_repaired_baseline",
    ]:
        (export / folder).mkdir(parents=True)

    _write_position(
        export / "position_primary_internal_subsleeve_mom12_70_30" / "position.csv",
        bank_pnl=80_000,
        power_pnl=70_000,
    )
    _write_position(
        export / "position_baseline_v57f_startup_preload_repaired_baseline" / "position.csv",
        bank_pnl=20_000,
        power_pnl=10_000,
    )
    _write_transaction(export / "transaction_primary_internal_subsleeve_mom12_70_30" / "transaction.csv")
    _write_transaction(export / "transaction_baseline_v57f_startup_preload_repaired_baseline" / "transaction.csv")


def _write_position(path: Path, bank_pnl: float, power_pnl: float) -> None:
    text = "\n".join(
        [
            "日期,品种,标的,多空,数量,可用数量,收盘价/结算价,市值/价值,盈亏/逐笔浮盈,开仓均价,持仓均价（期货）,保证金,当日盈亏,今手数,盈亏占比,仓位占比",
            f"2021-05-06,股票,银行A(600000.XSHG),多,100股,0股,10,1000,0,10,-,0,{bank_pnl},100股,0%,2000000,5%",
            f"2021-05-06,股票,电力A(600900.XSHG),多,100股,0股,10,1000,0,10,-,0,{power_pnl},100股,0%,2000000,5%",
        ]
    )
    path.write_text(text, encoding="gb18030")


def _write_transaction(path: Path) -> None:
    text = "\n".join(
        [
            "日期,委托时间,品种,标的,交易类型,下单类型,成交数量,成交价,成交额,委托数量,委托价格,平仓盈亏,手续费,状态,最后更新时间",
            "2021-05-06,09:35:00,股票,银行A(600000.XSHG),买,市价单,100股,10,1000,100股,-,0,5,全部成交,2021-05-06 09:35:00",
            "2021-05-06,09:35:00,股票,电力A(600900.XSHG),买,市价单,100股,10,1000,100股,-,0,5,全部成交,2021-05-06 09:35:00",
        ]
    )
    path.write_text(text, encoding="gb18030")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
