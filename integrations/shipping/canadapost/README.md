# Canada Post Shipping Provider

**Version:** 1.0.0
**Author:** Spwig
**License:** Proprietary

## Overview

The Canada Post shipping provider integration enables seamless integration with Canada Post's XML-based REST API for shipping rate calculation, label generation, and package tracking. This component uses HTTP Basic Authentication and supports both Contract Shipping (commercial customers) and Non-Contract Shipping (Solutions for Small Business).

## Features

### Supported Operations

- ✅ **Rate Calculation** - Get shipping rates for domestic, USA, and international destinations
- ✅ **Label Generation** - Create shipping labels in PDF format
- ✅ **Package Tracking** - Track shipments with detailed event history
- ✅ **Return Labels** - Generate return shipping labels (authorized and open returns)
- ✅ **International Shipping** - Full customs declarations support
- ✅ **Extra Services** - Insurance (COV), signature (SO), COD, and delivery preferences
- ✅ **Manifest System** - Batch shipping support for Contract customers
- ✅ **Dual Customer Types** - Contract and Non-Contract shipping support
- ❌ **Pickup Scheduling** - Not supported in v1.0.0 (planned for future release)

### Supported Service Codes

#### Domestic Services (Canada)

- **DOM.RP** - Regular Parcel (2-9 business days)
- **DOM.EP** - Expedited Parcel (1-7 business days)
- **DOM.XP** - Xpresspost (next-day to 2-day delivery)
- **DOM.PC** - Priority (overnight to most destinations)

#### USA Services

- **USA.EP** - Expedited Parcel USA (4-7 business days)
- **USA.XP** - Xpresspost USA (2-3 business days)

#### International Services

- **INT.XP** - Xpresspost International (4-7 business days to 65+ countries)
- **INT.IP.AIR** - International Parcel Air (6-12 business days)
- **INT.IP.SURF** - International Parcel Surface (4-12 weeks)

## Requirements

### System Requirements

- **Python:** >= 3.8
- **Django:** >= 4.2
- **Dependencies:**
  - `requests` >= 2.31.0

### Canada Post Account Requirements

1. **Developer Portal Account** (Free)
   - Register at: https://www.canadapost-postescanada.ca/information/app/wtz/business/productsServices/developers/default
   - Create API credentials (username and password)

2. **Customer Number** (Required)
   - 10-digit customer number from Canada Post
   - Identifies your business account

3. **Contract ID** (Optional - for Contract customers only)
   - Provided if you have a commercial parcel agreement
   - Enables discounted commercial rates
   - Grants access to manifest system

## Installation

This component is distributed via the platform's update server. Install through the admin interface:

1. Navigate to **Shipping > Providers > Browse**
2. Find **Canada Post** in the available providers list
3. Click **Install**
4. Follow the 8-step setup wizard to configure credentials

## Configuration

### Understanding Customer Types

Canada Post offers two distinct customer types, and the integration automatically detects which type you are based on your credentials:

#### Contract Shipping (Commercial Customers)

**Who it's for:** Businesses with a Canada Post commercial parcel agreement

**Requirements:**
- 10-digit customer number
- Contract ID
- Optional MOBO (Mailed On Behalf Of) number

**Benefits:**
- Discounted commercial rates
- Access to manifest system for batch shipping
- Postage charged to your account
- Full service access

**API Endpoint:** `/rs/{customer_number}/{mobo}/shipment`

**Example Credentials:**
```json
{
  "username": "your_api_username",
  "password": "your_api_password",
  "customer_number": "1234567890",
  "contract_id": "12345678",
  "environment": "production"
}
```

#### Non-Contract Shipping (Solutions for Small Business™)

**Who it's for:** Small businesses without a commercial parcel agreement

**Requirements:**
- 10-digit customer number
- NO contract ID

**Characteristics:**
- Higher retail rates (no commercial discount)
- Credit card payment required per shipment
- No manifest system
- Full service access

