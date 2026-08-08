import unittest
from v5.v5j_pit_disclosure_trust_audit_runner import _bank

class PitDisclosureTrustAuditTest(unittest.TestCase):
    def test_missing_field_is_untrusted(self):
        rows=_bank([{"rebalance_date":"2013-01-04","code":"x","selected_report_period":"2012-09-30","selected_report_visible_date":"2012-10-01"}],[])
        self.assertEqual(rows[0]["trust_label"],"untrusted_missing_pit_regulatory_disclosure")
        self.assertFalse(rows[0]["historical_reconstructed_candidate_allowed"])
if __name__=="__main__":unittest.main()
