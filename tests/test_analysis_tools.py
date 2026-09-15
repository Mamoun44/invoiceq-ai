import unittest

from analysis_tools import IntegrationAnalysisTool, fallback_intent


class IntegrationAnalysisToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = IntegrationAnalysisTool()

    def test_matches_invoiceq_error_to_request_value(self) -> None:
        result = self.tool.execute(
            intent="explain_failure",
            request_json={"supplier": {"taxId": ""}},
            response_json={
                "httpStatus": 400,
                "valid": False,
                "errors": [
                    {
                        "reason": "supplier.taxId",
                        "errorDescription": "Missing tax identification number.",
                    }
                ],
            },
            question="Why did this request fail?",
        )

        self.assertEqual(result.status, "failure")
        self.assertEqual(result.httpStatus, 400)
        self.assertEqual(result.problems[0].field, "supplier.taxId")
        self.assertEqual(result.problems[0].providedValue, "")
        self.assertIn("supplier.taxId", result.problems[0].recommendedAction)
        self.assertFalse(result.needsMoreInformation)

    def test_explains_response_without_request(self) -> None:
        result = self.tool.execute(
            intent="explain_error",
            request_json=None,
            response_json={
                "httpStatus": 400,
                "reason": "products",
                "errorDescription": "At least one valid product is required",
            },
            question="What does this error mean?",
        )

        self.assertEqual(result.status, "failure")
        self.assertEqual(result.problems[0].field, "products")
        self.assertEqual(result.problems[0].evidenceSource, "invoiceq_response")

    def test_request_only_rules_are_reported_as_potential_issues(self) -> None:
        question = "Why did this request fail and what should I change?"
        decision = fallback_intent(
            question,
            {"invoiceNumber": "", "invoiceType": "", "products": []},
            {},
        )
        result = self.tool.execute(
            intent=decision.intent,
            request_json={"invoiceNumber": "", "invoiceType": "", "products": []},
            response_json={},
            question=question,
        )

        self.assertEqual(decision.intent, "explain_failure")
        self.assertEqual(result.status, "failure")
        self.assertTrue({"invoiceNumber", "invoiceType", "products", "issueDate", "paymentMeans", "totalTaxAmount"}.issubset({problem.field for problem in result.problems}))
        self.assertTrue(
            all(problem.evidenceSource == "openapi_schema" for problem in result.problems)
        )
        self.assertIn("responseJson", result.missingContext)
        self.assertTrue(result.needsMoreInformation)

    def test_stored_invoice_question_is_blocked_for_anonymous_path(self) -> None:
        question = "What is the total amount I have for all my invoices?"
        decision = fallback_intent(question, None, None)
        result = self.tool.execute(
            intent=decision.intent,
            request_json=None,
            response_json=None,
            question=question,
        )

        self.assertEqual(decision.intent, "stored_invoice_query")
        self.assertEqual(result.status, "not_allowed")
        self.assertIn("authenticated customer context", result.missingContext)


if __name__ == "__main__":
    unittest.main()
