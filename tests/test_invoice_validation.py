import copy
import unittest

from analysis_tools import IntegrationAnalysisTool


def valid_invoice():
    return {
        "invoiceNumber": "TEST-001", "currencyIsoCode": "AED",
        "issueDate": "2026-09-15T09:30:00Z", "paymentMeans": 10,
        "totalDiscountAmount": 0, "totalTaxAmount": 5,
        "totalInvoiceAmount": 105, "totalNetAmount": 105,
        "products": [{
            "productCode": "P1", "productName": "Test item", "unitType": "EA",
            "quantity": 1, "unitCost": 100, "netAmount": 105,
            "taxType": "S", "taxPercentage": 5, "lineTotalTaxAmount": 5,
        }],
    }


class InvoiceValidationTests(unittest.TestCase):
    def setUp(self):
        self.tool = IntegrationAnalysisTool()

    def analyze(self, invoice, response=None, intent="validate_request"):
        return self.tool.execute(intent=intent, request_json=invoice, response_json=response, question="Validate this invoice")

    def fields(self, invoice):
        return {p.field for p in self.analyze(invoice).problems}

    def test_valid_invoice_is_unchanged_and_server_acceptance_is_unknown(self):
        invoice = valid_invoice()
        original = copy.deepcopy(invoice)
        result = self.analyze(invoice)
        self.assertEqual(result.problems, [])
        self.assertEqual(result.status, "unknown")
        self.assertTrue(result.facts["localValidationPassed"])
        self.assertEqual(invoice, original)

    def test_empty_request_reports_each_missing_field(self):
        fields = self.fields({})
        self.assertEqual(len(fields), 9)
        self.assertIn("products", fields)
        self.assertIn("totalNetAmount", fields)

    def test_nested_missing_fields_and_array_indices(self):
        invoice = valid_invoice()
        invoice["products"].append({})
        invoice["customerInfo"] = {}
        fields = self.fields(invoice)
        self.assertIn("products[1].productCode", fields)
        self.assertIn("products[1].netAmount", fields)
        self.assertIn("customerInfo.countryIsoCode", fields)

    def test_types_and_enums_do_not_coerce(self):
        for field, value in (("paymentMeans", "10"), ("paymentMeans", True), ("paymentMeans", 20), ("totalNetAmount", True), ("isEcommerce", "false"), ("invoiceType", "")):
            with self.subTest(field=field, value=value):
                invoice = valid_invoice()
                invoice[field] = value
                self.assertIn(field, self.fields(invoice))

    def test_date_time_requires_valid_calendar_and_zone(self):
        for value in ("2026-09-15", "2026-02-30T12:00:00Z", "2026-09-15T12:00:00", "2026-09-15 12:00:00Z", "2026-09-15T12:00:00+03:99"):
            invoice = valid_invoice()
            invoice["issueDate"] = value
            self.assertIn("issueDate", self.fields(invoice))
        invoice["issueDate"] = "2026-09-15T12:00:00+03:00"
        self.assertNotIn("issueDate", self.fields(invoice))

    def test_wrong_nested_types_do_not_crash_business_checks(self):
        for key, value in (("products", {}), ("products", [None, False, "x"]), ("customerInfo", []), ("invoiceLevelCharges", [None]), ("customFields", "oops")):
            invoice = valid_invoice()
            invoice[key] = value
            self.assertTrue(self.analyze(invoice).problems)
        for key in valid_invoice()["products"][0]:
            invoice = valid_invoice()
            invoice["products"][0][key] = {"bad": []}
            self.assertIn(f"products[0].{key}", self.fields(invoice))

    def test_optional_invoice_type_uses_default(self):
        self.assertNotIn("invoiceType", self.fields(valid_invoice()))

    def test_conditional_invoice_requirements(self):
        invoice = valid_invoice()
        invoice.update(currencyIsoCode="USD", isContinuousSupply=True, isFreeTradeZone=True, isEcommerce=True)
        fields = self.fields(invoice)
        self.assertTrue({"exchangeRate", "totalTaxAmountInBaseCurrency", "supplyDate", "supplyEndDate", "customerInfo.beneficiaryId", "customerInfo.deliveryAddress"} <= fields)

    def test_domestic_and_export_customer_rules(self):
        invoice = valid_invoice()
        invoice["customerInfo"] = {"mode": "USE_SAVED", "customerCode": "C1", "englishName": "Buyer", "countryIsoCode": "ARE", "city": "Dubai", "street": "Street", "entitySchemeId": "TL"}
        self.assertTrue({"customerInfo.arabicName", "customerInfo.authorityName", "customerInfo.registrationNumber", "customerInfo.provinceCode"} <= self.fields(invoice))
        invoice["customerInfo"]["countryIsoCode"] = "AUS"
        invoice["isExportInvoice"] = True
        self.assertEqual(self.fields(invoice), set())
        invoice["customerInfo"]["peppolSchemaId"] = "0235"
        self.assertIn("customerInfo.peppolParticipantId", self.fields(invoice))

    def test_tax_and_commodity_requirements(self):
        invoice = valid_invoice()
        line = invoice["products"][0]
        line.update(taxType="AE", commodityCode="B")
        self.assertTrue({"products[0].taxPercentage", "products[0].lineTotalTaxAmount", "products[0].natureCode", "products[0].standardItemId", "products[0].hsCode", "products[0].serviceAccountingCode", "customerInfo.entityTaxNumber"} <= self.fields(invoice))

    def test_commercial_and_margin_categories(self):
        invoice = valid_invoice()
        invoice["invoiceType"] = "COMMERCIAL"
        self.assertIn("products[0].taxType", self.fields(invoice))
        invoice["invoiceType"] = "STANDARD"
        invoice["isMarginScheme"] = True
        self.assertIn("products[0].taxType", self.fields(invoice))
        invoice["products"][0].update(taxType="N", lineTotalTaxAmount=0)
        self.assertNotIn("products[0].taxType", self.fields(invoice))

    def test_noncommercial_exempt_only_and_exemption_code(self):
        invoice = valid_invoice()
        invoice["products"][0].update(taxType="E", taxPercentage=0)
        self.assertTrue({"products", "products[0].exemptionReasonCode"} <= self.fields(invoice))

    def test_amounts_and_tax_mismatches(self):
        invoice = valid_invoice()
        invoice.update(totalDiscountAmount=20, totalTaxAmount=100, totalInvoiceAmount=99, totalNetAmount=50)
        invoice["products"][0]["netAmount"] = 50
        self.assertTrue({"totalDiscountAmount", "totalTaxAmount", "totalInvoiceAmount", "totalNetAmount", "products[0].netAmount"} <= self.fields(invoice))

    def test_line_and_document_adjustments(self):
        invoice = valid_invoice()
        line = invoice["products"][0]
        line.update(discountAmount=10, netAmount=84, lineTotalTaxAmount=4)
        line["lineAllowances"] = [{"amount": 10, "allowanceCode": "95"}]
        invoice["invoiceLevelCharges"] = [{"amount": 20, "chargeCode": "AA", "taxType": "S"}]
        invoice.update(totalDiscountAmount=10, totalInvoiceAmount=105, totalNetAmount=105)
        self.assertEqual(self.fields(invoice), set())
        invoice["invoiceLevelCharges"][0]["taxType"] = "N"
        self.assertIn("invoiceLevelCharges[0].taxType", self.fields(invoice))

    def test_rounding_and_advance(self):
        invoice = valid_invoice()
        invoice["products"][0].update(unitCost=0.1, quantity=3, netAmount=0.315, lineTotalTaxAmount=0.015)
        invoice.update(totalInvoiceAmount=0.32, totalTaxAmount=0.02, totalAdvancedPaidAmount=0.1, totalNetAmount=0.22)
        self.assertEqual(self.fields(invoice), set())
        invoice["totalTaxAmount"] = 0.01
        self.assertIn("totalTaxAmount", self.fields(invoice))

    def test_precision_and_nonfinite_numbers(self):
        invoice = valid_invoice()
        invoice["products"][0]["unitCost"] = 1.12345678
        self.assertIn("products[0].unitCost", self.fields(invoice))
        invoice["products"][0]["unitCost"] = float("inf")
        self.assertIn("products[0].unitCost", self.fields(invoice))

    def test_prepayment_and_duplicate_attributes(self):
        invoice = valid_invoice()
        invoice.update(totalAdvancedPaidAmount=0, invoicePrepaymentDetails=[{"prepaymentInvoiceRef": "PRE1", "invoiceDate": "2026-09-01T00:00:00Z"}], customFields=[{"attributeCode": "A"}, {"attributeCode": "A"}])
        self.assertTrue({"totalAdvancedPaidAmount", "customFields[1].attributeCode"} <= self.fields(invoice))

    def test_attachment_and_principal(self):
        invoice = valid_invoice()
        invoice.update(invoiceAttachmentBase64="not-base64!", principalTaxNumber="123")
        self.assertTrue({"invoiceAttachmentBase64", "invoiceAttachmentFileType", "principalTaxNumber"} <= self.fields(invoice))

    def test_response_errors_and_local_checks_are_both_kept(self):
        invoice = valid_invoice()
        invoice["products"][0]["quantity"] = -1
        result = self.analyze(invoice, {"httpStatus": 400, "errors": [{"field": "invoiceNumber", "message": "Duplicate"}]}, "explain_failure")
        self.assertEqual(result.problems[0].evidenceSource, "invoiceq_response")
        self.assertIn("products[0].quantity", {p.field for p in result.problems})

    def test_success_message_is_not_an_error(self):
        result = self.analyze(valid_invoice(), {"httpStatus": 200, "valid": True, "message": "Created"})
        self.assertEqual(result.problems, [])
        self.assertEqual(result.status, "success")

    def test_response_cannot_override_anonymous_boundary(self):
        result = self.analyze(valid_invoice(), {"httpStatus": 200, "valid": True}, "stored_invoice_query")
        self.assertEqual(result.status, "not_allowed")
        self.assertEqual(result.problems, [])


if __name__ == "__main__":
    unittest.main()
