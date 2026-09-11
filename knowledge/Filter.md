# Filter

## Fields

### fieldName

Required: Yes
Type: string
Description: Represent the field you want to filter against.<br>You can use the following fields to filter outward invoices: dueDate, issueDate, createdOn, and dueAmount.<br>You can use the following fields to filter payments: paymentDate, paymentReference.

### operator

Required: Yes
Type: string
Description: The operator used to filter against field
Allowed values: GREATER_THAN, GREATER_THAN_EQUAL, LESS_THAN, LESS_THAN_EQUAL, EQUALS, LIKE, NOT_EQ, IN, IS_NULL, NOT_NULL

### firstValue

Required: Yes
Type: string
Description: The value you want to filter against, even for numbers should be string format 
