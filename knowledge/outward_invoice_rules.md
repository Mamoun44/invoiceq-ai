Documentation

- Saudi Arabia

- Egypt

- Jordan

- UAE

- Oman

# Outward Invoices

Submit sales invoices to InvoiceQ for UAE clearance or reporting, search what you already submitted, and download the generated document. UAE uses the V2 create endpoint only.

## Create

Use /api/external/v2/outward-invoice/create . Attachments are sent inline as base64. Your invoiceNumber must be unique under the chosen duplicateMode .

## Invoice type and buyer

UAE invoiceType values are STANDARD , SELF_BILLING , or COMMERCIAL (defaults to STANDARD ). Buyer details go in customerInfo ; domestic UAE buyers use commercial registration identifiers ( entitySchemeId such as TL / EID / PAS / CD), while export buyers use the foreign registration id when available.

## Duplicates and response shape

duplicateMode rejects a repeated number by default, or returns HTTP 208 with existing document details when set to RETRIEVE_DUPLICATE_DETAILS . responseTemplate selects PDF, XML, QR, or none.

## Search defaults

When invoiceStatus is omitted, search returns CLEARED invoices only.

## Endpoints

Click a row to jump to that operation in the explorer.

## API explorer

Try requests against the sandbox server after authorizing.

JavaScript is required for the API explorer. Download this page's OpenAPI document .
