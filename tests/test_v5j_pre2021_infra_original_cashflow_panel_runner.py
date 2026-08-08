import unittest

from v5.v5j_pre2021_infra_original_cashflow_panel_runner import _period, _period_from_undated_title


class Pre2021InfraOriginalCashflowPanelRunnerTest(unittest.TestCase):
    def test_report_periods(self):
        self.assertEqual(_period("2020年第三季度报告"), "2020-09-30")
        self.assertEqual(_period("2020年三季度报告全文"), "2020-09-30")
        self.assertEqual(_period("2019年年度报告"), "2019-12-31")
        self.assertEqual(_period_from_undated_title("第三季度报告", "2020-10-29"), "2020-09-30")


if __name__ == "__main__": unittest.main()
