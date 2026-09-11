# OutwardInvoiceList

Outward Invoice Response

## Fields

### invoiceqReference

Required: No
Type: string

### orgKey

Required: Yes
Type: string
Description: Corporate Key

### invoiceNumber

Required: Yes
Type: string
Description: Invoice Number as exists on customer systems , incase duplicate will be rejected

### base64PDF

Required: No
Type: string
Description: Generated Invoice PDF

### encodedXml

Required: No
Type: string
Description: Generated Xml Invoice

### qrCode

Required: No
Type: string
Description: Generated Qr Code

### currencyIsoCode

Required: Yes
Type: string
Allowed values: JOD, USD, SAR, EGP, AED, BHD, QAR, EUR, KWD, OMR, YER, IQD, INR, HKD, GBP, CHF, SEK

### totalNetAmount

Required: Yes
Type: number
Format: double
Description: Total net amount the customer needs to pay, including taxes and after discounts. totalNetAmount = totalInvoiceAmount.

### totalInvoiceAmount

Required: Yes
Type: number
Format: double
Description: Total invoice amount including tax, after discounts.

### totalDiscountAmount

Required: Yes
Type: number
Format: double
Description: Total discount given to customer, if no discount to be passed as zero, it is possible to have discount as zeros in product list while it has value here. In case discount on product level this should be the sum up of all discounts provided in product level

### totalTaxAmount

Required: Yes
Type: number
Format: double
Description: Total tax amount collected from customer, if no tax to be passed as zero, it is possible to have tax as zeros in product list while it has value here. In case discount on product level this should be the sum up of all discounts provided in product level

### issueDate

Required: Yes
Type: string
Format: date-time
Description: zoned datetime format yyyy-mm-ddThh24:mi:ssZ, i.e. 2021-07-01T18:23:00Z

### dueDate

Required: No
Type: string
Format: date-time
Description: zoned datetime format yyyy-mm-ddThh24:mi:ssZ, i.e. 2021-07-01T18:23:00Z

### supplyDate

Required: No
Type: string
Format: date-time
Description: zoned datetime for the suuply date or supply start date incase of supply over period <br>format yyyy-mm-ddThh24:mi:ssZ, i.e. 2021-07-01T18:23:00Z

### supplyEndDate

Required: No
Type: string
Format: date-time
Description: [Conditional] - Required for of supply over periods <br>zoned datetime format yyyy-mm-ddThh24:mi:ssZ, i.e. 2021-07-01T18:23:00Z

### narration

Required: Yes
Type: string
Description: Service details or narrations to be printed in customer invoice

### customerInfo

Required: No
References schema: CustomerInfo

### products

Required: Yes
Type: array
Description: List of products/services
Array items: Product

### integrationStatus

Required: No
Type: string
Description: Third Party Integration Status
