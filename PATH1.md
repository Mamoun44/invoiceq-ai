# Anonymous InvoiceQ integration path

This path has no authenticated customer, company context, database access, or
stored invoices. The caller supplies a question plus an InvoiceQ request, an
InvoiceQ response, or both.

## Runtime flow

1. Gemini classifies the question into a constrained intent.
2. `IntegrationAnalysisTool` runs an ordered Python rule chain.
   This includes recursive OpenAPI validation and documented UAE business rules,
   whether or not the caller supplies an InvoiceQ error response.
3. Gemini File Search adds only relevant documented InvoiceQ rules.
4. The tool returns an `AnalysisResult` JSON object.
5. Gemini converts that JSON into a short human-readable answer.

Stored-invoice questions are classified as `stored_invoice_query` and are
refused because this path has no authenticated data access.

## Compatible request shapes

The existing Spring contract remains supported:

```json
{
  "invoice": {},
  "invoiceqError": {},
  "question": "Why did this request fail?"
}
```

Explicit integration names are also accepted:

```json
{
  "requestJson": {},
  "responseJson": {},
  "question": "What does this error mean?"
}
```

## Endpoints

- `POST /ai/analyze` returns the internal normalized `AnalysisResult` JSON for
  testing and observability.
- `POST /ai/explain` preserves the original structured explanation response.
- `POST /ai/explain/stream` returns the final short answer as SSE tokens.

## Invoice validation

`analysis_tools.py` validates the create-invoice request against the bundled
`data/invoiceq_uae_openapi.json`: required fields, nested objects and array items,
strict JSON types, allowed values, integer ranges, and zoned date-time formats.
Unknown properties are allowed because this specification does not prohibit
them. Optional `invoiceType` can be omitted. `paymentMeans` must be integer 10;
the specification's string-encoded enum is normalized without accepting string
input. The shared allowance/charge schema's taxType requirement is waived for
line adjustments, where its description says the line's category applies.

`invoice_validation.py` implements rules from the bundled `knowledge` files:

- Customer domestic identifiers, emirates, Peppol pairs and fallback conditions;
  e-commerce delivery, free-zone beneficiary and reverse-charge buyer TRN.
- Summary/continuous supply dates, foreign-currency fields, attachment format,
  principal TRN format, prepayment exclusivity and duplicate custom attributes.
- Commercial/margin tax categories, rates, exemptions, reverse-charge fields,
  commodity identifiers, quantities and unit prices.
- Line net amounts, discounts, document allowances/charges, invoice totals,
  payable amounts after advances, ordinary VAT totals and AED conversion.
- Decimal arithmetic, optional two-decimal UAE invoice rounding with half-up
  mode, and up to seven decimals on line monetary values.

Retrieved documentation findings are merged only when they identify a source
and field matching a retrieved rule. These model-assisted findings supplement
the deterministic checks; they do not guarantee exhaustive retrieval.

### Meaning and limits of the result

`problems` contains all detected issues, using paths such as
`products[1].netAmount`. `evidenceSource` distinguishes returned InvoiceQ errors
from schema and documentation findings. With no InvoiceQ response, `failure`
means local problems were detected, not that a submission actually failed.
For request-only validation, `facts.localValidationPassed` records whether the
deterministic checks passed; a clean invoice keeps `status: unknown` because
server acceptance has not been checked. Retrieval outages preserve local issues.

The bundled schema and documentation are the supported validation baseline.
Duplicate invoice numbers, saved customer data, registered custom fields,
dynamic lookup codes and authority-only requirements require server context.
An absent export delivery address cannot be rejected just from buyer country:
the actual deliver-to country is needed. Margin-scheme document VAT and the
interaction of `payableRoundingAmount` with totals are not fully specified in
the bundled sources. For standard lines with discounts/adjustments, the docs'
line-VAT formula is ambiguous, so only the VAT category constraints are applied
to `lineTotalTaxAmount`; net and ordinary document VAT calculations still use
the documented taxable amounts. These cases require InvoiceQ confirmation.

### Run the tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests cover the local validator, retrieval merge/failure behavior and API
contracts with mocked Gemini responses. They do not submit invoices or consume
Gemini quota.
