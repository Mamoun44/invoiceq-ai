import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

import app
from analysis_tools import IntegrationAnalysisTool, IntentDecision, KnowledgeAssessment, fallback_intent
from explanation_service import ExplanationService
from test_invoice_validation import valid_invoice


class ValidationServiceTests(unittest.TestCase):
    def test_guest_missing_details_requests_context_without_provider(self):
        with patch.object(app, "get_explanation_service", side_effect=AssertionError("No provider needed")):
            for question in ["My invoice failed", "Check this invoice JSON"]:
                response = TestClient(app.app).post("/ai/explain/stream", json={"question": question})
                self.assertEqual(response.status_code, 200)
                self.assertIn("Add invoice details", response.text)
                self.assertIn("event: done", response.text)

    def test_guest_amount_question_does_not_call_provider(self):
        with patch.object(app, "get_explanation_service", side_effect=AssertionError("Must not call Gemini")):
            response = TestClient(app.app).post("/ai/explain/stream", json={
                "question": "what is the amount of my invoice",
                "invoice": {"invoiceNumber": "example"},
                "invoiceqError": {"httpStatus": 400},
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Please sign in", response.text)
        self.assertIn("event: done", response.text)
        self.assertNotIn("event: status", response.text)

    def setUp(self):
        # No credentials, live Gemini requests, or InvoiceQ submissions.
        self.service = ExplanationService.__new__(ExplanationService)
        self.service.store_name = "test-store"
        self.service.client = Mock()
        self.service.analysis_tool = IntegrationAnalysisTool()
        self.service.route_intent = Mock(return_value=IntentDecision(intent="validate_request", reason="Test"))

    def knowledge(self, **overrides):
        data = {"matchedRules": [], "documentedProblems": [], "documentationSufficient": True}
        data.update(overrides)
        self.service.client.chats.create.return_value.send_message.return_value = SimpleNamespace(parsed=KnowledgeAssessment.model_validate(data))

    def analyze(self, invoice=None):
        return self.service.analyze_context(request_json=invoice or valid_invoice(), response_json=None, question="Validate this invoice")

    def test_grounded_knowledge_problems_are_merged(self):
        self.knowledge(
            matchedRules=[{"rule": "Example retrieved requirement", "source": "test-doc", "fields": ["customerInfo.beneficiaryId"]}],
            documentedProblems=[{"field": "customerInfo.beneficiaryId", "reason": "Missing identifier", "recommendedAction": "Provide the identifier", "source": "test-doc"}],
        )
        result = self.analyze()
        self.assertEqual(result.status, "failure")
        self.assertEqual(result.problems[0].field, "customerInfo.beneficiaryId")
        self.assertEqual(result.knowledgeStatus, "matched")

    def test_unsupported_knowledge_problem_is_not_a_failure(self):
        self.knowledge(documentedProblems=[{"field": "inventedField", "reason": "Unsupported", "recommendedAction": "Add it", "source": "missing-doc"}])
        result = self.analyze()
        self.assertEqual(result.problems, [])
        self.assertTrue(result.needsMoreInformation)

    def test_knowledge_does_not_duplicate_schema_errors(self):
        self.knowledge(
            matchedRules=[{"rule": "Currency required", "source": "test-doc", "fields": ["currencyIsoCode"]}],
            documentedProblems=[{"field": "currencyIsoCode", "reason": "Required", "recommendedAction": "Add currency", "source": "test-doc"}],
        )
        invoice = valid_invoice()
        del invoice["currencyIsoCode"]
        result = self.analyze(invoice)
        self.assertEqual(len([p for p in result.problems if p.field == "currencyIsoCode"]), 1)

    def test_search_outage_retains_local_errors(self):
        self.service.client.chats.create.side_effect = RuntimeError("Offline")
        invoice = valid_invoice()
        invoice["products"] = []
        result = self.analyze(invoice)
        self.assertEqual(result.knowledgeStatus, "unavailable")
        self.assertEqual(result.status, "failure")
        self.assertIn("products", {p.field for p in result.problems})

    def test_search_outage_does_not_report_a_clean_invoice_as_accepted(self):
        self.service.client.chats.create.side_effect = RuntimeError("Offline")
        result = self.analyze()
        self.assertEqual(result.status, "unknown")
        self.assertTrue(result.needsMoreInformation)

    def test_api_preserves_validation_findings_for_both_contracts(self):
        self.knowledge()
        invoice = valid_invoice()
        invoice["products"][0]["unitCost"] = -10
        with patch.object(app, "get_explanation_service", return_value=self.service):
            client = TestClient(app.app)
            for request_name in ("invoice", "requestJson"):
                response = client.post("/ai/analyze", json={request_name: invoice, "question": "Validate this invoice"})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "failure")
                self.assertIn("products[0].unitCost", {p["field"] for p in response.json()["problems"]})

    def test_fallback_validation_takes_precedence_over_fact_keywords(self):
        decision = fallback_intent("Check the invoice number and currency", valid_invoice(), None)
        self.assertEqual(decision.intent, "validate_request")


if __name__ == "__main__":
    unittest.main()
