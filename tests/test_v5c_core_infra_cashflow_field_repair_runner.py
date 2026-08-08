from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from v5.v5c_core_infra_cashflow_field_repair_runner import (
    _enrich_rows,
    _field_coverage,
    _latest_visible_financial_record,
    run_v5c_core_infra_cashflow_field_repair,
)


class V5cCoreInfraCashflowFieldRepairRunnerTest(unittest.TestCase):
    def test_latest_visible_financial_record_respects_pub_date(self) -> None:
        records = [
            {"pubDate": "2019-04-25", "statDate": "2019-03-31", "CFOToNP": "1.0"},
            {"pubDate": "2018-10-31", "statDate": "2018-09-30", "CFOToNP": "0.8"},
        ]

        selected = _latest_visible_financial_record(records, "2019-04-01")

        self.assertEqual(selected["statDate"], "2018-09-30")

    def test_enrich_rows_fills_ocf_quality_but_not_capex(self) -> None:
        rows = [
            {
                "sector_id": "highway_infrastructure",
                "scope": "strict_pit_universe",
                "trade_date": "2019-07-01",
                "code": "600035.XSHG",
                "close": "4.0",
                "future_return": "0.1",
            }
        ]
        records = {
            "600035.XSHG": [
                {
                    "pubDate": "2019-04-30",
                    "statDate": "2019-03-31",
                    "CFOToOR": "0.30",
                    "CFOToGr": "0.31",
                    "CFOToNP": "1.5",
                    "roeAvg": "0.08",
                    "ebitToInterest": "12",
                    "liabilityToAsset": "0.45",
                    "netProfit": "100",
                    "totalShare": "1000",
                }
            ]
        }

        enriched = _enrich_rows(rows, records)

        self.assertEqual(enriched[0]["ocf_to_revenue"], "0.3")
        self.assertEqual(enriched[0]["cash_collection_quality"], "0.31")
        self.assertEqual(enriched[0]["operating_cash_flow_yield"], "0.0375")
        self.assertEqual(enriched[0]["capex_burden"], "")
        self.assertEqual(enriched[0]["cashflow_repair_status"], "pass_ocf_quality_capex_blocked")

    def test_field_coverage_marks_capex_source_blocked(self) -> None:
        rows = [
            {
                "sector_id": "port_rail_infrastructure",
                "scope": "strict_pit_universe",
                "ocf_to_revenue": "0.2",
                "cash_collection_quality": "0.2",
                "operating_cash_flow_yield": "0.03",
                "return_on_equity_ttm": "0.08",
                "operating_cash_flow_to_net_profit": "1.1",
                "interest_coverage": "10",
                "asset_liability_ratio": "0.5",
                "free_cash_flow_yield": "",
                "capex_burden": "",
            }
        ]

        coverage = _field_coverage(rows)
        capex = [row for row in coverage if row["field"] == "capex_burden"][0]

        self.assertEqual(capex["field_status"], "missing")
        self.assertEqual(capex["source_status"], "source_blocked")

    def test_runner_blocks_when_inputs_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_v5c_core_infra_cashflow_field_repair(Path(tmp), fetch_baostock=False)

        self.assertEqual(summary["status"], "blocked_missing_inputs")
        self.assertGreater(summary["fatal_blocker_count"], 0)


if __name__ == "__main__":
    unittest.main()
