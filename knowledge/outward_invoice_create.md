# Create Outward Invoice

Method: POST
Path: /api/external/v2/outward-invoice/create

Summary: Create Outward Invoice

Description: Upload Outward Invoice with attachments in base64string format

Request schema: OutwardInvoice

## Responses

### HTTP 200
OK
Response schema: OutwardInvoiceOperationResponse

### HTTP 208
Already reported, a document with the same reference was uploaded before. When the channel uses RETRIEVE_DUPLICATE_DETAILS the existing document details are returned in the body
Response schema: OutwardInvoiceOperationResponse

### HTTP 400
Validation or business error, details are provided in the errors list
Response schema: OutwardInvoiceOperationResponse

### HTTP 401
Unauthorized, session is missing or invalid
Response schema: ResponseEnvelop

### HTTP 403
Forbidden, the bearer token is expired or malformed

### HTTP 500
Internal server error
Response schema: ResponseEnvelop