**API Endpoint:** `/rs/{customer_number}/ncshipment`

**Example Credentials:**
```json
{
  "username": "your_api_username",
  "password": "your_api_password",
  "customer_number": "1234567890",
  "contract_id": "",
  "environment": "production"
}
```

### Required Credentials

| Field | Description | Required | Format |
|-------|-------------|----------|--------|
| **API Username** | API username from Developer Portal | Yes | String (min 8 chars) |
| **API Password** | API password from Developer Portal | Yes | String (min 8 chars) |
| **Customer Number** | 10-digit Canada Post customer number | Yes | 10 digits |
| **Contract ID** | Contract ID (Contract customers only) | No | String |
| **MOBO** | Mailed On Behalf Of number | No | 10 digits (defaults to customer number) |
| **Environment** | API environment | Yes | `development` or `production` |

### Environment Selection

#### Development Environment (Testing)

- **Use for:** Development and testing
- **Base URL:** `https://ct.soa-gw.canadapost.ca`
- **Features:** Full API access with test data
- **No charges:** Test shipments and labels

#### Production Environment (Live)

- **Use for:** Live shipments
- **Base URL:** `https://soa-gw.canadapost.ca`
- **Features:** Full API access with real data
- **Real charges:** Actual postage costs apply

### Setup Wizard

After installing the component, use the 8-step setup wizard:

1. **Understanding Customer Types** - Learn about Contract vs Non-Contract
2. **Determine Your Customer Type** - Select which type applies to you
3. **Register at Developer Portal** - Create developer account
4. **Generate API Credentials** - Get username and password
5. **Enter Credentials** - Input all required information
6. **Test Connection** - Verify credentials work
7. **Configure Services** - Select available shipping services
8. **Configure Options** - Enable shipping options (signature, insurance, etc.)

## API Information

### Authentication

- **Method:** HTTP Basic Authentication
- **Format:** Base64-encoded `username:password`
- **Header:** `Authorization: Basic {credentials}`
- **No tokens required** - Credentials sent with each request

### API Format

- **Request Format:** XML
- **Response Format:** XML
- **Content-Type:** `application/vnd.cpc.*+xml` (varies by endpoint)
- **Character Encoding:** UTF-8

### API Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| **Rate Calculation** | POST | `/rs/ship/price` |
| **Contract Shipment** | POST | `/rs/{customer}/{mobo}/shipment` |
| **Non-Contract Shipment** | POST | `/rs/{customer}/ncshipment` |
| **Tracking** | GET | `/vis/track/pin/{tracking}/summary` |
| **Void Shipment** | DELETE | `/rs/{customer}/{mobo}/shipment/{id}` |
| **Label Artifact** | GET | `/rs/artifact/{id}/{token}` |

### XML Namespaces

Canada Post uses specific XML namespaces for each API version:

```xml
<!-- Rate Request (v4) -->
<mailing-scenario xmlns="http://www.canadapost.ca/ws/ship/rate-v4">
  ...
</mailing-scenario>

<!-- Shipment Request (v8 Contract) -->
<shipment xmlns="http://www.canadapost.ca/ws/shipment-v8">
  ...
</shipment>

<!-- Non-Contract Shipment (v4) -->
<non-contract-shipment xmlns="http://www.canadapost.ca/ws/ncshipment-v4">
  ...
</non-contract-shipment>

<!-- Tracking (v2) -->
<tracking-detail xmlns="http://www.canadapost.ca/ws/track">
  ...
</tracking-detail>
```

### Rate Limits

Canada Post does not publicly document rate limits, but the integration includes:
- Exponential backoff retry logic
- Automatic retry on transient failures (503, 504)
- Configurable retry attempts (default: 3)
- Request timeout: 30 seconds (60 seconds for shipment creation)

## Usage Examples

### Get Shipping Rates

