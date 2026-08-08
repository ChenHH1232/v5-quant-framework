import unittest
from v5.v5j_material_action_unclassified_notice_fallback_runner import OUT
class UnclassifiedMaterialActionFallbackTest(unittest.TestCase):
    def test_output_dir(self):self.assertIn("fallback",str(OUT))
if __name__=="__main__":unittest.main()
