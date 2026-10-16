
import sys
import unittest
from pathlib import Path

# Allow Python to import src/router_cli.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from router_cli import detect_domain, tax_year_is_specified


class TestDomainRouting(unittest.TestCase):

    def test_simple_and_compound_interest_routes_to_finance(self):
        domain, scores, issue = detect_domain(
            "Explain the difference between simple interest and compound interest."
        )
        self.assertEqual(domain, "finance")
        self.assertIsNone(issue)

    def test_inflation_routes_to_finance(self):
        domain, scores, issue = detect_domain(
            "How does inflation affect purchasing power?"
        )
        self.assertEqual(domain, "finance")
        self.assertIsNone(issue)

    def test_emi_routes_to_finance(self):
        domain, scores, issue = detect_domain(
            "How is an EMI calculated for a loan?"
        )
        self.assertEqual(domain, "finance")
        self.assertIsNone(issue)

    def test_contract_question_routes_to_legal(self):
        domain, scores, issue = detect_domain(
            "Explain the important clauses in a legal contract."
        )
        self.assertEqual(domain, "legal")
        self.assertIsNone(issue)

    def test_income_tax_question_routes_to_tax(self):
        domain, scores, issue = detect_domain(
            "Explain how income tax works for an individual."
        )
        self.assertEqual(domain, "tax")
        self.assertIsNone(issue)

    def test_unrelated_question_has_no_domain(self):
        domain, scores, issue = detect_domain(
            "Tell me a funny story about a cat."
        )
        self.assertIsNone(domain)
        self.assertIsNotNone(issue)

    def test_multi_domain_question_is_flagged_as_ambiguous(self):
        domain, scores, issue = detect_domain(
            "Explain bank fraud, legal contracts, and income tax."
        )
        self.assertIsNone(domain)
        self.assertIsNotNone(issue)


class TestTaxYearValidation(unittest.TestCase):

    def test_financial_year_is_recognized(self):
        self.assertTrue(
            tax_year_is_specified(
                "Compare the tax regimes for FY 2025-26."
            )
        )

    def test_assessment_year_is_recognized(self):
        self.assertTrue(
            tax_year_is_specified(
                "Explain deductions for AY 2026-27."
            )
        )

    def test_missing_tax_year_is_detected(self):
        self.assertFalse(
            tax_year_is_specified(
                "Which income tax regime is better for me?"
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