```python
from shipping.models import ShippingProvider

provider = ShippingProvider.objects.get(provider_key='canadapost')

rates = provider.get_rates(
    origin={
        'street': '1234 Main St',
        'city': 'Ottawa',
        'state': 'ON',
        'postal_code': 'K1A0B1',
        'country': 'CA'
    },
    destination={
        'street': '5678 Bay St',
        'city': 'Toronto',
        'state': 'ON',
        'postal_code': 'M5H2N2',
        'country': 'CA'
    },
    parcels=[{
        'weight_lb': 2.5,
        'length_in': 12,
        'width_in': 8,
        'height_in': 6
    }]
)

for rate in rates:
    print(f"{rate['service_name']}: ${rate['total_charge']} CAD")
    print(f"  Service Code: {rate['service_code']}")
    print(f"  Delivery: {rate['delivery_date']}")
```

**Example Output:**
```
Regular Parcel: $12.50 CAD
  Service Code: DOM.RP
  Delivery: 2025-10-30
Expedited Parcel: $18.75 CAD
  Service Code: DOM.EP
  Delivery: 2025-10-28
Xpresspost: $25.00 CAD
  Service Code: DOM.XP
  Delivery: 2025-10-27
```

### Generate Shipping Label

```python
# Select a rate
selected_rate = rates[0]  # Choose Regular Parcel

# Purchase label
label_data = provider.buy_label(
    shipment_id='SHIP-12345',
    rate=selected_rate,
    options={
        'origin': {
            'street': '1234 Main St',
            'city': 'Ottawa',
            'state': 'ON',
            'postal_code': 'K1A0B1',
            'country': 'CA'
        },
        'destination': {
            'street': '5678 Bay St',
            'city': 'Toronto',
            'state': 'ON',
            'postal_code': 'M5H2N2',
            'country': 'CA'
        },
        'parcels': [{
            'weight_lb': 2.5,
            'length_in': 12,
            'width_in': 8,
            'height_in': 6
        }],
        'sender_name': 'ACME Corp',
        'sender_company': 'ACME Corporation',
        'sender_phone': '613-555-1234',
        'recipient_name': 'John Doe',
        'recipient_phone': '416-555-5678',
        'options': [
            {'code': 'SO'},  # Signature required
            {'code': 'COV', 'amount': '500.00'}  # $500 insurance
        ]
    }
)

tracking_number = label_data['tracking_number']
label_url = label_data['label_url']  # Base64-encoded PDF

print(f"Label created: {tracking_number}")
print(f"Cost: ${label_data['cost']} {label_data['currency']}")
```

### Track Package

```python
tracking_info = provider.get_tracking('1234567890123456')

print(f"Status: {tracking_info['status']}")
print(f"Service: {tracking_info['service_name']}")
print(f"Destination: {tracking_info['destination_postal_code']}")
print(f"Expected Delivery: {tracking_info['expected_delivery_date']}")

print("\nTracking Events:")
for event in tracking_info['events']:
    print(f"  {event['timestamp']} - {event['description']}")
    print(f"    Location: {event['location']}")
```

**Example Output:**
```
Status: in_transit
Service: Regular Parcel
Destination: M5H2N2
Expected Delivery: 2025-10-30

Tracking Events:
  2025-10-25 14:30:00 - Item accepted at Post Office
    Location: Ottawa, ON
  2025-10-26 08:15:00 - Item in transit
    Location: Mississauga, ON
  2025-10-27 05:45:00 - Item processed
    Location: Toronto, ON
```

### International Shipment with Customs

