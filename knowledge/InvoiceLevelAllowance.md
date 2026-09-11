# InvoiceLevelAllowance

Allowances on Invoice/Note Level

## Fields

### amount

Required: Yes
Type: number
Format: double
Description: Amount excluding VAT. On invoiceLevelAllowances / noteLevelAllowances: this document-level allowance amount. On lineAllowances: this line's allowance amount. Not a per-tax-rate total of all lines.

### taxRate

Required: No
Type: integer
Format: int32
Description: Do not send on invoice/note-level lists. Derived from taxType (S = 5, E/O/Z/AE = 0). Ignored if provided. On lineAllowances, omit or pass the line taxPercentage.

### taxType

Required: Yes
Type: string
Description: PINT AE VAT category for invoice/note-level allowances. Required on invoiceLevelAllowances / noteLevelAllowances. Ignored on lineAllowances (the line taxType applies). Allowed: S, E, O, AE, Z. N (margin scheme) is not allowed (ibr-115-ae). Must match a line taxType on the same document. E requires exemptionCode. Z/AE do not.
Allowed values: S, E, O, AE, Z

### exemptionCode

Required: No
Type: string
Description: The exemption code for zero or exempted tax rate that granted allowance

### allowanceCode

Required: Yes
Type: string
Description: <b>Required</b> Allowance Code based on UNTDID 5189 code list, can be obtained <br>using lookups API
