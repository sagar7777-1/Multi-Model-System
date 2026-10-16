
import sys
import unittest
from pathlib import Path

# Allow imports from src/router_cli.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from router_cli import (
    inspect_answer,
    should_use_tax_fallback,
)


class TestAnswerSafety(unittest.TestCase):

    def test_flags_suspicious_2011_legal_reference(self):
        answer = (
            "The Data Privacy Act, 2011 requires every company "
            "to follow these rules."
        )

        warnings = inspect_answer("legal", answer)

        self.assertTrue(warnings)

    def test_allows_dpdp_act_2023_reference(self):
        answer = (
            "India enacted the Digital Personal Data Protection "
            "Act, 2023. Check applicable provisions and "
            "commencement notifications for the relevant situation."
        )

        warnings = inspect_answer("legal", answer)

        self.assertEqual(warnings, [])

    def test_flags_tax_answer_with_rupee_amount(self):
        answer = "Your tax liability will be ₹25,000."

        warnings = inspect_answer("tax", answer)

        self.assertTrue(warnings)

    def test_flags_tax_answer_with_percentage(self):
        answer = "You will pay tax at a rate of 20%."

        warnings = inspect_answer("tax", answer)

        self.assertTrue(warnings)

    def test_flags_unsupported_regime_replacement_claim(self):
        answer = "The new tax regime replaced the old tax regime."

        warnings = inspect_answer("tax", answer)

        self.assertTrue(warnings)

    def test_allows_general_tax_explanation_without_figures(self):
        answer = (
            "Tax outcomes depend on eligibility, applicable rules, "
            "deductions, and the taxpayer's circumstances. "
            "Compare both regimes using the applicable official rules."
        )

        warnings = inspect_answer("tax", answer)

        self.assertEqual(warnings, [])

    def test_finance_answer_is_not_flagged(self):
        answer = (
            "Compound interest is calculated on the principal "
            "and accumulated interest."
        )

        warnings = inspect_answer("finance", answer)

        self.assertEqual(warnings, [])

    def test_tax_fallback_message_is_cautious(self):
        # This mirrors the fallback text in router_cli.py.
        fallback = (
            "I cannot provide a reliable tax-regime recommendation "
            "from the model's current response because it contains "
            "numerical claims that have not been verified.\n\n"
            "For a proper comparison, calculate your tax liability "
            "under both regimes using the official Income Tax "
            "Department calculator for the specified financial year. "
            "Use the same income, eligible deductions, exemptions, "
            "and other relevant details for both calculations. "
            "Then compare the resulting tax liabilities and check "
            "which regime's rules apply to your circumstances.\n\n"
            "No tax figures or personalized recommendation are "
            "being provided by this router until the relevant "
            "claims can be verified."
        )

        self.assertTrue(fallback.strip())
        self.assertIn("cannot provide a reliable", fallback.lower())
        self.assertIn("official income tax department calculator", fallback.lower())
        self.assertIn("have not been verified", fallback.lower())
        self.assertNotIn("₹", fallback)


    def test_tax_warnings_trigger_fallback(self):
        warnings = ["Unverified numerical tax claim"]

        self.assertTrue(
            should_use_tax_fallback("tax", warnings)
        )

    def test_tax_without_warnings_does_not_trigger_fallback(self):
        self.assertFalse(
            should_use_tax_fallback("tax", [])
        )

    def test_finance_warnings_do_not_trigger_tax_fallback(self):
        warnings = ["Some warning"]

        self.assertFalse(
            should_use_tax_fallback("finance", warnings)
        )

    def test_tax_answer_flagged_for_unnecessary_dependents(self):
        answer = (
            "Provide the number of dependents to estimate your "
            "Indian income tax."
        )
        warnings = inspect_answer("tax", answer)
        self.assertTrue(warnings)

    def test_tax_answer_flagged_for_unnecessary_marital_status(self):
        answer = (
            "Please specify your marital status to calculate "
            "your individual income tax."
        )
        warnings = inspect_answer("tax", answer)
        self.assertTrue(warnings)

    def test_tax_fallback_triggered_when_personal_data_is_flagged(self):
        answer = (
            "Provide the number of dependents to estimate your tax."
        )
        warnings = inspect_answer("tax", answer)
        self.assertTrue(should_use_tax_fallback("tax", warnings))



if __name__ == "__main__":
    unittest.main(verbosity=2)
