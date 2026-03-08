# USPS Shipping Provider

**Version:** 1.0.0
**Author:** Spwig
**License:** Proprietary

## Overview

The USPS shipping provider integration enables seamless integration with the United States Postal Service API for shipping rate calculation, label generation, and package tracking. This component uses the USPS REST API v3 with OAuth 2.0 authentication.

## Features

### Supported Operations

- ✅ **Rate Calculation** - Get shipping rates for all USPS domestic mail classes
- ✅ **Label Generation** - Create shipping labels in PDF format
- ✅ **Package Tracking** - Track shipments with detailed event history
- ✅ **Return Labels** - Generate return shipping labels
- ✅ **Extra Services** - Insurance and signature confirmation support
- ❌ **International Shipping** - Not supported in v1.0.0 (planned for v1.1.0)
- ❌ **Pickup Scheduling** - Not supported in v1.0.0 (planned for v1.1.0)

### Supported Mail Classes

- **USPS Ground Advantage™** - Ground shipping (replaces First-Class Package Service)
- **Priority Mail®** - 1-3 day delivery
- **Priority Mail Express®** - Overnight delivery
- **Parcel Select®** - Ground delivery for bulk shipments
- **USPS Connect® Local** - Same-day local delivery
- **USPS Connect® Regional** - Regional delivery service
- **Media Mail®** - Books, CDs, DVDs, etc.
- **Library Mail** - Educational materials
- **Bound Printed Matter** - Catalogs, directories, etc.

## Requirements

### System Requirements

- **Python:** >= 3.10
- **Django:** >= 4.2
- **Dependencies:**
  - `requests` >= 2.31.0
  - `python-dateutil` >= 2.8.2

### USPS Account Requirements

1. **USPS Developer Portal Account** (Free)
   - Register at: https://developers.usps.com/
   - Create an application to get API credentials

2. **API Credentials** (Required)
   - Consumer Key (Client ID)
   - Consumer Secret (Client Secret)

3. **Payment Account** (Optional - required for label generation only)
   - Enterprise Payment System (EPS) account, OR
   - Permit account, OR
   - Postage Meter account
   - 10-digit account number

## Installation

This component is distributed via the platform's update server. Install through the admin interface:

1. Navigate to **Shipping > Providers > Browse**
2. Find **USPS** in the available providers list
3. Click **Install**
4. Follow the connection wizard to configure credentials

## Configuration

### Required Credentials

| Field | Description | Required |
|-------|-------------|----------|
| **Consumer Key** | USPS API Consumer Key (Client ID) from developer portal | Yes |
| **Consumer Secret** | USPS API Consumer Secret (Client Secret) | Yes |
| **Payment Account Number** | 10-digit EPS/Permit/Meter account number | No* |
| **Environment** | Test (TEM) or Production | Yes |

*Required for label generation, optional for rates and tracking only.

### Environment Selection

#### Test Environment (TEM)
- **Use for:** Development and testing
- **Base URL:** `https://apis-tem.usps.com`
- **Features:** All API features available with test data
- **No charges:** Test tracking numbers and labels (no real postage)

#### Production Environment
- **Use for:** Live shipments
- **Base URL:** `https://apis.usps.com`
- **Features:** All API features with real data
- **Real charges:** Actual postage costs apply

### Connection Wizard

After installing the component, use the 5-step connection wizard to configure:

1. **Select Provider** - Choose USPS from the list
2. **Setup Instructions** - Review API setup guide
3. **Enter Credentials** - Input Consumer Key, Consumer Secret, and optional Payment Account
4. **Test Connection** - Verify credentials work correctly
5. **Configure Settings** - Set preferences and options

## API Information

### OAuth Authentication

- **Token Endpoint:** `/oauth2/v3/token`
- **Grant Type:** Client Credentials
- **Token Lifetime:** 8 hours (28,800 seconds)
- **Token Caching:** Automatic with 7 hour 55 minute cache (refreshes before expiration)

### API Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| **OAuth Token** | POST | `/oauth2/v3/token` |
| **Rate Calculation** | POST | `/prices/v3/base-rates/search` |
| **Label Generation** | POST | `/labels/v3/label` |
| **Package Tracking** | POST | `/tracking/v3r2/tracking` |

### Rate Limits

USPS API enforces rate limits. The provider includes automatic retry logic with exponential backoff for 429 (Too Many Requests) responses.

## Usage Examples

### Get Shipping Rates

```python
from shipping.models import ShippingProvider

provider = ShippingProvider.objects.get(provider_key='usps')

rates = provider.get_rates(
    origin={
        'street_line1': '123 Main St',
        'city': 'Springfield',
        'state_code': 'IL',
        'postal_code': '62701',
        'country_code': 'US'
    },
    destination={
        'street_line1': '456 Oak Ave',
        'city': 'Chicago',
        'state_code': 'IL',
        'postal_code': '60601',
        'country_code': 'US'
    },
    parcels=[{
        'weight_lb': 2.5,
        'length_in': 12,
        'width_in': 8,
        'height_in': 6
    }]
)

for rate in rates:
    print(f"{rate['service_name']}: ${rate['total_charge']}")
```

