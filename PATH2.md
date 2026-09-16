# Path 2: authenticated invoice questions

## Status

Python tools and the Spring authentication/database integration are implemented.
Spring source is in `C:/Users/Admin/Desktop/demo1`; follow its PATH2_SETUP.md.
The Angular page includes login/logout and authenticated invoice questions.
Use the controlled bootstrap command to create each real company and admin.
No sample data is inserted. PostgreSQL invoiceAi still requires the locally
entered password and a first startup to apply its dedicated-schema migrations.
Spring sessions are revocable one-hour bearer tokens; Python forwards the same
user token. Initial scope is one company per account, without company switching.

Path 1 is unchanged and cannot query stored invoices. Path 2 does not use RAG.

## Python API

POST `/ai/invoices/query`
Authorization: Bearer <real user access token>

```json
{"question":"Total including tax for invoices with status CLEARED"}
```

Only question is accepted in the body. Authentication is checked through Spring
before the LLM is called. Company IDs are never accepted from model arguments.
At most one data query and three Gemini calls are performed per request (two routing attempts for transient provider failures, then one explanation).

Totals return the before-tax total, tax-inclusive total and remaining payable amount together; no amount-type clarification is needed. Unclear individual invoice identifiers still trigger clarification.
Always ask for status filters before calculating totals unless explicitly
specified. "All my invoices" alone is not a choice of all statuses. No silent
exclusion of cancelled/rejected invoices. No currency conversion.

This first endpoint is stateless: resend the complete question after a
clarification. The authenticated UI is available; persistent conversation state is not implemented. Supported amount types are totalIncludingTax and remainingPayable;
Spring maps these to total_including_tax and remaining_payable decimal columns.

## Spring adapter contract

These routes are now implemented in demo1 against its dedicated invoice_ai schema.
Every route must independently validate the user token, resolve the active company
from trusted context and check permissions. Never authorize by a company header
alone. Company switching must check membership. Never use a shared service token
as a substitute for user identity.

GET `/internal/invoice-assistant/context`

```json
{
  "corporationId":"A",
  "allowedTools":["get_invoice_amount","get_invoice_totals"],
  "allowedStatuses":["CLEARED","UNCLEARED","PENDING"]
}
```

These integration-status values are documented in InvoiceQ UAE Swagger. They are not payment statuses.

POST `/internal/invoice-assistant/amount`

```json
{"invoiceNumber":"001","amountType":"totalIncludingTax","statuses":[]}
```

Use exact invoice-number matching within the authorized company, preserving
leading zeros. An unspecified "ID" needs clarification, not guessing a database
primary key. Use parameterized SQL and mandatory company predicates. Return
not_found both for nonexistent numbers and numbers in another company. Multiple
matches within one company return ambiguous rather than choosing arbitrarily.

POST `/internal/invoice-assistant/totals`

```json
{
  "amountType":"totalIncludingTax",
  "statusScope":"selected",
  "statuses":["CLEARED"],
  "currency":"AED",
  "dateFrom":"2026-01-01",
  "dateTo":"2026-09-15"
}
```

Currency and inclusive invoice issue-date bounds are optional. Define the date
timezone in the backend. statusScope all requires an empty statuses list. Compute
SUM and COUNT in the database using decimal columns, grouped by currency. Do not
return all invoice rows for the LLM to aggregate. Decide credit-note treatment
before extending these tools to credit notes. Reject unsupported filters.

Both operations return:

```json
{
  "corporationId":"A",
  "status":"ok",
  "invoiceNumber":null,
  "amountType":"totalIncludingTax",
  "totals":[{"currency":"AED","amount":"12500.00","invoiceCount":20}]
}
```

For an individual invoice return its exact invoiceNumber and one row with count 1.
Other statuses: not_found, ambiguous, no_matches, with empty totals. Monetary
values should be decimal strings. Database failures must return HTTP errors,
never a successful zero. Invalid tokens return 401; denied permissions return 403.
Python checks returned company, amount type, currency, and lookup consistency
before sending any result to Gemini. Spring still owns enforcement in the query.

## Result presentation

Response includes answer, tool (applied arguments), result and explanationSource.
Render structured amounts/currencies and filters as the authoritative values.
LLM prose is supplementary and can be inaccurate. Final-generation outages
preserve data and return template text. Routing distinguishes provider quota (429), temporary provider failures after a bounded retry (503), timeout (504), and rejected configuration or invalid model output (502). Backend failures return 502. Never display a service failure as an invoice balance of zero.

## Configuration and deployment

INVOICE_BACKEND_URL is configured in local .env as
`http://127.0.0.1:8080`. Remote destinations require HTTPS. Existing GEMINI_API_KEY
and GEMINI_MODEL are reused. Missing configuration returns 503. No new store is
needed. Redirect following and environment proxies are disabled on backend calls.
Deploy behind the authenticated application gateway with TLS and rate limits;
never log authorization tokens or put them in query strings.

## Tests

`.\.venv\Scripts\python.exe -m unittest discover -s tests -v`

Tests simulate Spring and Gemini, including company mismatches, invalid auth,
restricted operations, ambiguous inputs, mixed currencies, outages, and the API.
They do not prove real database isolation. Before enabling production, test the
Spring implementation with invoice 001 in both companies, company B data queried
by company A, expired sessions, unauthorized roles and independent totals.


## Router schema compatibility

The router uses response_json_schema with InvoiceToolCall.model_json_schema().
Using response_schema with this strict Pydantic model caused Gemini to reject
additional_properties with HTTP 400; older code incorrectly wrapped that as 503.
Local validation still rejects extra tool arguments, including company overrides.
Logs include provider status/error type only, not tokens, invoice data, or raw
provider exception text. A successful local SDK serialization test does not prove
provider acceptance; test the live routing call separately after schema changes.

## Totals overview and existing records

Each currency row now includes totalExcludingTax, totalIncludingTax,
remainingPayable and missingPreTaxCount, alongside the compatible amount field.
The primary amount defaults to remainingPayable, but all three amounts are
returned regardless of that selection. Remaining payable already includes tax
and reflects recorded payments; never add VAT to it again.

Spring migration V2 preserves V1 unchanged, retains original values in
legacy_status, and copies only CLEARED into the corrected status field.
Legacy REJECTED/DRAFT/CANCELLED require verification instead of automatic mapping.
All-status totals that match unresolved rows return 409; selected integration
statuses include only verified matching rows. An ADMIN can record a verified
status via PATCH /api/admin/invoices/{id}/integration-status with {"status":"PENDING"}.
Both role and company ownership are checked.

A nullable total_excluding_tax column stores the actual before-tax amount.
Populate totalExcludingTax when creating invoices. Old invoices remain NULL until
their real values are supplied. If any matching row lacks that value, the entire
currency's before-tax total is unavailable (not a partial sum or a guessed 5%
calculation); the other two totals are still returned. Records are not connected
to live payment synchronization, so balances reflect the data stored locally.

Source: https://sandbox.invoiceq.com/swagger-ui/uae/specs/full.json
