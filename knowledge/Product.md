# Product

## Fields

### productCode

Required: Yes
Type: string
Description: Product unique identifier, could be barcode

### productName

Required: Yes
Type: string
Description: <u>Required</u> Product name as it would show in generated invoice

### description

Required: No
Type: string
Description: Product description as it would show in generated invoice

### unitType

Required: Yes
Type: string
Description: Unit of measurement code for the line. Recommended to follow UN/ECE Recommendation 20.

### commodityCode

Required: No
Type: string
Description: Commodity classification for the item. Optional; when provided must be G (goods), S (services), or B (both). G or B requires hsCode. S or B requires serviceAccountingCode.
Allowed values: G, S, B

### hsCode

Required: No
Type: string
Description: Harmonized System (HS) code for goods. Required when commodityCode is G or B.

### serviceAccountingCode

Required: No
Type: string
Description: Service accounting code (SAC). Required when commodityCode is S or B.

### natureCode

Required: No
Type: string
Description: Nature of goods code for reverse-charge lines. Required when taxType is AE. Allowed values: DL8.48.8.2, DL8.48.8.1, DL8.48.3.1, DL8.48.3.2, DL8.48.3.3.
Allowed values: DL8.48.8.2, DL8.48.8.1, DL8.48.3.1, DL8.48.3.2, DL8.48.3.3

### standardItemId

Required: No
Type: string
Description: Standard item identifier (GTIN). Required when taxType is AE (reverse charge).

### quantity

Required: Yes
Type: number
Format: double
Description: Line quantity. Must not be negative.

### unitCost

Required: Yes
Type: number
Format: double
Description: Unit price excluding VAT. Must be greater than zero.

### discountAmount

Required: No
Type: number
Format: double
Description: Price-level discount on this line (PINT Price/AllowanceCharge). Line-total excluding VAT. Omit or pass 0 when unused. Do not also send the same amount as lineAllowances.

### netAmount

Required: Yes
Type: number
Format: double
Description: Line amount payable including VAT. Must equal ((quantity × unitCost) − discountAmount − Σ lineAllowances + Σ lineCharges) × (1 + (taxPercentage / 100)).

### lineAllowances

Required: No
Type: array
Description: Allowances on this line (PINT InvoiceLine/AllowanceCharge). Amounts excluding VAT. Distinct from discountAmount (price-level).
Array items: InvoiceLevelAllowance

### lineCharges

Required: No
Type: array
Description: Charges on this line (PINT InvoiceLine/AllowanceCharge). Amounts excluding VAT.
Array items: InvoiceLevelCharge

### taxType

Required: Yes
Type: string
Description: PINT AE VAT category for the line. Allowed: S (standard 5%), E (exempt), O (out of scope), AE (reverse charge), Z (zero-rated), N (margin scheme). Margin scheme invoices require N on every line. Commercial (480) invoices allow O, E, or Z only. Non-commercial invoices must include at least one S, Z, AE, or N line (cannot be E/O-only).
Allowed values: S, E, O, AE, Z, N

### taxPercentage

Required: Yes
Type: integer
Format: int32
Description: VAT rate percent for the line. Must match taxType: S = 5, Z = 0, N > 0. For E, O, and AE use 0 unless otherwise required by the category rules.

### lineTotalTaxAmount

Required: No
Type: number
Format: double
Description: Line VAT amount in the invoice currency. Must be greater than zero for taxType S. Must be zero for taxType AE, Z, and N (and typically zero for E/O). For standard-rated lines: quantity * unitCost * (taxPercentage / 100).

### exemptionReasonCode

Required: No
Type: string
Description: VAT exemption reason code. Required only when taxType is E (exempt); use DL8.46.1–DL8.46.4 from '/api/external/v1/lookups/exemptions'. Do not send for Z (zero-rated), AE, S, O, or N.

### lineCustomFields

Required: No
Type: array
Description: List of custom fields identified using the portal, <br>1.Must not contain duplicate attributeCode, <br> 2.Required/Optional will be validated based on definition in the portal
Array items: CustomAttribute
