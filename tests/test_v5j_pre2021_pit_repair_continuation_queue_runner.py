import unittest
from v5.v5j_pre2021_pit_repair_continuation_queue_runner import OUT
class PitRepairContinuationQueueTest(unittest.TestCase):
    def test_output(self):self.assertEqual(OUT.name,"current")
if __name__=="__main__":unittest.main()
