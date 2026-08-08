from __future__ import annotations

import unittest

from v5.v5j_repaired_multisleeve_pit_pool_runner import _bs_to_jq, _jq_to_bs, _sleeve_for_industry


class V5jRepairedMultisleevePitPoolRunnerTests(unittest.TestCase):
    def test_historical_industry_mapping_is_narrow(self) -> None:
        self.assertEqual(_sleeve_for_industry("G54道路运输业"), "highway_infrastructure")
        self.assertEqual(_sleeve_for_industry("G55水上运输业"), "port_rail_infrastructure")
        self.assertEqual(_sleeve_for_industry("D44电力、热力生产和供应业"), "utilities_electricity")
        self.assertEqual(_sleeve_for_industry("电力、热力、燃气及水生产和供应业-水的生产和供应业"), "")
        self.assertEqual(_sleeve_for_industry("电力、热力、燃气及水生产和供应业-燃气生产和供应业"), "")
        self.assertEqual(_sleeve_for_industry("J66货币金融服务"), "bank")
        self.assertEqual(_sleeve_for_industry("C39计算机、通信和其他电子设备制造业"), "")

    def test_code_conversions_are_lossless_for_a_share_codes(self) -> None:
        self.assertEqual(_bs_to_jq("sh.600900"), "600900.XSHG")
        self.assertEqual(_bs_to_jq("sz.000001"), "000001.XSHE")
        self.assertEqual(_jq_to_bs("600900.XSHG"), "sh.600900")
        self.assertEqual(_jq_to_bs("000001.XSHE"), "sz.000001")


if __name__ == "__main__":
    unittest.main()
