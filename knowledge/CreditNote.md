# CreditNote

Credit Note

## Fields

### invoiceIQReference

Required: No
Type: string
Description: InvoiceQ outward invoice reference of the invoice being credited. Required unless <code>creditReason</code> is <code>VD</code> (volume discount). When <code>creditReason</code> is <code>VD</code>, this field must be omitted so that no BillingReference is generated.

### invoiceType

Required: No
Type: string
Description: UAE credit note document type. Required when creditReason is <code>VD</code> because no original invoice is available to determine the document type.<br>Allowed values: STANDARD (tax credit note), COMMERCIAL (out-of-scope commercial credit note), or SELF_BILLING (self-billed credit note).
Allowed values: SIMPLE, NORMAL, STANDARD, SELF_BILLING, COMMERCIAL

### currencyIsoCode

Required: No
Type: string
Description: Currency in which all credit note amounts are stated, except amounts explicitly stated in the tax accounting currency.<br>Required when creditReason is <code>VD</code> because no original invoice is available to determine the currency. Use an [ISO 4217 alpha-3 currency code](https://www.iso.org/iso-4217-currency-codes.html), for example AED or USD.<br>When the currency is not AED, exchangeRate and totalTaxAmountInBaseCurrency are required.
Allowed values: JOD, USD, SAR, EGP, AED, BHD, QAR, EUR, KWD, OMR, YER, IQD, INR, HKD, GBP, CHF, SEK

### updatedCustomer

Required: Yes
References schema: CustomerInfo

### creditNoteMode

Required: No
Type: string
Description: For the AMOUNT credit mode will be on the total invoice amount as it will credit a specific amount from the total invoice amount only; no quantities or items can be credited here just a certain amount from the total amount. <br>For the AMOUNT_WITH_QUANTITY mode will be to credit a specific quantity or amount from the chosen item/s - the credit note will contain the credited amount or quantity from each invoice item
Allowed values: AMOUNT, AMOUNT_WITH_QUANTITY, AMOUNT_WITH_COUNT

### creditNoteNumber

Required: Yes
Type: string
Description: Unique credit note reference number as per originating system, incase duplicate will be rejected

### narration

Required: No
Type: string
Description: Credit note narration, incase not provided will be defaulted to Credit Note

### poReference

Required: No
Type: string
Description: Purchase Order Reference Number

### identifierCode

Required: No
Type: string
Description: Corporate Identification Code Registered previously in InvoiceQ

### customFields

Required: No
Type: array
Description: List of custom fields identified using the portal, <br>1.Must not contain duplicate attributeCode, <br> 2.Required/Optional will be validated based on definition in the portal
Array items: CustomAttribute

### issueDate

Required: Yes
Type: string
Format: date-time
Description: zoned datetime format yyyy-mm-ddThh24:mi:ssZ, i.e. 2021-07-01T18:23:00Z, if not provided will be current date time

### supplyDate

Required: No
Type: string
Format: date-time
Description: zoned datetime for the supply date or supply start date incase of supply over period <br>format yyyy-mm-ddThh24:mi:ssZ, i.e. 2021-09-02T18:23:00Z

### supplyEndDate

Required: No
Type: string
Format: date-time
Description: [Conditional] - Required for of supply over periods <br>zoned datetime format yyyy-mm-ddThh24:mi:ssZ, i.e. 2021-09-02T18:23:00Z

### creditReason

Required: Yes
Type: string
Description: Credit note reason code. Required. One of: DL8.61.1.A, DL8.61.1.B, DL8.61.1.C, DL8.61.1.D, DL8.61.1.E, VD.
Allowed values: DL8.61.1.A, DL8.61.1.B, DL8.61.1.C, DL8.61.1.D, DL8.61.1.E, VD

### creditProducts

Required: Yes
Type: array
Description: List of refunded products
Array items: CreditProduct

### noteLevelAllowances

Required: No
Type: array
Description: Document-level allowances (PINT CreditNote/AllowanceCharge). Amounts excluding VAT.
Array items: InvoiceLevelAllowance

### noteLevelCharges

Required: No
Type: array
Description: Document-level charges (PINT CreditNote/AllowanceCharge). Amounts excluding VAT.
Array items: InvoiceLevelCharge

### totalTaxAmount

Required: No
Type: number
Format: double
Description: Total VAT credited across lines. Must equal the sum of creditedTaxAmount (within rounding tolerance).

### totalCreditNetAmount

Required: No
Type: number
Format: double
Description: Total credit note net amount including VAT. Same as creditAmountWithAllowanceAndCharge. Note-level allowances and charges are reflected in creditAmountWithAllowanceAndCharge.

### creditAmountWithAllowanceAndCharge

Required: Yes
Type: number
Format: double
Description: Total credit note amount including VAT, after note-level allowances and charges. Required. Must equal Σ creditedNetAmount − Σ note-level allowances (gross) + Σ note-level charges (gross) (within rounding tolerance).

### payableRoundingAmount

Required: No
Type: number
Format: double
Description: Payable Rounding Amount

### exchangeRate

Required: No
Type: number
Format: double
Description: Required when the credit note currency is not AED. Exchange rate from credit note currency to AED.

### totalTaxAmountInBaseCurrency

Required: No
Type: number
Format: double
Description: Total credit note tax amount in AED (UAE base currency). Required when the credit note currency is not AED.

### attachmentBase64

Required: No
Type: string
Description: Supporting document jpg or png image file to be shared with customer, should be Base64 string

### attachmentFileType

Required: No
Type: string
Description: Supporting document file type, must be provided incase invoiceAttachmentBase64 has value, <u>note this is not the requested response format</u>
Allowed values: JPEG, PNG, JPG, PDF

### extraPrintDetails

Required: No
Type: string
Description: Extra print details to be used integrated layout.

### isDisclosedAgentBilling

Required: No
Type: boolean
Description: Whether the credit note uses disclosed agent billing. Defaults to false. When true, principalTaxNumber is required and must differ from the seller TRN.

### principalTaxNumber

Required: No
Type: string
Description: Principal tax registration number for disclosed agent billing. Must be exactly 15 digits, start with 1, and end with 03.
