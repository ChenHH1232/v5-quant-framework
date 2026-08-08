import unittest

from v5.v5j_material_corporate_action_notice_repair_runner import _keyword_types, _number


class MaterialCorporateActionNoticeRepairRunnerTest(unittest.TestCase):
    def test_keyword_classification(self):
        kinds = _keyword_types("关于重大资产重组及权益分派实施公告")
        self.assertIn("restructuring_or_merger", kinds)
        self.assertIn("cash_dividend_or_ex_right", kinds)

    def test_number_is_safe(self):
        self.assertEqual(_number("0.5"), 0.5)
        self.assertEqual(_number(""), 0.0)


if __name__ == "__main__":
    unittest.main()
