from pathlib import Path
import unittest

from src.v5.v5j_pre2019_pit_rebuild_data_gate_runner import run_v5j_pre2019_pit_rebuild_data_gate


class V5jPre2019PitRebuildDataGateRunnerTest(unittest.TestCase):
    def test_inventory_does_not_confuse_minute_data_with_a_pit_pool(self) -> None:
        summary = run_v5j_pre2019_pit_rebuild_data_gate(Path("."))
        self.assertEqual(summary["status"], "completed_p0_inventory_blocked_for_rebuild")
        self.assertTrue(summary["minute_data_available"])
        self.assertFalse(summary["pre2019_repaired_daily_price_panel_available"])
        self.assertFalse(summary["pre2019_full_multisleeve_pit_pool_available"])
        self.assertFalse(summary["accepted"])
        out = Path("v5j_pre2019_pit_rebuild_data_gate") / "current"
        self.assertTrue((out / "v5j_pre2019_multisleeve_pit_inventory.csv").exists())
        self.assertTrue((out / "v5j_pre2019_pit_rebuild_queue.csv").exists())


if __name__ == "__main__":
    unittest.main()