```python
# Get rates for international shipment
rates = provider.get_rates(
    origin={
        'postal_code': 'K1A0B1',
        'country': 'CA'
    },
    destination={
        'postal_code': '10001',
        'country': 'US'
    },
    parcels=[{
        'weight_lb': 3.0,
        'length_in': 10,
        'width_in': 8,
        'height_in': 6
    }]
)

# Purchase label with customs declaration
label_data = provider.buy_label(
    shipment_id='SHIP-12346',
    rate=rates[0],
    options={
        'origin': {...},
        'destination': {...},
        'parcels': [{...}],
        'sender_name': 'ACME Corp',
        'sender_phone': '613-555-1234',
        'recipient_name': 'Jane Smith',
        'recipient_phone': '212-555-9876',
        'customs': {
            'currency': 'CAD',
            'reason_for_export': 'SALE',
            'other_reason': '',
            'invoice_number': 'INV-12346',
            'items': [
                {
                    'description': 'T-Shirt',
                    'hs_code': '6109.10.00',
                    'quantity': 2,
                    'unit_value': 25.00,
                    'weight_kg': 0.5,
                    'country_of_origin': 'CA'
                },
                {
                    'description': 'Coffee Mug',
                    'hs_code': '6912.00.00',
                    'quantity': 1,
                    'unit_value': 15.00,
                    'weight_kg': 0.8,
                    'country_of_origin': 'CA'
                }
            ]
        }
    }
)
```

## XML Request/Response Examples

### Rate Request XML

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mailing-scenario xmlns="http://www.canadapost.ca/ws/ship/rate-v4">
  <customer-number>1234567890</customer-number>
  <contract-id>12345678</contract-id>
  <parcel-characteristics>
    <weight>1.0</weight>
    <dimensions>
      <length>25.0</length>
      <width>20.0</width>
      <height>15.0</height>
    </dimensions>
  </parcel-characteristics>
  <origin-postal-code>K1A0B1</origin-postal-code>
  <destination>
    <domestic>
      <postal-code>M5H2N2</postal-code>
    </domestic>
  </destination>
</mailing-scenario>
```

### Rate Response XML

```xml
<?xml version="1.0" encoding="UTF-8"?>
<price-quotes xmlns="http://www.canadapost.ca/ws/ship/rate-v4">
  <price-quote>
    <service-code>DOM.RP</service-code>
    <service-link rel="service" href=".../service/DOM.RP" media-type="..."/>
    <service-name>Regular Parcel</service-name>
    <price-details>
      <base>10.00</base>
      <taxes>
        <gst>0.50</gst>
        <pst>0.00</pst>
        <hst>0.00</hst>
      </taxes>
      <due>10.50</due>
    </price-details>
    <weight-details>
      <cubed-weight>1.2</cubed-weight>
    </weight-details>
    <service-standard>
      <am-delivery>false</am-delivery>
      <guaranteed-delivery>false</guaranteed-delivery>
      <expected-transit-time>5</expected-transit-time>
      <expected-delivery-date>2025-10-30</expected-delivery-date>
    </service-standard>
  </price-quote>
  <!-- More price quotes... -->
</price-quotes>
```

### Shipment Request XML (Contract)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<shipment xmlns="http://www.canadapost.ca/ws/shipment-v8">
  <group-id>GROUP-001</group-id>
  <requested-shipping-point>K1A0B1</requested-shipping-point>
  <delivery-spec>
    <service-code>DOM.EP</service-code>
    <sender>
      <name>ACME Corp</name>
      <company>ACME Corporation</company>
      <contact-phone>613-555-1234</contact-phone>
      <address-details>
        <address-line-1>1234 Main St</address-line-1>
        <city>Ottawa</city>
        <prov-state>ON</prov-state>
        <postal-zip-code>K1A0B1</postal-zip-code>
      </address-details>
    </sender>
    <destination>
      <name>John Doe</name>
      <address-details>
        <address-line-1>5678 Bay St</address-line-1>
        <city>Toronto</city>
        <prov-state>ON</prov-state>
        <postal-zip-code>M5H2N2</postal-zip-code>
      </address-details>
    </destination>
    <options>
      <option>
        <option-code>SO</option-code>
      </option>
      <option>
        <option-code>COV</option-code>
        <option-amount>500.00</option-amount>
      </option>
    </options>
    <parcel-characteristics>
      <weight>2.5</weight>
      <dimensions>
        <length>30.0</length>
        <width>20.0</width>
        <height>15.0</height>
      </dimensions>
    </parcel-characteristics>
  </delivery-spec>
</shipment>
```