### Generate Shipping Label

```python
label_data = provider.buy_label(
    shipment_id='SHIP-12345',
    rate=selected_rate,
    options={
        'label_format': 'PDF',
        'include_receipt': True
    }
)

tracking_number = label_data['tracking_number']
label_url = label_data['label_url']
```

### Track Package

```python
tracking_info = provider.get_tracking('9400100000000000000000')

print(f"Status: {tracking_info['status']}")
print(f"Location: {tracking_info['current_location']}")
print(f"Estimated Delivery: {tracking_info['estimated_delivery']}")

for event in tracking_info['events']:
    print(f"{event['timestamp']}: {event['description']}")
```

## Label Generation

### Payment Authorization

Labels require a payment authorization token (separate from OAuth):

1. Set up a USPS payment account (EPS, Permit, or Meter)
2. Use the Payments API to generate an authorization token
3. Token is valid for 60 days and authorizes label purchases
4. Provider handles token management automatically

### Label Formats

- **PDF** - Standard shipping label format
- **PNG** - Image format for thermal printers
- **ZPL** - Zebra printer format
- **TIFF** - High-resolution image format

### Multipart Response

USPS returns labels in `multipart/form-data` format with:
- **labelMetadata** (JSON) - Tracking number, postage, service info
- **labelImage** (Base64) - Label binary data
- **receiptImage** (Base64) - Postal receipt
- **returnLabelImage** (optional) - Return label if requested

The provider automatically parses multipart responses and extracts all components.

## Tracking

### Tracking Number Format

USPS uses various tracking number formats:
- 20-22 digits (most common)
- Various service-specific formats
- Example: `9400100000000000000000`

### Status Mapping

USPS uses descriptive text statuses (not codes). The provider maps these to standardized platform statuses:

| USPS Status Pattern | Platform Status |
|---------------------|----------------|
| "Delivered" | `delivered` |
| "Out for Delivery" | `out_for_delivery` |
| "In Transit", "Accepted", "Arrived" | `in_transit` |
| "Notice Left", "Alert" | `exception` |
| "Available for Pickup" | `available_for_pickup` |

## Troubleshooting

### Common Issues

#### 401 Unauthorized
- Verify Consumer Key and Consumer Secret are correct
- Check that credentials haven't expired
- Ensure correct environment is selected (Test vs Production)

#### Payment Authorization Required
- Label generation requires a payment account
- Set up EPS, Permit, or Meter account with USPS
- Generate payment authorization token via Payments API
- Enter account number in provider credentials

#### No Rates Returned
- Verify origin and destination ZIP codes are valid
- Check that package dimensions and weight are within USPS limits
- Ensure selected mail class is available for the route
- Some services may not be available in Test environment

#### Tracking Not Found
- Verify tracking number format is correct
- Allow time for tracking to become available after label creation
- Test tracking numbers may not work in production (and vice versa)

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger('shipping.providers.usps').setLevel(logging.DEBUG)
```

## Support Resources

- **USPS Developer Portal:** https://developers.usps.com/
- **API Documentation:** https://developers.usps.com/apis
- **Getting Started:** https://developers.usps.com/getting-started
- **API Support:** https://emailus.usps.com/s/web-tools-inquiry
- **Domestic Mail Manual:** https://pe.usps.com/DMM300
- **Publication 199 (IMpb):** https://postalpro.usps.com/pub199

## Limitations

### Current Version (v1.0.0)

- **Domestic Only:** International shipping not supported
- **No Webhooks:** USPS API doesn't support webhooks; use polling with `get_tracking()`
- **No Label Cancellation:** Labels cannot be voided via API (must use Business Customer Gateway)
- **No Pickup Scheduling:** Carrier pickup scheduling not implemented

### Planned Features (v1.1.0+)

- International shipping and customs forms
- Carrier pickup scheduling integration
- Address validation integration
- Enhanced extra services support
- Bulk rate calculations

## Security

### Credential Storage

- Credentials are encrypted in the database
- Consumer Secret is never logged or displayed
- Payment account number is masked in logs (shows last 4 digits only)

### API Communication

- All API requests use HTTPS
- OAuth tokens cached securely with automatic refresh
- Retry logic respects rate limits to prevent account suspension

## Performance

### Token Caching

- OAuth tokens cached for 7 hours 55 minutes (8-hour lifetime)
- Thread-safe token acquisition with locking
- Automatic refresh before expiration

### Retry Logic

- Exponential backoff for transient failures
- Configurable retry attempts (default: 3)
- Respects Retry-After headers for rate limit errors

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## License

Proprietary - Copyright © 2025 Spwig. All rights reserved.

## Support

For issues, questions, or feature requests, please contact Spwig support.
