from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5e_limited_engineering_runner import VARIANTS, run_v5e_limited_engineering_loop


class V5eLimitedEngineeringRunnerTest(unittest.TestCase):
    def test_runner_generates_fixed_variant_checkpoint_without_acceptance(self) -> None:
        root = Path(".")
        summary = run_v5e_limited_engineering_loop(root)

        self.assertEqual(summary["status"], "completed_one_hour_checkpoint")
        self.assertEqual(len(summary["versions_tested"]), 7)
        self.assertEqual([v.version_id for v in VARIANTS], summary["versions_tested"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["erc_modified"])
        self.assertFalse(summary["v5d_modified"])
        self.assertFalse(summary["joinquant_started"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["parameter_scan_started"])
        self.assertFalse(summary["accepted_marked"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = root / "v5e_limited_engineering_loop" / "current"
        comparison = (out / "v5e_engineering_comparison.csv").read_text(encoding="utf-8-sig")
        self.assertIn("v5e_combined_main_profit_lock_plus_trailing", comparison)
        self.assertIn("pre_registered_not_optimized", comparison)

        t_log = (out / "v5e_t_violation_log.csv").read_text(encoding="utf-8-sig")
        reentry_log = (out / "v5e_reentry_violation_log.csv").read_text(encoding="utf-8-sig")
        self.assertEqual(len([line for line in t_log.splitlines() if line.strip()]), 0)
        self.assertEqual(len([line for line in reentry_log.splitlines() if line.strip()]), 0)

        gate = (out / "v5e_pm_gate_decision.csv").read_text(encoding="utf-8-sig")
        self.assertIn("accepted,v57f_replacement", gate)
        self.assertIn(",no,no,", gate)


if __name__ == "__main__":
    unittest.main()