### Shipment Response XML

```xml
<?xml version="1.0" encoding="UTF-8"?>
<shipment-info xmlns="http://www.canadapost.ca/ws/shipment-v8">
  <shipment-id>545021584937284062</shipment-id>
  <shipment-status>created</shipment-status>
  <tracking-pin>1234567890123456</tracking-pin>
  <links>
    <link rel="label" href=".../artifact/12345/0" media-type="application/pdf"/>
    <link rel="receipt" href=".../artifact/12345/1" media-type="application/pdf"/>
  </links>
</shipment-info>
```

## Shipping Options

Canada Post provides various shipping options that can be added to shipments:

| Option Code | Option Name | Description | Value Required | Example |
|-------------|-------------|-------------|----------------|---------|
| **SO** | Signature | Signature required on delivery | No | `{'code': 'SO'}` |
| **COV** | Coverage (Insurance) | Insurance coverage up to $5,000 | Yes (amount in CAD) | `{'code': 'COV', 'amount': '500.00'}` |
| **COD** | Collect on Delivery | Collect payment on delivery | Yes (amount to collect) | `{'code': 'COD', 'amount': '250.00'}` |
| **D2PO** | Deliver to Post Office | Hold at post office for pickup | No | `{'code': 'D2PO'}` |
| **HFP** | Card for Pickup | Leave notice card for pickup | No | `{'code': 'HFP'}` |
| **DNS** | Do Not Safe Drop | Requires signature or card | No | `{'code': 'DNS'}` |
| **LAD** | Leave at Door | Allow safe drop delivery | No | `{'code': 'LAD'}` |
| **PA18** | Proof of Age 18 | Verify recipient is 18+ | No | `{'code': 'PA18'}` |
| **PA19** | Proof of Age 19 | Verify recipient is 19+ | No | `{'code': 'PA19'}` |
| **RASE** | Return at Sender's Expense | Return to sender if undeliverable | No | `{'code': 'RASE'}` |

**Note:** Not all options are available for all service types. Canada Post will return an error if you request incompatible option combinations.

## Manifest System (Contract Customers Only)

Contract customers can use the manifest system to batch process multiple shipments:

### Benefits
- Consolidates multiple shipments into a single manifest
- Required for account billing
- Provides proof of shipment submission
- Simplifies end-of-day processing

### Workflow

1. **Create shipments** with `group-id` (instead of `transmit`)
2. **Add multiple shipments** to the same group
3. **Transmit manifest** when ready to ship all packages
4. **Receive manifest artifact** (PDF document)

```python
# This functionality is built into the provider but requires
# additional implementation in the shipping management interface
```

## International Shipping

### Customs Declarations

All international shipments require customs declarations:

#### Required Fields

- **currency** - Currency code (e.g., 'CAD', 'USD')
- **reason_for_export** - One of: 'DOC' (documents), 'SAM' (sample), 'REP' (repair), 'SOG' (sale of goods), 'OTH' (other)
- **other_reason** - Required if reason is 'OTH'
- **invoice_number** - Optional invoice reference

#### Customs Items

Each item requires:

- **description** - Item description (max 45 chars)
- **hs_code** - Harmonized System tariff code (6-10 digits)
- **quantity** - Number of items
- **unit_value** - Value per item
- **weight_kg** - Weight per item in kilograms
- **country_of_origin** - ISO country code (e.g., 'CA', 'US', 'CN')

### HS Codes

Harmonized System (HS) codes classify goods for customs:

- **Format:** 6-10 digits (6-digit minimum required)
- **Examples:**
  - `6109.10.00` - T-shirts, cotton
  - `6204.62.40` - Women's trousers
  - `6912.00.00` - Ceramic tableware
  - `8471.30.01` - Portable computers

