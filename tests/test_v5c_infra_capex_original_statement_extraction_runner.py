from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from v5.v5c_infra_capex_original_statement_extraction_runner import (
    _apply_capex_panel,
    _infer_report_period,
    _is_usable_financial_report_title,
    _parse_value_after_term,
    run_v5c_infra_capex_original_statement_extraction,
)


class V5cInfraCapexOriginalStatementExtractionRunnerTest(unittest.TestCase):
    def test_infer_report_period_for_cninfo_titles(self) -> None:
        self.assertEqual(_infer_report_period("2020年第一季度报告全文"), "2020-03-31")
        self.assertEqual(_infer_report_period("2020年半年度报告"), "2020-06-30")
        self.assertEqual(_infer_report_period("2020年第三季度报告"), "2020-09-30")
        self.assertEqual(_infer_report_period("2020年年度报告（更新后）"), "2020-12-31")

    def test_title_filter_blocks_summary_body_and_cancelled(self) -> None:
        self.assertTrue(_is_usable_financial_report_title("2020年半年度报告"))
        self.assertFalse(_is_usable_financial_report_title("2020年半年度报告摘要"))
        self.assertFalse(_is_usable_financial_report_title("2020年第三季度报告正文"))
        self.assertFalse(_is_usable_financial_report_title("2020年年度报告（已取消）"))

    def test_parse_value_after_cashflow_terms(self) -> None:
        text = (
            "合并现金流量表 单位：元\n"
            "经营活动产生的现金流量净额 1,000,000.00 900,000.00\n"
            "购建固定资产、无形资产和其他长期资产支付的现金 250,000.00 200,000.00\n"
        )

        cfo = _parse_value_after_term(text, "经营活动产生的现金流量净额")
        capex = _parse_value_after_term(text, "购建固定资产、无形资产和其他长期资产支付的现金")

        self.assertEqual(cfo, 1_000_000.0)
        self.assertEqual(capex, 250_000.0)

    def test_apply_capex_panel_respects_visible_date_and_calculates_ratios(self) -> None:
        rows = [
            {
                "scope": "strict_pit_universe",
                "sector_id": "highway_infrastructure",
                "trade_date": "2020-07-01",
                "code": "600035.XSHG",
                "cashflow_report_period": "2020-03-31",
                "operating_cash_flow_yield": "0.08",
            },
            {
                "scope": "strict_pit_universe",
                "sector_id": "highway_infrastructure",
                "trade_date": "2020-04-01",
                "code": "600035.XSHG",
                "cashflow_report_period": "2020-03-31",
                "operating_cash_flow_yield": "0.08",
            },
        ]
        extracted = [
            {
                "code": "600035.XSHG",
                "report_period": "2020-03-31",
                "pit_visible_date": "2020-04-30",
                "operating_cash_flow_net_original": "1000",
                "capex_cash_paid_original": "250",
                "source_page_number": "10",
                "unit": "cny",
                "local_pdf_path": "sample.pdf",
                "extraction_status": "pass_original_statement_extracted",
            }
        ]

        panel = _apply_capex_panel(rows, extracted, "strict_pit_universe")

        self.assertEqual(panel[0]["capex_burden"], "0.25")
        self.assertEqual(panel[0]["free_cash_flow_yield"], "0.06")
        self.assertEqual(panel[0]["capex_fcf_status"], "pass_pit_original_statement_extracted")
        self.assertEqual(panel[1]["capex_fcf_status"], "missing_pit_original_statement_extraction")

    def test_runner_blocks_when_required_inputs_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_v5c_infra_capex_original_statement_extraction(Path(tmp))

        self.assertEqual(summary["status"], "blocked_missing_required_inputs")
        self.assertGreater(summary["fatal_blocker_count"], 0)


if __name__ == "__main__":
    unittest.main()
