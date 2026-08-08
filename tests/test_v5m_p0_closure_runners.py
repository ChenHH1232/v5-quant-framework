from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5m_forward_paper_cycle_readiness_runner import run_v5m_forward_paper_cycle_readiness
from v5.v5m_p0_closure_runner import run_v5m_p0_closure
from v5.v5m_qmt_historical_contract_recovery_runner import run_v5m_qmt_historical_contract_recovery


class V5mP0ClosureRunnersTest(unittest.TestCase):
    def test_historical_contract_and_forward_schema_do_not_claim_execution(self) -> None:
        root = Path(".")
        qmt = run_v5m_qmt_historical_contract_recovery(root)
        forward = run_v5m_forward_paper_cycle_readiness(root)
        closeout = run_v5m_p0_closure(root)
        self.assertFalse(qmt["exact_qmt_contract_recovered"])
        self.assertFalse(forward["future_target_generated"])
        self.assertFalse(forward["platform_started"])
        self.assertEqual(closeout["final_pm_gate_decision"], "candidate_needs_cash_and_qmt_recovery")


if __name__ == "__main__":
    unittest.main()