**Resources:**
- Canadian Tariff Finder: https://www.cbsa-asfc.gc.ca/trade-commerce/tariff-tarif/menu-eng.html
- World Customs Organization: http://www.wcoomd.org/

## Error Handling

### Exception Hierarchy

```python
CanadaPostError (base exception)
├── CanadaPostAuthenticationError     # 401 Unauthorized
├── CanadaPostValidationError         # 400 Bad Request / validation issues
├── CanadaPostShipmentError           # Shipment creation failures
├── CanadaPostTrackingError           # Tracking lookup failures
├── CanadaPostServiceUnavailableError # 503 Service Unavailable
└── CanadaPostAPIError                # Generic API errors
```

### Common Errors

#### Authentication Errors

**Error:** `401 Unauthorized`
**Cause:** Invalid API username or password
**Solution:** Verify credentials in Developer Portal, ensure no extra spaces

#### Validation Errors

**Error:** `Invalid postal code format`
**Cause:** Postal code doesn't match expected format
**Solution:** Canadian postal codes must be in format `A1A1A1` (with or without space)

**Error:** `Customer number must be 10 digits`
**Cause:** Customer number is invalid
**Solution:** Verify your 10-digit customer number with Canada Post

#### Shipment Errors

**Error:** `Service not available for destination`
**Cause:** Selected service doesn't serve the destination
**Solution:** Use Get Rates to see available services for the route

**Error:** `Invalid option combination`
**Cause:** Incompatible options selected
**Solution:** Review service-specific option restrictions

#### Tracking Errors

**Error:** `Tracking number not found`
**Cause:** Invalid tracking number or not yet in system
**Solution:** Verify tracking number format, wait 30-60 minutes after label creation

### Retry Logic

The provider includes automatic retry logic for transient failures:

- **Retryable Status Codes:** 500, 502, 503, 504, 429
- **Max Attempts:** 3 (configurable)
- **Backoff Strategy:** Exponential (1s, 2s, 4s)
- **Timeout:** 30 seconds (60 seconds for shipments)

## Troubleshooting

### Connection Test Fails

**Issue:** Test connection returns authentication error

**Checklist:**
1. Verify API username and password are correct
2. Check for extra spaces in credentials
3. Ensure customer number is exactly 10 digits
4. Verify environment selection (Development vs Production)
5. Confirm Developer Portal account is active

### No Rates Returned

**Issue:** Get Rates returns empty list

**Checklist:**
1. Verify both origin and destination postal codes are valid
2. Check package weight and dimensions are reasonable
3. Ensure service is available for the route
4. For USA/International, verify customs requirements
5. Check if customer type supports requested service

### Label Creation Fails

**Issue:** Buy Label returns error

**Checklist:**
1. Verify all required address fields are provided
2. For international, ensure customs declaration is complete
3. Check that origin postal code matches your shipping location
4. Verify selected service code is valid
5. Ensure options are compatible with service
6. For Non-Contract customers, verify payment method is configured

### Tracking Not Working

**Issue:** Get Tracking returns "not found"

**Checklist:**
1. Wait 30-60 minutes after label creation
2. Verify tracking number is correct (no extra characters)
3. Ensure tracking number format is valid
4. Check that shipment was actually created (not just a rate quote)
5. For test environment, use test tracking numbers

### XML Parse Errors

**Issue:** "Failed to parse XML response"

**Checklist:**
1. Enable debug logging to see raw XML
2. Check for special characters in addresses
3. Verify XML encoding is UTF-8
4. Ensure request follows Canada Post XML schema
5. Check API version compatibility

### Debug Logging

Enable detailed logging to troubleshoot issues:

```python
import logging

# Enable debug logging for Canada Post provider
logging.getLogger('shipping.providers.canadapost').setLevel(logging.DEBUG)

# This will log:
# - Full XML requests (truncated for security)
# - Full XML responses (truncated)
# - API call timing and status codes
# - Authentication details (credentials redacted)
```

