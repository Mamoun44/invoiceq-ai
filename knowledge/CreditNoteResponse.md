# CreditNoteResponse

CreditNote response would be provided for successful uploads, incase of any failuer this would be null

## Fields

### invoiceqReference

Required: No
Type: string
Description: InvoiceQ reference for uploaded credit note

### creditNoteNumber

Required: No
Type: string
Description: Credit Note Number provided by customer on creation request

### pdfFileName

Required: No
Type: string
Description: Generated Credit Note PDF Filename

### base64PDF

Required: No
Type: string
Description: Generated Credit Note PDF

### encodedXml

Required: No
Type: string
Description: Generated Xml Invoice

### qrCode

Required: No
Type: string
Description: Generated Qr Code

### directLink

Required: No
Type: string
Description: Credit Note Download Link

### duplicateNotes

Required: No
Type: array
Description: Previously reported notes with same number
Array items: CreditNoteList

### submittedPayableAmount

Required: No
Type: number
Format: double
Description: Submitted Payable Amount for Tax Authority

### submittedTaxAmount

Required: No
Type: number
Format: double
Description: Submitted Tax Amount for Tax Authority

### submittedPayableRoundingAmount

Required: No
Type: number
Format: double
Description: Submitted Payable Rounding Amount for Tax Authority

### integrationStatus

Required: No
Type: string
Description: Third Party Integration Status
