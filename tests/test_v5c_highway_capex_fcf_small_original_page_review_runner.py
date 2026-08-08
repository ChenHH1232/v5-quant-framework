from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5c_highway_capex_fcf_small_original_page_review_runner import (
    _cycle_refresh,
    _keyword_hits,
    _review_status,
    _sidecar_refresh,
    run_v5c_highway_capex_fcf_small_original_page_review,
)


class V5cHighwayCapexFcfSmallOriginalPageReviewRunnerTest(unittest.TestCase):
    def test_runner_blocks_when_inputs_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_v5c_highway_capex_fcf_small_original_page_review(Path(tmp))

        self.assertEqual(summary["status"], "blocked_missing_required_inputs")
        self.assertGreater(summary["fatal_blocker_count"], 0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["backtest_started"])

    def test_runner_keeps_capex_fcf_as_data_gate_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_inputs(root)

            summary = run_v5c_highway_capex_fcf_small_original_page_review(root)

            self.assertEqual(summary["status"], "completed_data_gate_only")
            self.assertFalse(summary["highway_capex_fcf_model_use_allowed"])
            self.assertTrue(summary["sidecar_observation_only"])
            self.assertTrue(summary["cycle_sector_data_gate_only"])

            out = root / "v5c_highway_capex_fcf_small_original_page_review" / "current"
            with (out / "v5c_highway_capex_fcf_pm_gate_decision.csv").open(
                "r", encoding="utf-8-sig", newline=""
            ) as handle:
                decision = list(csv.DictReader(handle))[0]
            self.assertEqual(
                decision["pm_gate_decision"],
                "capex_fcf_small_original_page_review_completed_data_gate_only",
            )
            self.assertEqual(decision["highway_capex_fcf_model_use_allowed"], "False")

    def test_keyword_hits_detect_cashflow_evidence(self) -> None:
        text = "合并现金流量表 单位：元 经营活动产生的现金流量净额 购建固定资产、无形资产和其他长期资产支付的现金"
        hits = _keyword_hits(text)

        self.assertTrue(hits["cash_flow_table_keyword_hit"])
        self.assertTrue(hits["unit_keyword_hit"])
        self.assertTrue(hits["cfo_keyword_hit"])
        self.assertTrue(hits["capex_keyword_hit"])

    def test_review_status_requires_pit_clean_but_never_enables_model(self) -> None:
        evidence = {
            "pdf_exists": True,
            "text_extract_status": "text_extracted",
            "cash_flow_table_keyword_hit": True,
            "unit_keyword_hit": True,
        }
        queue_row = {"first_affected_trade_date": "2020-07-01"}
        panel_row = {
            "capex_original_visible_date": "2020-04-30",
            "capex_fcf_status": "pass_pit_original_statement_extracted",
            "free_cash_flow_yield": "0.01",
            "capex_burden": "0.02",
        }

        self.assertEqual(
            _review_status(queue_row, panel_row, evidence),
            "reviewed_pit_clean_capex_fcf_available_not_model_input",
        )

    def test_sidecar_and_cycle_refresh_do_not_allow_backtest(self) -> None:
        sidecar = _sidecar_refresh([{"sidecar_id": "gas", "sector_id": "gas_water_operators", "status": "sidecar_observation_only"}])
        cycle = _cycle_refresh([{"sector_id": "cement", "status": "cycle_data_gate_only"}])

        self.assertEqual(sidecar[0]["updated_status"], "continue_sidecar_observation_only")
        self.assertFalse(sidecar[0]["backtest_allowed"])
        self.assertEqual(cycle[0]["updated_status"], "continue_pit_state_data_gate_only_no_backtest")
        self.assertFalse(cycle[0]["backtest_allowed"])


def _seed_inputs(root: Path) -> None:
    freeze = root / "v5c_highway_ocf_risk_cap_rule_freeze" / "current"
    capex = root / "v5c_infra_capex_original_statement_extraction" / "current"
    sidecar = root / "v5c_sidecar_observation_enhancement" / "current"
    cycle = root / "v5c_cycle_sector_data_gate_queue" / "current"
    riskcap = root / "v5c_highway_ocf_risk_cap_v1_limited_engineering" / "current"
    for path in [freeze, capex, sidecar, cycle, riskcap]:
        path.mkdir(parents=True, exist_ok=True)

    _write_csv(
        freeze / "v5c_highway_capex_fcf_original_page_review_queue.csv",
        [
            {
                "priority": "P0_sample_review",
                "code": "600001.XSHG",
                "sector_id": "highway_infrastructure",
                "report_period": "2020-03-31",
                "first_affected_trade_date": "2020-07-01",
                "capex_fcf_status": "source_pdf_missing",
                "capex_source_pdf": "",
                "capex_source_page_number": "",
                "review_goal": "confirm original table",
                "model_use_allowed": "False",
            }
        ],
    )
    _write_csv(
        capex / "v5c_infra_capex_strict_panel.csv",
        [
            {
                "trade_date": "2020-07-01",
                "code": "600001.XSHG",
                "sector_id": "highway_infrastructure",
                "cashflow_report_period": "2020-03-31",
                "capex_original_visible_date": "2020-04-30",
                "cashflow_factor_visible_date": "2020-04-30",
                "operating_cash_flow_net_original": "1",
                "capex_cash_paid_original": "2",
                "free_cash_flow_yield": "0.01",
                "capex_burden": "0.02",
                "capex_source_unit": "cny",
                "capex_fcf_status": "source_pdf_missing",
            }
        ],
    )
    _write_csv(
        capex / "v5c_infra_capex_blockers.csv",
        [{"blocker_id": "financial_report_pdf_unavailable", "code": "600001.XSHG", "report_period": "2020-03-31", "detail": "missing_pdf_url"}],
    )
    _write_csv(
        sidecar / "v5c_sidecar_observation_enhancement_queue.csv",
        [{"sidecar_id": "gas_water_observation_enhancement", "sector_id": "gas_water_operators", "status": "sidecar_observation_only"}],
    )
    _write_csv(
        cycle / "v5c_cycle_sector_data_gate_queue.csv",
        [{"sector_id": "cement", "status": "cycle_data_gate_only", "required_state_data": "regional_price"}],
    )
    (riskcap / "v5c_highway_ocf_risk_cap_limited_summary.json").write_text(
        json.dumps({"pm_gate_decision": "diagnostic_only_no_incremental_value"}),
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