## Support Resources

### Official Documentation

- **Developer Portal:** https://www.canadapost-postescanada.ca/information/app/wtz/business/productsServices/developers/default
- **API Documentation:** https://www.canadapost-postescanada.ca/cpc/doc/en/business/developers/apis/docs/index.htm
- **Developer Guide:** https://www.canadapost-postescanada.ca/information/app/drc/home

### Tools and Utilities

- **Track a Package:** https://www.canadapost-postescanada.ca/track-reperage/en#/home
- **Rate Calculator:** https://www.canadapost-postescanada.ca/information/app/far/business/findARate?execution=e1s1
- **Postal Code Lookup:** https://www.canadapost-postescanada.ca/information/app/fpo/personal/findbyaddress
- **Tariff Finder:** https://www.cbsa-asfc.gc.ca/trade-commerce/tariff-tarif/menu-eng.html

### Customer Support

- **Developer Support Email:** developer@canadapost.ca
- **Business Customer Service:** 1-866-607-6301
- **Solutions for Small Business:** https://www.canadapost-postescanada.ca/information/app/wtz/business/smallBusiness?LOCALE=en

### API Reference

- **Rate Calculator API:** `/rs/ship/price` (v4)
- **Shipping API:** `/rs/{customer}/{mobo}/shipment` (v8)
- **Non-Contract Shipping API:** `/rs/{customer}/ncshipment` (v4)
- **Tracking API:** `/vis/track/pin/{tracking}/summary` (v2)

## Limitations

### Current Version (v1.0.0)

- **No Pickup Scheduling:** Carrier pickup scheduling not implemented
- **No Label Cancellation via Tracking:** Void requires shipment ID, not tracking number
- **No Webhooks:** Canada Post doesn't support webhooks for tracking updates
- **XML Only:** API uses XML format, not JSON
- **Single Parcel:** Multi-parcel shipments not supported (use first parcel only)

### Service Limitations

- **Weight Limit:** Varies by service (typically 30 kg domestic, 30 kg USA)
- **Dimension Limit:** Length + girth must not exceed 3 meters
- **Insurance Limit:** Maximum $5,000 CAD coverage
- **COD Limit:** Maximum $1,000 CAD

## Security

### Credential Storage

- Credentials encrypted in database using Django's encryption
- API password never logged or displayed in plain text
- Customer number masked in logs (shows last 4 digits only)
- Credentials redacted in error messages

### API Communication

- All requests use HTTPS
- HTTP Basic Authentication on every request
- No token caching required (stateless authentication)
- Timeout protection against slow/hanging requests

### Best Practices

1. **Rotate credentials regularly** - Generate new API credentials periodically
2. **Use environment variables** - Don't hardcode credentials
3. **Monitor failed auth attempts** - Set up alerts for 401 errors
4. **Restrict API access** - Use separate credentials per integration
5. **Audit shipment activity** - Log all label purchases and voids

## Performance

### Request Timing

Typical response times (may vary):
- **Get Rates:** 500-1500ms
- **Create Shipment:** 1000-2000ms
- **Get Tracking:** 300-800ms
- **Download Label:** 500-1500ms

### Optimization Tips

1. **Cache rates** - Cache rate quotes for same route/weight combinations
2. **Batch operations** - Use manifest system for multiple shipments
3. **Async tracking** - Don't block UI waiting for tracking updates
4. **Retry strategically** - Use exponential backoff for transient failures
5. **Connection pooling** - Reuse HTTP connections when possible

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

## License

AGPL-3.0

This component is licensed software. Redistribution and use in source and binary forms, with or without modification, are not permitted without express written permission.

## Support

For issues, questions, or feature requests:

- **Platform Support:** Contact Spwig support team
- **Bug Reports:** Submit through admin interface
- **Feature Requests:** Submit via support portal

---

**Version:** 1.0.0
**Last Updated:** 2025-10-23
**Maintained by:** Spwig Development Team
