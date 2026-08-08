import unittest

from v5.v5j_pit_availability_boundary_closeout_runner import _decision


class PitAvailabilityBoundaryCloseoutTest(unittest.TestCase):
    def test_exact_validation_stays_blocked(self):
        self.assertFalse(_decision([], [], [])["frozen_v5f_validation_permitted"])


if __name__ == "__main__": unittest.main()
