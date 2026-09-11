# CreditProduct

Credit Note Product Lines

## Fields

### productCode

Required: Yes
Type: string
Description: Refunded Item code as per outward invoice

### description

Required: Yes
Type: string
Description: Refunded Item description

### creditedQuantity

Required: Yes
Type: number
Format: double
Description: Credited quantity for the line. Must not be negative and must not exceed remaining un-refunded quantity on the original invoice.

### taxPercentage

Required: No
Type: integer
Format: int32
Description: VAT rate percent for the credited line. Must match taxType: S = 5, Z = 0, N > 0. For E, O, and AE use 0 unless otherwise required by the category rules.

### creditDiscountAmount

Required: Yes
Type: number
Format: double
Description: Price-level discount on this credited line. Line-total excluding VAT. Pass 0 when unused. Do not also send the same amount as lineAllowances.

### creditedNetAmount

Required: Yes
Type: number
Format: double
Description: Net credit amount for the line including VAT. Must equal ((creditedQuantity × unitCost) − creditDiscountAmount − Σ lineAllowances + Σ lineCharges) × (1 + (taxPercentage / 100)) when those fields are provided.

### creditedTaxAmount

Required: Yes
Type: number
Format: double
Description: Credited line VAT amount. Must be greater than zero for taxType S. Must be zero for taxType AE, Z, and N (and typically zero for E/O).

### lineAllowances

Required: No
Type: array
Description: Allowances on this credited line (PINT CreditNoteLine/AllowanceCharge). Amounts excluding VAT. Distinct from creditDiscountAmount (price-level).
Array items: InvoiceLevelAllowance

### lineCharges

Required: No
Type: array
Description: Charges on this credited line (PINT CreditNoteLine/AllowanceCharge). Amounts excluding VAT.
Array items: InvoiceLevelCharge

### unitType

Required: Yes
Type: string
Description: Unit of measurement code for the credited line. Recommended to follow UN/ECE Recommendation 20.

### taxType

Required: No
Type: string
Description: PINT AE VAT category for the credited line. Optional override; when omitted InvoiceQ resolves from the original invoice line or catalog item. Allowed: S, E, O, AE, Z, N. Margin scheme requires N; commercial (480) allows O, E, or Z only. Non-commercial documents need at least one S, Z, AE, or N line. For AE, natureCode and standardItemId (GTIN) must exist on the catalog item.
Allowed values: S, E, O, AE, Z, N

### invoiceIQReference

Required: No
Type: string
Description: Original InvoiceQ invoice reference for this credited line when the credit spans multiple invoices.

### exemptionReasonCode

Required: No
Type: string
Description: VAT exemption reason code. Required only when taxType is E (exempt); use DL8.46.1–DL8.46.4 from '/api/external/v1/lookups/exemptions'. Do not send for Z (zero-rated), AE, S, O, or N. May fall back to the original invoice line reason when omitted.

### productName

Required: No
Type: string
Description: Refunded item name as shown on the credit note.

### lineCustomFields

Required: No
Type: array
Description: List of custom fields identified using the portal, <br>1.Must not contain duplicate attributeCode, <br> 2.Required/Optional will be validated based on definition in the portal
Array items: CustomAttribute
