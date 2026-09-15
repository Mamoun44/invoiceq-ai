"""UAE create-invoice checks sourced from the bundled knowledge/*.md files.

This is a local preflight, not a substitute for authenticated InvoiceQ checks.
Only calculate an amount when every input is usable; schema errors own bad types.
"""

import base64
import binascii
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = Decimal(str(value))
    return result if result.is_finite() else None


def empty(value):
    return value is None or value == "" or (isinstance(value, str) and not value.strip())


def objects(value):
    return [(i, item) for i, item in enumerate(value) if isinstance(item, dict)] if isinstance(value, list) else []


def adjustment_sum(data, key, with_tax=False):
    values = data.get(key, [])
    if not isinstance(values, list):
        return None
    total = Decimal(0)
    for item in values:
        if not isinstance(item, dict) or (amount := number(item.get("amount"))) is None:
            return None
        if with_tax:
            category = item.get("taxType")
            if category not in ("S", "E", "O", "AE", "Z"):
                return None
            amount *= Decimal("1.05") if category == "S" else 1
        total += amount
    return total


class InvoiceBusinessRule:
    def apply(self, context, state):
        if context.intent not in {"validate_request", "explain_failure"} or context.request_json is None:
            return
        from analysis_tools import AnalysisProblem

        invoice = context.request_json
        before = len(state.problems)

        def problem(path, value, reason, action=None):
            if any(p.field == path and p.evidenceSource == "openapi_schema" for p in state.problems):
                return
            state.problems.append(AnalysisProblem(
                field=path, providedValue=value, reason=reason,
                recommendedAction=action or f"Correct {path} according to this documented requirement.",
                evidenceSource="invoiceq_documentation",
            ))

        def require(data, name, prefix, reason):
            if empty(data.get(name)):
                problem(prefix + name, data.get(name), reason, f"Provide {prefix + name}.")

        def compare(data, field, expected, prefix="", rounded=False):
            actual = number(data.get(field))
            if actual is None or expected is None:
                return
            # UAE invoice-level rounding is optional and uses base-currency
            # precision (AED: two decimals). Lines preserve up to 7 decimals.
            quantum = Decimal("0.01") if rounded else Decimal("0.0000001")
            try:
                accepted = expected.quantize(quantum, rounding=ROUND_HALF_UP)
            except InvalidOperation:
                return
            if actual != expected and actual != accepted:
                problem(prefix + field, data[field], f"The amount does not match the documented calculation; expected {expected} (or {accepted} after half-up rounding).")

        for flag in ("isSummaryInvoice", "isContinuousSupply"):
            if invoice.get(flag) is True:
                for name in ("supplyDate", "supplyEndDate"):
                    require(invoice, name, "", f"{name} is required when {flag} is true.")

        currency = invoice.get("currencyIsoCode")
        if isinstance(currency, str) and currency and currency != "AED":
            for name in ("exchangeRate", "totalTaxAmountInBaseCurrency"):
                require(invoice, name, "", f"{name} is required for a non-AED invoice.")
        if "totalAdvancedPaidAmount" in invoice and invoice.get("invoicePrepaymentDetails"):
            problem("totalAdvancedPaidAmount", invoice["totalAdvancedPaidAmount"], "Do not send totalAdvancedPaidAmount together with invoicePrepaymentDetails.")
        principal = invoice.get("principalTaxNumber")
        if isinstance(principal, str) and not re.fullmatch(r"1[0-9]{12}03", principal):
            problem("principalTaxNumber", principal, "Principal TRN must contain 15 digits, start with 1 and end with 03.")
        attachment = invoice.get("invoiceAttachmentBase64")
        if isinstance(attachment, str) and attachment:
            require(invoice, "invoiceAttachmentFileType", "", "Attachment file type is required when an attachment is supplied.")
            try:
                base64.b64decode(attachment, validate=True)
            except (ValueError, binascii.Error):
                problem("invoiceAttachmentBase64", "[attachment omitted]", "Attachment must be valid Base64.")

        products = invoice.get("products")
        lines = objects(products)
        categories = [line.get("taxType") for _, line in lines if isinstance(line.get("taxType"), str)]
        commercial = invoice.get("invoiceType", "STANDARD") == "COMMERCIAL"
        if categories and len(categories) == len(lines) and all(c in ("E", "O") for c in categories) and not commercial:
            problem("products", None, "A non-commercial invoice must contain at least one S, Z, AE, or N line.")

        customer = invoice.get("customerInfo")
        customer_data = customer if isinstance(customer, dict) else {}
        country = customer_data.get("countryIsoCode")
        domestic = country in ("AE", "ARE")
        prefix = "customerInfo."
        if domestic:
            for name in ("arabicName", "entitySchemeId", "registrationNumber", "provinceCode"):
                require(customer_data, name, prefix, f"{name} is required for domestic UAE buyers.")
            if customer_data.get("entitySchemeId") == "TL":
                require(customer_data, "authorityName", prefix, "Issuing authority is required for domestic TL registration.")
            self._emirate(customer_data, prefix, problem)
        if commercial:
            require(customer_data, "registrationNumber", prefix, "Buyer registration number is required for commercial invoices.")
        if "AE" in categories:
            require(customer_data, "entityTaxNumber", prefix, "Buyer TRN is required for reverse-charge lines.")
        if invoice.get("isFreeTradeZone") is True:
            require(customer_data, "beneficiaryId", prefix, "Beneficiary identifier is required for free trade zone scenarios.")
        for name, partner in (("peppolSchemaId", "peppolParticipantId"), ("peppolParticipantId", "peppolSchemaId")):
            if not empty(customer_data.get(name)):
                require(customer_data, partner, prefix, "Peppol scheme and participant identifiers must be supplied together.")
        if isinstance(country, str) and country and not domestic and invoice.get("isExportInvoice") is not True and invoice.get("isDeemedSupply") is not True:
            require(customer_data, "peppolParticipantId", prefix, "This non-UAE buyer does not qualify for a predefined Peppol participant identifier.")
            require(customer_data, "peppolSchemaId", prefix, "A Peppol scheme is required with the participant identifier.")
        delivery = customer_data.get("deliveryAddress")
        if invoice.get("isEcommerce") is True:
            require(customer_data, "deliveryAddress", prefix, "Delivery address is required for e-commerce invoices.")
            if isinstance(delivery, dict):
                for name in ("street", "city"):
                    require(delivery, name, prefix + "deliveryAddress.", "E-commerce delivery requires street and city.")
        if isinstance(delivery, dict) and delivery.get("country") in ("AE", "ARE"):
            if invoice.get("isEcommerce") is True:
                require(delivery, "provinceCode", prefix + "deliveryAddress.", "Domestic e-commerce delivery requires an emirate code.")
            self._emirate(delivery, prefix + "deliveryAddress.", problem)

        def unique(data, key, path):
            seen = set()
            for i, item in objects(data.get(key)):
                code = item.get("attributeCode")
                if isinstance(code, str):
                    if code in seen:
                        problem(f"{path}{key}[{i}].attributeCode", code, "Custom attribute codes must not be duplicated in the same list.")
                    seen.add(code)

        unique(invoice, "customFields", "")
        # Decimal arithmetic avoids binary float noise in seven-decimal lines.
        with localcontext() as decimal_context:
            decimal_context.prec = 1000
            calculated_taxes = []
            for index, line in lines:
                path = f"products[{index}]."
                tax = line.get("taxType")
                rate = number(line.get("taxPercentage"))
                quantity = number(line.get("quantity"))
                cost = number(line.get("unitCost"))
                discount = number(line.get("discountAmount", 0))
                for name, value, invalid, reason in (
                    ("quantity", quantity, quantity is not None and quantity < 0, "Quantity must not be negative."),
                    ("unitCost", cost, cost is not None and cost <= 0, "Unit cost must be greater than zero."),
                ):
                    if invalid:
                        problem(path + name, line[name], reason)
                if commercial and tax in ("S", "AE", "N"):
                    problem(path + "taxType", tax, "Commercial invoices allow only O, E, or Z lines.")
                if invoice.get("isMarginScheme") is True and tax != "N":
                    problem(path + "taxType", tax, "Every margin scheme line must use taxType N.")
                if rate is not None and ((tax == "S" and rate != 5) or (tax in ("E", "O", "AE", "Z") and rate != 0) or (tax == "N" and rate <= 0)):
                    problem(path + "taxPercentage", line["taxPercentage"], "Tax rate must match the category: S = 5, E/O/AE/Z = 0, N > 0.")
                if tax == "E":
                    require(line, "exemptionReasonCode", path, "Exempt lines require an exemption reason code.")
                    code = line.get("exemptionReasonCode")
                    if isinstance(code, str) and code not in ("DL8.46.1", "DL8.46.2", "DL8.46.3", "DL8.46.4"):
                        problem(path + "exemptionReasonCode", code, "Use a documented exemption code DL8.46.1 through DL8.46.4.")
                elif tax in ("S", "O", "AE", "Z", "N") and not empty(line.get("exemptionReasonCode")):
                    problem(path + "exemptionReasonCode", line["exemptionReasonCode"], "Exemption reason codes may be sent only for E lines.")
                if tax == "AE":
                    for name in ("natureCode", "standardItemId"):
                        require(line, name, path, f"{name} is required for reverse charge.")
                commodity = line.get("commodityCode")
                for codes, name in ((("G", "B"), "hsCode"), (("S", "B"), "serviceAccountingCode")):
                    if commodity in codes:
                        require(line, name, path, f"{name} is required for commodityCode {commodity}.")
                vat = number(line.get("lineTotalTaxAmount"))
                if vat is not None and ((tax == "S" and vat <= 0) or (tax in ("AE", "Z", "N") and vat != 0)):
                    problem(path + "lineTotalTaxAmount", line["lineTotalTaxAmount"], "Line VAT must be positive for S and zero for AE, Z, and N.")
                allowances = adjustment_sum(line, "lineAllowances")
                charges = adjustment_sum(line, "lineCharges")
                if all(v is not None for v in (quantity, cost, discount, allowances, charges, rate)):
                    taxable = quantity * cost - discount - allowances + charges
                    expected = taxable * (1 + rate / 100)
                    compare(line, "netAmount", expected, path)
                    # Margin scheme tax treatment needs authority context; do
                    # not infer its document tax from the gross line formula.
                    if tax in ("S", "Z", "E", "O", "AE"):
                        calculated_taxes.append(taxable * rate / 100)
                    if tax == "S" and discount == 0 and allowances == 0 and charges == 0:
                        compare(line, "lineTotalTaxAmount", quantity * cost * rate / 100, path)
                for name in ("unitCost", "discountAmount", "netAmount", "lineTotalTaxAmount"):
                    amount = number(line.get(name))
                    if amount is not None and amount != amount.quantize(Decimal("0.0000001"), rounding=ROUND_HALF_UP):
                        problem(path + name, line[name], "Line amounts support at most seven decimal places.")
                unique(line, "lineCustomFields", path)

            for key in ("invoiceLevelAllowances", "invoiceLevelCharges"):
                for index, item in objects(invoice.get(key)):
                    path = f"{key}[{index}]."
                    tax = item.get("taxType")
                    if isinstance(tax, str) and categories and tax not in categories:
                        problem(path + "taxType", tax, "Document adjustment taxType must match a product line taxType.")
                    if tax == "E":
                        require(item, "exemptionCode", path, "Exempt document adjustments require exemptionCode.")

            if isinstance(products, list) and products and len(lines) == len(products):
                discounts = [number(line.get("discountAmount", 0)) for _, line in lines]
                nets = [number(line.get("netAmount")) for _, line in lines]
                if all(v is not None for v in discounts):
                    compare(invoice, "totalDiscountAmount", sum(discounts), rounded=True)
                allowances = adjustment_sum(invoice, "invoiceLevelAllowances", True)
                charges = adjustment_sum(invoice, "invoiceLevelCharges", True)
                if all(v is not None for v in nets) and allowances is not None and charges is not None:
                    compare(invoice, "totalInvoiceAmount", sum(nets) - allowances + charges, rounded=True)
                if len(calculated_taxes) == len(products) and allowances is not None and charges is not None:
                    allowance_net = adjustment_sum(invoice, "invoiceLevelAllowances")
                    charge_net = adjustment_sum(invoice, "invoiceLevelCharges")
                    compare(invoice, "totalTaxAmount", sum(calculated_taxes) - (allowances - allowance_net) + (charges - charge_net), rounded=True)
            total = number(invoice.get("totalInvoiceAmount"))
            advanced = number(invoice.get("totalAdvancedPaidAmount", 0))
            if total is not None and advanced is not None:
                compare(invoice, "totalNetAmount", total - advanced, rounded=True)
            tax_total = number(invoice.get("totalTaxAmount"))
            exchange = number(invoice.get("exchangeRate"))
            if currency != "AED" and tax_total is not None and exchange is not None:
                compare(invoice, "totalTaxAmountInBaseCurrency", tax_total * exchange, rounded=True)

        if len(state.problems) > before:
            state.status = "failure"

    @staticmethod
    def _emirate(data, prefix, problem):
        value = data.get("provinceCode")
        if isinstance(value, str) and value and value not in ("AUH", "DXB", "SHJ", "UAQ", "FUJ", "AJM", "RAK"):
            problem(prefix + "provinceCode", value, "Use an emirate code: AUH, DXB, SHJ, UAQ, FUJ, AJM, or RAK.")
