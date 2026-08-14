from __future__ import annotations

import json
import unittest
from pathlib import Path

from v5.v5v_application_final_report_readiness_runner import run_v5v_application_final_report_readiness


class V5vApplicationFinalReportReadinessRunnerTest(unittest.TestCase):
    def test_builds_a_constrained_application_readiness_packet(self) -> None:
        summary = run_v5v_application_final_report_readiness(Path("."))
        self.assertEqual(summary["baseline"], "v57f_startup_preload_repaired_baseline")
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["pairwise_observations"], 1228)
        self.assertFalse(summary["accepted"])
        out = Path("v5v_application_final_report_readiness") / "current"
        self.assertTrue((out / "figures" / "v5v_formal_pairwise_comparison.png").exists())
        self.assertTrue((out / "figures" / "v5_time_series_sample_isolation_design.png").exists())
        self.assertTrue((out / "v5v_required_disclosure_register.csv").exists())
        figure_register = (out / "v5v_figure_register.csv").read_text(encoding="utf-8-sig")
        self.assertIn("v5_time_series_sample_isolation_design.png", figure_register)
        self.assertIn("sample isolation", (out / "v5v_chart_captions_and_usage.md").read_text(encoding="utf-8-sig").lower())
        payload = json.loads((out / "v5v_application_final_report_readiness_summary.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(payload["candidate_status"], "primary_forward_paper_candidate_not_accepted")


if __name__ == "__main__":
    unittest.main()
