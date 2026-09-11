# OutwardInvoice

<b>Upload Outward Invoice : </b><br> 1.All totals on invoice level can be rounded optionally to number of decimals of country base currency<br> 2.For lines level, amounts must be passed with full fractions (up to 7) regardless of currency decimals <br> 3.Any rounding should follow half-up mode

## Fields

### invoiceNumber

Required: Yes
Type: string
Description: Invoice Number/Reference as exists on customer systems, must be <u>unique</u> in case same invoice number provided for another invoice the new one will be rejected following duplicateMode

### identifierCode

Required: No
Type: string
Description: Corporate Identification Code Registered previously in InvoiceQ

### poReference

Required: No
Type: string
Description: Purchase Order Reference Number

### currencyIsoCode

Required: Yes
Type: string
Description: Currency code to be used for currency identifiers and tags for all amounts within the invoice, <br> <u>alpha iso code</u> as described in the [ISO 4217](https://www.iban.com/currency-codes)
Allowed values: JOD, USD, SAR, EGP, AED, BHD, QAR, EUR, KWD, OMR, YER, IQD, INR, HKD, GBP, CHF, SEK

### invoiceType

Required: No
Type: string
Description: Invoice type. Allowed values: STANDARD, SELF_BILLING, COMMERCIAL. Defaults to STANDARD when not provided.
Allowed values: STANDARD, SELF_BILLING, COMMERCIAL

### duplicateMode

Required: No
Type: string
Description: How invoiceq would handle the duplicates, by default this would be REJECT_WITH_FAILURE mode <br> <b>REJECT_WITH_FAILURE</b>: incase same document already uploaded, invoiceq would reject the new request with Generic error and HTTP 400<br> <b>RETRIEVE_DUPLICATE_DETAILS</b>: incase same document already uploaded, invoiceq would response with http 208 along with providing the uploaded document details in the body without the generated PDF/XML/QR
Allowed values: REJECT_WITH_FAILURE, RETRIEVE_DUPLICATE_DETAILS

### responseTemplate

Required: No
Type: string
Description: The response type you need to be received, default is PDF_A3, <br> XML only functional incase TAX Authority enabled
Allowed values: PDF_A3, XML, QR, NONE, QRANDXML

### issueDate

Required: Yes
Type: string
Format: date-time
Description: zoned datetime format yyyy-mm-ddThh24:mi:ssZ, i.e. 2021-07-01T18:23:00Z

### dueDate

Required: No
Type: string
Format: date-time
Description: Zoned datetime format yyyy-mm-ddThh24:mi:ssZ, i.e. 2021-07-01T18:23:00Z <br> incase not provided will be stored with value same as issueDate

### supplyDate

Required: No
Type: string
Format: date-time
Description: <u>Conditional</u> <br>must be provided for Normal Invoices, incase not provided will be copied from issueDate tag <br>zoned datetime format yyyy-mm-ddThh24:mi:ssZ, i.e. 2021-07-01T18:23:00Z

### supplyEndDate

Required: No
Type: string
Format: date-time
Description: <u>Conditional</u> <br>must be provided for invoices related supplies over period<br>zoned datetime format yyyy-mm-ddThh24:mi:ssZ, i.e. 2021-07-01T18:23:00Z

### customerInfo

Required: No
References schema: CustomerInfo

### products

Required: Yes
Type: array
Description: List of products/services
Array items: Product

### customFields

Required: No
Type: array
Description: List of custom fields identified using the portal, <br>1.Must not contain duplicate attributeCode, <br> 2.Required/Optional will be validated based on definition in the portal
Array items: CustomAttribute

### totalDiscountAmount

Required: Yes
Type: number
Format: double
Description: Total discount given to customer, if no discount to be passed as zero. This is the summation of all discounts provided on the product lines only.

### totalInvoiceAmount

Required: Yes
Type: number
Format: double
Description: Total invoice amount including VAT, after line discounts, line allowances/charges, and invoice-level allowances/charges. Amounts may be rounded to the number of decimals of the country base currency.

### totalNetAmount

Required: Yes
Type: number
Format: double
Description: Total net amount the customer needs to pay, including taxes and after discounts. totalNetAmount = totalInvoiceAmount - totalAdvancedPaidAmount. Amounts may be rounded to the number of decimals of the country base currency.

### totalAdvancedPaidAmount

Required: No
Type: number
Format: double
Description: Sum of amounts paid in advance on this invoice (PINT IBT-113). Optional; omit or pass zero when none. totalNetAmount = totalInvoiceAmount - totalAdvancedPaidAmount. Do not send together with invoicePrepaymentDetails (FTA two-invoice advance).

### payableRoundingAmount

Required: No
Type: number
Format: double
Description: Payable Rounding Amount

### invoiceLevelAllowances

Required: No
Type: array
Description: Document-level allowances (PINT Invoice/AllowanceCharge). Amounts excluding VAT.
Array items: InvoiceLevelAllowance

### invoiceLevelCharges

Required: No
Type: array
Description: Document-level charges (PINT Invoice/AllowanceCharge). Amounts excluding VAT.
Array items: InvoiceLevelCharge

### invoicePrepaymentDetails

Required: No
Type: array
Description: Optional references to previously issued advance tax invoices (FTA §17.1). Each entry becomes a preceding invoice reference (IBT-025 / IBT-026). Only prepaymentInvoiceRef and invoiceDate are used. Do not send together with totalAdvancedPaidAmount.
Array items: InvoiceLevelPrepaymentDetails

### totalTaxAmount

Required: Yes
Type: number
Format: double
Description: Total tax amount collected from customer, if no tax to be passed as zero, it is possible to have tax as zeros in product list while it has value here. <br>In case discount on product level this should be the sum up of all discounts provided in product level<br> *totalTaxAmount can be rounded optionally to number of decimals of country base currency*

### totalTaxAmountInBaseCurrency

Required: No
Type: number
Format: double
Description: Total tax amount in AED (UAE base currency). Required when the invoice currency is not AED. Amounts may be rounded to the number of decimals of the country base currency.

### exchangeRate

Required: No
Type: number
Format: double
Description: Required when the invoice currency is not AED. Exchange rate from invoice currency to AED.

### isExportInvoice

Required: No
Type: boolean
Description: Set true when supplying goods/services to a non-UAE buyer. Export invoices relax domestic UAE buyer rules (TRN, TL/EID/PAS/CD, emirate provinceCode). customerInfo.deliveryAddress is required for export only when the deliver-to country is not AE/ARE. When neither customerInfo.peppolParticipantId nor customerInfo.peppolSchemaId is provided, InvoiceQ automatically applies EndpointID 9900000099 with scheme ID 0235.

### isSummaryInvoice

Required: No
Type: boolean
Description: The invoice is issued for sales occurring over a period of time and occurs for some types of invoicing arrangements between seller and buyer, require supply date and supply end date, default is false

### isDeemedSupply

Required: No
Type: boolean
Description: Whether the invoice relates to a deemed supply under UAE VAT rules. Defaults to false. When neither customerInfo.peppolParticipantId nor customerInfo.peppolSchemaId is provided, InvoiceQ automatically applies EndpointID 9900000097 with scheme ID 0235.

### isDisclosedAgentBilling

Required: No
Type: boolean
Description: Whether the invoice uses disclosed agent billing. Defaults to false.

### isContinuousSupply

Required: No
Type: boolean
Description: Whether the invoice covers a continuous supply over a period. Requires supplyDate and supplyEndDate. Defaults to false.

### isFreeTradeZone

Required: No
Type: boolean
Description: Whether the supply is from or to a designated free trade zone. Defaults to false.

### isEcommerce

Required: No
Type: boolean
Description: Whether the invoice is an e-commerce transaction. Defaults to false. When true, customerInfo.deliveryAddress is required (street and city; emirate provinceCode when delivery country is AE/ARE).

### isMarginScheme

Required: No
Type: boolean
Description: Whether the invoice uses the profit margin scheme. Defaults to false.

### paymentMeans

Required: Yes
Type: integer
Format: int32
Description: Payment means for the invoice. Only cash is supported today — always send UN/ECE 4461 code 10.
Allowed values: 10

### principalTaxNumber

Required: No
Type: string
Description: Principal tax registration number for disclosed agent billing. Must be exactly 15 digits, start with 1, and end with 03.

### invoiceAttachmentBase64

Required: No
Type: string
Description: Supporting document jpg or png image file to be shared with customer, should be Base64 string

### invoiceAttachmentFileType

Required: No
Type: string
Description: Supporting document file type, must be provided incase invoiceAttachmentBase64 has value, <u>note this is not the requested response format</u>
Allowed values: JPEG, PNG, JPG, PDF

### extraPrintDetails

Required: No
Type: string
Description: Extra print details to be used integrated layout.

### narration

Required: No
Type: string
Description: Invoice note (PINT IBT-022). Use this for FTA §17.1 when linking a final invoice to an advance tax invoice in prose, instead of or in addition to invoicePrepaymentDetails.
