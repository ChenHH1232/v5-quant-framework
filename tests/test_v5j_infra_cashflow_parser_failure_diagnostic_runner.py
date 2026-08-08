import unittest
from v5.v5j_infra_cashflow_parser_failure_diagnostic_runner import CAPEX
class InfraCashflowParserFailureDiagnosticTest(unittest.TestCase):
 def test_has_payment_variants(self):self.assertGreaterEqual(len(CAPEX),3)
if __name__=="__main__":unittest.main()
