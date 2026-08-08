from __future__ import annotations
import unittest
from v5.v5j_statement_visible_date_factor_panel_runner import _panel
class V5jStatementVisibleDateFactorPanelTests(unittest.TestCase):
    def test_future_statement_is_excluded(self)->None:
        p=_panel([{"rebalance_date":"2020-04-01","code":"600000.XSHG","sleeve_id":"bank"}],[{"code":"600000.XSHG","pub_date":"2020-04-02","stat_date":"2019-12-31"}], [])
        self.assertEqual(p[0]["record_visible_status"],"missing_visible_statement")
if __name__=="__main__":unittest.main()
