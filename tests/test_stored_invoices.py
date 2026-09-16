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
    return InvoiceAccess(corporationId=company, allowedTools=["get_invoice_amount", "get_invoice_totals"], allowedStatuses=["CLEARED", "UNCLEARED", "PENDING"])


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

    def test_schema_survives_actual_sdk_serialization(self):
        from google import genai
        service = self.service(call())
        with genai.Client(api_key="synthetic-test-key") as client:
            service.client = client
            with patch.object(client._api_client, "request", side_effect=RuntimeError("transport intercepted")) as transport:
                with self.assertRaises(InvoiceBackendError):
                    service.ask("fake-login-token", "Invoice number 001 total including tax")
                request = transport.call_args.args[2]
                config = request["generationConfig"]
                self.assertNotIn("responseSchema", config)
                self.assertFalse(config["responseJsonSchema"]["additionalProperties"])
                self.assertNotIn("fake-login-token", str(request))

    def test_provider_400_is_not_reported_as_overload_or_retried(self):
        from google.genai import errors
        service = self.service(call())
        service.client.models.generate_content.side_effect = errors.ClientError(400, {"error": {"message": "invalid schema"}})
        with self.assertRaises(InvoiceBackendError) as caught:
            service.ask("token", "invoice amount")
        self.assertEqual(caught.exception.status_code, 502)
        self.assertIn("rejected", str(caught.exception))
        self.assertEqual(service.client.models.generate_content.call_count, 1)
        service.backend.execute.assert_not_called()

    def test_transient_failure_retries_then_executes_once(self):
        from google.genai import errors
        service = self.service(call())
        service.client.models.generate_content.side_effect = [errors.ServerError(503, {"error": {"message":"busy"}}), SimpleNamespace(parsed=call()), SimpleNamespace(text="AED 105.00")]
        with patch("stored_invoice_service.time.sleep") as delay:
            result = service.ask("token", "invoice amount")
        self.assertEqual(result.status, "ok")
        delay.assert_called_once_with(1)
        service.backend.execute.assert_called_once()

    def test_repeated_overload_is_bounded_and_quota_is_distinct(self):
        from google.genai import errors
        for code, expected, count in ((503, 503, 2), (429, 429, 1)):
            service = self.service(call())
            error_type = errors.ServerError if code == 503 else errors.ClientError
            service.client.models.generate_content.side_effect = error_type(code, {"error": {"message":"unavailable"}})
            with patch("stored_invoice_service.time.sleep"), self.assertRaises(InvoiceBackendError) as caught:
                service.ask("token", "invoice amount")
            self.assertEqual(caught.exception.status_code, expected)
            self.assertEqual(service.client.models.generate_content.call_count, count)
            service.backend.execute.assert_not_called()

    def test_invalid_generated_company_override_still_rejected(self):
        service = self.service({**call().model_dump(), "corporationId":"another-company"})
        with self.assertRaises(InvoiceBackendError) as caught:
            service.ask("token", "invoice amount")
        self.assertEqual(caught.exception.status_code, 502)
        service.backend.execute.assert_not_called()

    def test_generic_totals_default_to_remaining_payable_including_tax(self):
        query = InvoiceToolCall(tool="get_invoice_totals", statusScope="selected", statuses=["CLEARED"])
        self.assertEqual(query.amountType, "remainingPayable")
        service = self.service(query)
        service.backend.execute.return_value = InvoiceData.model_validate({**data(), "amountType":"remainingPayable", "invoiceNumber":None, "totals":[{"currency":"AED","amount":"55.00","invoiceCount":1,"totalExcludingTax":"100.00","totalIncludingTax":"105.00","remainingPayable":"55.00"}]})
        service.client.models.generate_content.side_effect = [SimpleNamespace(parsed=query), RuntimeError("offline")]
        result = service.ask("token", "What is my total for CLEARED invoices?")
        self.assertIn("55.00", result.answer)
        self.assertIn("100.00", result.answer)
        self.assertIn("105.00", result.answer)
        self.assertIn("including tax", result.answer)
        self.assertEqual(service.backend.execute.call_args.args[2].amountType, "remainingPayable")

    def test_generic_totals_still_ask_for_statuses(self):
        service = self.service(InvoiceToolCall(tool="get_invoice_totals"))
        result = service.ask("token", "What is my total?")
        self.assertEqual(result.status, "clarification_required")
        self.assertIn("UNCLEARED", result.answer)
        self.assertIn("including tax", result.answer)
        service.backend.execute.assert_not_called()

    def test_explicit_gross_totals_override_payable_default(self):
        query = InvoiceToolCall(tool="get_invoice_totals", amountType="totalIncludingTax", statusScope="all")
        self.assertEqual(query.amountType,"totalIncludingTax")

    def test_old_integration_status_is_not_accepted(self):
        for status in ("DRAFT", "REJECTED", "CANCELLED"):
            query=InvoiceToolCall(tool="get_invoice_totals",statusScope="selected",statuses=[status])
            with self.assertRaises(InvoiceBackendError):
                self.backend.execute("token",access(),query)
        self.backend._request.assert_not_called()

    def test_missing_pretax_is_not_a_partial_total_or_assumed_vat_rate(self):
        result = InvoiceData.model_validate({**data(), "amountType":"remainingPayable", "totals":[{"currency":"AED","amount":"55.00","invoiceCount":2,"totalExcludingTax":None,"totalIncludingTax":"105.00","remainingPayable":"55.00","missingPreTaxCount":1}]})
        from stored_invoice_service import StoredInvoiceService
        answer = StoredInvoiceService._answer(result, overview=True)
        self.assertIn("unavailable", answer)
        self.assertIn("105.00", answer)
        self.assertIn("55.00", answer)
        invalid = result.model_dump()
        invalid["totals"][0]["totalExcludingTax"] = "50.00"
        with self.assertRaises(ValidationError):
            InvoiceData.model_validate(invalid)


if __name__ == "__main__":
    unittest.main()
