from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5l_candidate_hardening_closeout_runner import run_v5l_candidate_hardening_closeout
from v5.v5l_cash_constrained_nav_validation_runner import run_v5l_cash_constrained_nav_validation
from v5.v5l_primary_candidate_risk_observation_runner import run_v5l_primary_candidate_risk_observation
from v5.v5l_qmt_execution_evidence_runner import run_v5l_qmt_execution_evidence


class V5lCandidateHardeningRunnersTest(unittest.TestCase):
    def test_historical_only_hardening_preserves_real_evidence_boundaries(self) -> None:
        root = Path(".")
        cash = run_v5l_cash_constrained_nav_validation(root)
        qmt = run_v5l_qmt_execution_evidence(root)
        risk = run_v5l_primary_candidate_risk_observation(root)
        closeout = run_v5l_candidate_hardening_closeout(root)
        self.assertTrue(cash["strict_cash_ledger_pass"])
        self.assertFalse(cash["strict_cash_nav_available"])
        self.assertEqual(cash["partial_or_skipped_buy_count"], 43)
        self.assertFalse(qmt["qmt_contract_complete"])
        self.assertEqual(risk["relative_weak_years"], 2)
        self.assertEqual(closeout["final_pm_gate_decision"], "candidate_needs_cash_constrained_retest")
        self.assertFalse(closeout["accepted"])


if __name__ == "__main__":
    unittest.main()
