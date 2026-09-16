import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

import app
from stored_invoice_service import (
    InvoiceAccess, InvoiceBackendError, InvoiceData, InvoiceQuestion,
    InvoiceToolCall, SpringInvoiceBackend, StoredInvoiceService,
)


def access(company="A"):
    return InvoiceAccess(corporationId=company, allowedTools=["get_invoice_amount", "get_invoice_totals"], allowedStatuses=["CLEARED", "CANCELLED"])


def data(company="A"):
    return {"corporationId":company, "status":"ok", "invoiceNumber":"001", "amountType":"totalIncludingTax", "totals":[{"currency":"AED", "amount":"105.00", "invoiceCount":1}]}


def call():
    return InvoiceToolCall(tool="get_invoice_amount", invoiceNumber="001", amountType="totalIncludingTax")


class StoredInvoiceTests(unittest.TestCase):
    def setUp(self):
        self.backend = SpringInvoiceBackend("http://127.0.0.1:8080")
        self.backend._request = Mock(return_value=data())

    def test_cross_company_result_is_rejected(self):
        self.backend._request.return_value = data("B")
        with self.assertRaises(InvoiceBackendError) as caught:
            self.backend.execute("token", access("A"), call())
        self.assertEqual(caught.exception.status_code, 502)

    def test_company_never_comes_from_tool_arguments(self):
        with self.assertRaises(ValidationError):
            InvoiceToolCall.model_validate({**call().model_dump(), "corporationId":"B"})
        self.backend.execute("token", access(), call())
        payload = self.backend._request.call_args.args[2]
        self.assertNotIn("corporationId", payload)
        self.assertEqual(payload["invoiceNumber"], "001")

    def test_other_company_invoice_is_indistinguishable_from_missing(self):
        self.backend._request.return_value = {**data(), "status":"not_found", "totals":[]}
        result = self.backend.execute("token", access(), call())
        self.assertEqual(result.status, "not_found")

    def test_permissions_checked_before_data_query(self):
        scope = access()
        scope.allowedTools = []
        with self.assertRaises(InvoiceBackendError) as caught:
            self.backend.execute("token", scope, call())
        self.assertEqual(caught.exception.status_code, 403)
        self.backend._request.assert_not_called()

    def test_unsupported_status_does_not_reach_backend(self):
        query = InvoiceToolCall(tool="get_invoice_totals", amountType="totalIncludingTax", statusScope="selected", statuses=["invented"])
        with self.assertRaises(InvoiceBackendError):
            self.backend.execute("token", access(), query)
        self.backend._request.assert_not_called()

    def test_mixed_currency_totals_are_preserved(self):
        response = data()
        response["invoiceNumber"] = None
        response["totals"].append({"currency":"USD", "amount":"20.00", "invoiceCount":2})
        self.backend._request.return_value = response
        query = InvoiceToolCall(tool="get_invoice_totals", amountType="totalIncludingTax", statusScope="all")
        result = self.backend.execute("token", access(), query)
        self.assertEqual([str(row.amount) for row in result.totals], ["105.00", "20.00"])

    def test_invalid_routes_and_arguments_are_rejected(self):
        for payload in ({"tool":"run_sql"}, {"tool":"get_invoice_amount"}, {"tool":"get_invoice_totals", "sql":"select *"}, {"tool":"get_invoice_totals", "statusScope":"selected"}, {"tool":"get_invoice_totals", "dateFrom":"2026-09-15", "dateTo":"2026-01-01"}):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                InvoiceToolCall.model_validate(payload)

    def test_plaintext_remote_backend_is_rejected(self):
        with self.assertRaises(ValueError):
            SpringInvoiceBackend("http://example.com")

    def test_wrong_invoice_or_amount_type_is_rejected(self):
        for key, value in (("invoiceNumber", "002"), ("amountType", "remainingPayable")):
            self.backend._request.return_value = {**data(), key:value}
            with self.assertRaises(InvoiceBackendError):
                self.backend.execute("token", access(), call())

    def service(self, decision):
        backend = Mock()
        backend.access.return_value = access()
        backend.execute.return_value = InvoiceData.model_validate(data())
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(parsed=decision)
        return StoredInvoiceService(backend, client, "test-model")

    def test_invalid_auth_stops_before_llm(self):
        service = self.service(call())
        service.backend.access.side_effect = InvoiceBackendError(401, "Sign in")
        with self.assertRaises(InvoiceBackendError):
            service.ask("expired", "my invoices")
        service.client.models.generate_content.assert_not_called()

    def test_totals_without_status_require_clarification(self):
        service = self.service(InvoiceToolCall(tool="get_invoice_totals", amountType="totalIncludingTax"))
        result = service.ask("token", "total of my invoices")
        self.assertEqual(result.status, "clarification_required")
        service.backend.execute.assert_not_called()

    def test_missing_amount_type_requires_clarification(self):
        service = self.service(InvoiceToolCall(tool="get_invoice_amount", invoiceNumber="001"))
        self.assertEqual(service.ask("token", "amount of 001").status, "clarification_required")
        service.backend.execute.assert_not_called()

    def test_generation_outage_preserves_verified_data(self):
        service = self.service(call())
        service.client.models.generate_content.side_effect = [SimpleNamespace(parsed=call()), RuntimeError("unavailable")]
        result = service.ask("token", "total including tax for invoice number 001")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.explanationSource, "template")
        self.assertIn("105.00", result.answer)
        self.assertEqual(service.backend.execute.call_count, 1)

    def test_backend_outage_is_not_a_zero_total(self):
        service = self.service(call())
        service.backend.execute.side_effect = InvoiceBackendError(502, "unavailable")
        with self.assertRaises(InvoiceBackendError):
            service.ask("token", "invoice amount")

    def test_endpoint_requires_auth_and_rejects_company_in_body(self):
        client = TestClient(app.app)
        for headers in ({}, {"Authorization":"Basic abc"}, {"Authorization":"Bearer "}):
            self.assertEqual(client.post("/ai/invoices/query", json={"question":"my invoices"}, headers=headers).status_code, 401)
        self.assertEqual(client.post("/ai/invoices/query", json={"question":"my invoices", "corporationId":"B"}, headers={"Authorization":"Bearer token"}).status_code, 422)

    def test_endpoint_returns_structured_amounts(self):
        service = self.service(call())
        service.client.models.generate_content.side_effect = [SimpleNamespace(parsed=call()), SimpleNamespace(text="Invoice 001 totals AED 105.00 including tax.")]
        with patch.object(app, "get_stored_invoice_service", return_value=service):
            response = TestClient(app.app).post("/ai/invoices/query", json={"question":"total including tax for invoice number 001"}, headers={"Authorization":"Bearer token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"]["totals"][0]["amount"], "105.00")


if __name__ == "__main__":
    unittest.main()
