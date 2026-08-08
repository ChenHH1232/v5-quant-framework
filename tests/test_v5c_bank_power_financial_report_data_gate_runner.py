from __future__ import annotations

import unittest

from v5.v5c_bank_power_financial_report_data_gate_runner import (
    BANK,
    POWER,
    _field_gate,
    _infer_report_period,
    _is_full_annual_report_title,
    _keyword_hits_from_pages,
    _pm_decision,
)


class V5cBankPowerFinancialReportDataGateRunnerTest(unittest.TestCase):
    def test_annual_report_title_filter(self) -> None:
        self.assertTrue(_is_full_annual_report_title("上海浦东发展银行股份有限公司2025年年度报告"))
        self.assertFalse(_is_full_annual_report_title("上海浦东发展银行股份有限公司2025年年度报告摘要"))
        self.assertFalse(_is_full_annual_report_title("关于2025年年度报告的更正公告"))
        self.assertEqual(_infer_report_period("长江电力2025年年度报告", "2026-04-30"), "2025-12-31")

    def test_keyword_hits_and_gate_decision(self) -> None:
        pages = [
            (1, "本行净息差为1.50%，不良贷款率保持稳定。"),
            (2, "公司燃料成本受煤价影响，上网电价和利用小时共同影响盈利。"),
        ]
        self.assertEqual(len(_keyword_hits_from_pages(pages, "净息差")), 1)
        self.assertEqual(len(_keyword_hits_from_pages(pages, "上网电价")), 1)

        keyword_rows = [
            {"industry": BANK, "code": "600000.XSHG", "field": "net_interest_margin", "hit_count": 1},
            {"industry": BANK, "code": "600000.XSHG", "field": "asset_quality", "hit_count": 1},
            {"industry": POWER, "code": "600011.XSHG", "field": "fuel_cost", "hit_count": 1},
            {"industry": POWER, "code": "600011.XSHG", "field": "tariff", "hit_count": 1},
        ]
        annual_rows = [
            {"industry": BANK, "code": "600000.XSHG"},
            {"industry": POWER, "code": "600011.XSHG"},
        ]
        bank_gate = _field_gate(BANK, keyword_rows, annual_rows)
        power_gate = _field_gate(POWER, keyword_rows, annual_rows)
        decision = _pm_decision(bank_gate, power_gate, [])

        self.assertEqual(decision[0]["pm_gate_decision"], "financial_report_data_gate_pass_to_batch_extraction_not_model_update")
        self.assertFalse(decision[0]["accepted"])


if __name__ == "__main__":
    unittest.main()
