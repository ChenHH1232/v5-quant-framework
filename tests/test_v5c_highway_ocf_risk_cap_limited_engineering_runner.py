from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from v5.v5c_highway_ocf_risk_cap_limited_engineering_runner import (
    PRIMARY,
    VERSION_ID,
    _apply_risk_cap,
    _risk_flags,
    run_v5c_highway_ocf_risk_cap_limited_engineering,
)


class V5cHighwayOcfRiskCapLimitedEngineeringRunnerTest(unittest.TestCase):
    def test_runner_blocks_when_inputs_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_v5c_highway_ocf_risk_cap_limited_engineering(Path(tmp))

        self.assertEqual(summary["status"], "blocked_missing_required_inputs")
        self.assertGreater(summary["fatal_blocker_count"], 0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["parameter_scan_used"])

    def test_risk_flags_use_frozen_ocf_fields_and_pit(self) -> None:
        weights = pd.DataFrame(
            [
                _weight("2021-05-06", "000001.XSHE", "highway_infrastructure", 0.04, 0.06),
                _weight("2021-05-06", "000002.XSHE", "highway_infrastructure", 0.04, 0.04),
                _weight("2021-05-06", "000003.XSHE", "highway_infrastructure", 0.04, 0.03),
                _weight("2021-05-06", "000004.XSHE", "highway_infrastructure", 0.04, 0.03),
            ]
        )
        panel = pd.DataFrame(
            [
                _panel("2021-05-06", "000001.XSHE", 0.01, 2.0, "2021-04-30"),
                _panel("2021-05-06", "000002.XSHE", 0.04, 0.5, "2021-04-30"),
                _panel("2021-05-06", "000003.XSHE", 0.08, 3.0, "2021-04-30"),
                _panel("2021-05-06", "000004.XSHE", 0.09, 4.0, "2021-05-07"),
            ]
        )

        rows = _risk_flags(weights, panel)
        by_code = {row["code"]: row for row in rows}

        self.assertTrue(by_code["000001.XSHE"]["ocf_yield_bottom_tercile"])
        self.assertTrue(by_code["000001.XSHE"]["flag_ocf_risk"])
        self.assertTrue(by_code["000002.XSHE"]["ocf_to_np_below_median"])
        self.assertTrue(by_code["000002.XSHE"]["flag_ocf_risk"])
        self.assertFalse(by_code["000003.XSHE"]["flag_ocf_risk"])
        self.assertEqual(by_code["000004.XSHE"]["pit_status"], "fail_visible_after_rebalance")
        self.assertFalse(by_code["000004.XSHE"]["flag_ocf_risk"])

    def test_apply_risk_cap_caps_overweight_and_redistributes_same_sleeve(self) -> None:
        weights = pd.DataFrame(
            [
                _weight("2021-05-06", "000001.XSHE", "highway_infrastructure", 0.04, 0.06),
                _weight("2021-05-06", "000002.XSHE", "highway_infrastructure", 0.04, 0.04),
                _weight("2021-05-06", "000003.XSHE", "utilities_electricity", 0.10, 0.12),
            ]
        )
        risk_flags = [
            {"rebalance_date": "2021-05-06", "code": "000001.XSHE", "flag_ocf_risk": True, "risk_status": "flagged"},
            {"rebalance_date": "2021-05-06", "code": "000002.XSHE", "flag_ocf_risk": False, "risk_status": "clear"},
        ]

        adjusted, events = _apply_risk_cap(weights, risk_flags)
        by_code = {row["code"]: row for row in adjusted}

        self.assertEqual(by_code["000001.XSHE"]["version_id"], VERSION_ID)
        self.assertAlmostEqual(float(by_code["000001.XSHE"]["target_weight"]), 0.04)
        self.assertAlmostEqual(float(by_code["000002.XSHE"]["target_weight"]), 0.06)
        self.assertAlmostEqual(float(by_code["000003.XSHE"]["target_weight"]), 0.12)
        self.assertAlmostEqual(
            sum(float(row["target_weight"]) for row in adjusted if row["sleeve"] == "highway_infrastructure"),
            0.10,
        )
        self.assertTrue(any(row["cap_action"] == "cap_applied" for row in events))
        self.assertTrue(any(row["cap_action"] == "redistribution_receiver" for row in events))

    def test_capex_and_fcf_do_not_drive_v1_flags(self) -> None:
        weights = pd.DataFrame(
            [
                _weight("2021-05-06", "000001.XSHE", "highway_infrastructure", 0.04, 0.06),
                _weight("2021-05-06", "000002.XSHE", "highway_infrastructure", 0.04, 0.04),
                _weight("2021-05-06", "000003.XSHE", "highway_infrastructure", 0.04, 0.04),
            ]
        )
        panel = pd.DataFrame(
            [
                {
                    **_panel("2021-05-06", "000001.XSHE", 0.20, 3.0, "2021-04-30"),
                    "free_cash_flow_yield": -999.0,
                    "capex_burden": 999.0,
                },
                _panel("2021-05-06", "000002.XSHE", 0.01, 2.0, "2021-04-30"),
                _panel("2021-05-06", "000003.XSHE", 0.10, 1.0, "2021-04-30"),
            ]
        )

        row = {item["code"]: item for item in _risk_flags(weights, panel)}["000001.XSHE"]

        self.assertFalse(row["flag_ocf_risk"])
        self.assertNotIn("free_cash_flow_yield", row)
        self.assertNotIn("capex_burden", row)


def _weight(date: str, code: str, sleeve: str, base: float, target: float) -> dict[str, object]:
    return {
        "version_id": PRIMARY,
        "family": "v57f_pool_internal_subsleeve",
        "rebalance_date": date,
        "code": code,
        "sleeve": sleeve,
        "base_target_weight": base,
        "target_weight": target,
        "weight_delta": target - base,
        "mom_12_1": 0.1,
        "mr_60d": 0.0,
        "bucket": "test_bucket",
        "sleeve_weight_preserved": True,
        "new_stock_selected": False,
        "accepted": False,
    }


def _panel(date: str, code: str, ocf_yield: float, ocf_to_np: float, visible: str) -> dict[str, object]:
    return {
        "trade_date": date,
        "code": code,
        "operating_cash_flow_yield": ocf_yield,
        "operating_cash_flow_to_net_profit": ocf_to_np,
        "factor_visible_date": visible,
        "factor_visibility_source": "unit_test",
    }


if __name__ == "__main__":
    unittest.main()
