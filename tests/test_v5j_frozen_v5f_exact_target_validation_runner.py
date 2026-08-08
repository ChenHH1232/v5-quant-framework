import unittest

from v5.v5j_frozen_v5f_exact_target_validation_runner import OUT


class FrozenV5fExactTargetValidationRunnerTest(unittest.TestCase):
    def test_output_name_is_stable(self):
        self.assertEqual(OUT.name, "current")


if __name__ == "__main__": unittest.main()
