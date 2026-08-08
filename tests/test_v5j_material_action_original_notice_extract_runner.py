import unittest
from v5.v5j_material_action_original_notice_extract_runner import _rank

class MaterialActionOriginalNoticeExtractRunnerTest(unittest.TestCase):
    def test_rank_limits_each_event(self):
        rows=[{"event_id":"a","announcement_title":"权益分派 每10股","announcement_visible_date":"2014-01-01","candidate_types":"cash_dividend_or_ex_right"},{"event_id":"a","announcement_title":"其他","announcement_visible_date":"2014-01-02","candidate_types":""}]
        self.assertEqual(len(_rank(rows,1)),1)

if __name__=="__main__":unittest.main()
