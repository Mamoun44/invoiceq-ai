# CustomerInfo

## Fields

### mode

Required: Yes
Type: string
Description: How InvoiceQ should handle customer incase already known to InvoiceQ database, reference will be the used key to determine if customer already saved in InvoiceQ DB or not. USE_SAVED: if the customer exists, reuse saved data; if not found, create from this request. UPDATE_IF_EXISTS: if the customer exists, update it from this request; if not found, create. Default USE_SAVED.
Allowed values: USE_SAVED, UPDATE_IF_EXISTS

### customerCode

Required: Yes
Type: string
Description: Originating system reference and would be used as unique identification for each customer

### englishName

Required: Yes
Type: string
Description: Customer English name.

### arabicName

Required: No
Type: string
Description: Customer Arabic name. Required for domestic UAE buyers (countryIsoCode ARE/AE). Optional for export invoices to a non-UAE buyer.

### entitySchemeId

Required: No
Type: string
Description: Legal registration identifier type for the commercial registration number. Required for domestic UAE buyers (countryIsoCode ARE/AE). One of: TL = Commercial/Trade license, EID = Emirates ID, PAS = Passport, CD = Cabinet Decision. Not required for export invoices to a non-UAE buyer (foreign CompanyID may be sent without a UAE scheme).
Allowed values: TL, EID, PAS, CD

### registrationNumber

Required: No
Type: string
Description: Buyer legal registration / company identifier. For domestic UAE buyers (countryIsoCode ARE/AE): the commercial registration number issued in the UAE (pair with entitySchemeId TL, EID, PAS, or CD). For export invoices to a non-UAE buyer: the foreign company registration id when available (e.g. CompanyID on PartyLegalEntity). Also required for commercial (out-of-scope) invoices.

### entityTaxNumber

Required: No
Type: string
Description: Buyer Tax Registration Number (TRN). Applies to domestic UAE taxable buyers (countryIsoCode ARE/AE). Required when any line uses reverse charge (taxType AE). Not typically used for export invoices to a non-UAE buyer.

### authorityName

Required: No
Type: string
Description: Issuing authority name for the commercial/trade license. Required for domestic UAE buyers when entitySchemeId is TL. Not applicable to typical export buyers.

### beneficiaryId

Required: No
Type: string
Description: Beneficiary identifier for the customer. Required for free trade zone scenarios.

### peppolSchemaId

Required: No
Type: string
Description: Peppol scheme ID for the buyer EndpointID. When provided, customerInfo.peppolParticipantId is required. When InvoiceQ applies a predefined participant ID, it automatically uses scheme ID 0235; callers should omit both Peppol endpoint fields for those fallback scenarios.

### peppolParticipantId

Required: No
Type: string
Description: Peppol participant ID for the buyer EndpointID. When provided, customerInfo.peppolSchemaId is required. When neither Peppol endpoint field is provided, InvoiceQ automatically applies scheme ID 0235 and the applicable predefined participant ID: 9900000097 for deemed supply; 9900000099 when isExportInvoice is true; or 9900000098 for a UAE buyer (countryIsoCode AE/ARE), representing a buyer not subject to UAE e-invoicing regulations. For other non-UAE, non-export, non-deemed-supply customers, this field is required.

### countryIsoCode

Required: Yes
Type: string
Description: Buyer country ISO 3166-1 alpha-3 code. Use ARE (or AE) for domestic UAE buyers. For export invoices use the foreign buyer country (e.g. AUS).

### provinceCode

Required: No
Type: string
Description: Country subentity for the buyer postal address. For domestic UAE buyers (countryIsoCode ARE/AE): required emirate code, one of AUH, DXB, SHJ, UAQ, FUJ, AJM, RAK. For export invoices to a non-UAE buyer: foreign region/state code (e.g. WA).

### city

Required: Yes
Type: string
Description: City of the buyer postal address (e.g. Dubai for domestic, Perth for export).

### area

Required: No
Type: string
Description: District, area, or additional street name of the buyer postal address.

### street

Required: Yes
Type: string
Description: Street name of the buyer postal address.

### bldgNo

Required: No
Type: string
Description: Building number of the buyer postal address when applicable.

### pobox

Required: No
Type: string
Description: Postal code / postal zone of the buyer address.

### additionalNo

Required: No
Type: string
Description: Four digit number.

### deliveryAddress

Required: No
References schema: DeliveryAddressDetails
