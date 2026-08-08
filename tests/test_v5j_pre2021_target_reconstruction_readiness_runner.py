import unittest

from v5.v5j_pre2021_target_reconstruction_readiness_runner import _decision


class Pre2021TargetReconstructionReadinessTest(unittest.TestCase):
    def test_does_not_permit_proxy_when_blocked(self):
        result = _decision([{"status": "blocked"}])
        self.assertFalse(result["frozen_validation_permitted"])
        self.assertFalse(result["proxy_target_substitution_allowed"])


if __name__ == "__main__": unittest.main()
