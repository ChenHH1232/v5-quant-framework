from __future__ import annotations
import unittest
from v5.v5j_missing_1min_source_repair_runner import _usable

class V5jMissingOneMinuteSourceRepairTests(unittest.TestCase):
    def test_usable_requires_a_cleaned_path(self) -> None:
        self.assertTrue(_usable({"path": "x.csv", "status": "pass"}))
        self.assertFalse(_usable({"path": "", "status": "pass"}))

if __name__ == "__main__": unittest.main()
