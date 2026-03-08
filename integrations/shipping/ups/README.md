# UPS Shipping Provider

**Version**: 1.0.0
**Author**: Spwig
**License**: Proprietary

---

## Overview

Official UPS shipping provider integration for the platform. Provides rate calculation, shipping label generation, and real-time tracking via the UPS REST API with OAuth 2.0 authentication.

## Features

- **Rate Calculation**: Get shipping rates for domestic and international shipments
- **Label Generation**: Create shipping labels in PDF, PNG, or ZPL formats
- **Real-time Tracking**: Track shipments with 1Z tracking numbers
- **International Shipping**: Support for cross-border shipments
- **Insurance**: Optional shipment insurance
- **Signature Confirmation**: Signature-required delivery options
- **OAuth 2.0**: Secure authentication with automatic token refresh

## Requirements

- **Platform Version**: 1.0.0 or higher
- **Python**: 3.10+
- **Django**: 4.2+
- **Dependencies**:
  - requests >= 2.28.0
  - python-dateutil >= 2.8.2

## Getting Started

### 1. UPS Developer Account

1. Visit [UPS Developer Portal](https://developer.ups.com/)
2. Create a free developer account
3. Create a new application
4. Request access to these APIs:
   - Rating API
   - Shipping API
   - Tracking API
   - Address Validation (optional)

### 2. API Credentials

1. Navigate to your application in the UPS Developer Portal
2. Generate OAuth credentials (Client ID and Client Secret)
3. Copy both values - you'll need them during provider setup

### 3. UPS Account Number

- **Required for**: Generating shipping labels
- **Optional for**: Getting shipping rates
- **Format**: 6-character alphanumeric (e.g., A1B2C3)
- **Find it**: On invoices or in your UPS account dashboard

### 4. Installation

This provider is installed via the platform's update system:

1. Navigate to **Admin > Shipping > Providers > Browse**
2. Find "UPS" in the available providers list
3. Click **Install**
4. Follow the connection wizard to configure your credentials

## Configuration

### Credentials

The provider requires the following credentials:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **Client ID** | Text | Yes | Your UPS API Client ID from the developer portal |
| **Client Secret** | Password | Yes | Your UPS API Client Secret (shown once) |
| **Account Number** | Text | No* | Your 6-character UPS account number |
| **Environment** | Select | Yes | `test` or `production` |

*\*Required for label generation, optional for rate quotes*

### Environments

**Test Environment** (Customer Integration Environment - CIE):
- API Base: `https://wwwcie.ups.com`
- Use for development and testing
- No real shipments or charges
- Test tracking number: `1ZISDE016691676846`

**Production Environment**:
- API Base: `https://onlinetools.ups.com`
- Use for live shipments
- Real charges apply
- Requires UPS account approval

## Usage

### Getting Rates

```python
from shipping.services import ShippingService

service = ShippingService()

rates = service.get_rates(
    provider='ups',
    origin={
        'country': 'US',
        'postal_code': '10001',
        'state': 'NY',
        'city': 'New York'
    },
    destination={
        'country': 'US',
        'postal_code': '90001',
        'state': 'CA',
        'city': 'Los Angeles'
    },
    parcels=[{
        'weight': 5000,  # grams
        'length': 30,    # cm
        'width': 20,
        'height': 15,
        'value': 100.00,
        'currency': 'USD'
    }]
)
```

### Generating Labels

```python
label = service.buy_label(
    provider='ups',
    shipment_id='SHIP-12345',
    rate=selected_rate,
    options={
        'origin': origin_address,
        'destination': destination_address,
        'parcels': parcels,
        'label_format': 'PDF'  # PDF, PNG, or ZPL
    }
)

# label contains:
# - tracking_number: 1Z tracking number
# - label_data: Base64-encoded label
# - cost: Shipping cost
# - carrier: 'UPS'
```

### Tracking Shipments

```python
tracking = service.get_tracking(
    provider='ups',
    tracking_number='1Z999AA10123456784'
)

# tracking contains:
# - status: 'in_transit', 'delivered', etc.
# - events: List of tracking events with timestamps
# - estimated_delivery: Estimated delivery date
```

## UPS Service Codes

| Code | Service Name |
|------|--------------|
| 01 | UPS Next Day Air |
| 02 | UPS 2nd Day Air |
| 03 | UPS Ground |
| 07 | UPS Worldwide Express |
| 08 | UPS Worldwide Expedited |
| 11 | UPS Standard |
| 12 | UPS 3 Day Select |
| 13 | UPS Next Day Air Saver |
| 14 | UPS Next Day Air Early A.M. |
| 54 | UPS Worldwide Express Plus |
| 59 | UPS 2nd Day Air A.M. |
| 65 | UPS Saver |

## Tracking Number Format

UPS tracking numbers follow this format:
- Prefix: `1Z`
- Shipper Account: 6 alphanumeric characters
- Service Type: 2 digits
- Package ID: 8 digits
- Check Digit: 1 digit

**Example**: `1Z999AA10123456784`

## Error Handling

The provider includes comprehensive error handling:

- **Authentication Errors**: Invalid credentials
- **Authorization Errors**: Insufficient API access
- **Validation Errors**: Invalid addresses or package details
- **Rate Limit Errors**: Too many requests
- **Service Errors**: UPS API temporarily unavailable

Errors are logged with appropriate severity levels and user-friendly messages.

## Troubleshooting

### Connection Test Fails

**Problem**: "Invalid UPS API credentials"

**Solutions**:
1. Verify Client ID and Client Secret are correct
2. Check that API access has been granted for your application
3. Ensure you're using the correct environment (test vs production)
4. Try regenerating your credentials in the UPS Developer Portal

### Rate Request Fails

**Problem**: "No rates returned" or "Invalid address"

**Solutions**:
1. Verify origin and destination addresses are complete
2. Check that postal codes are valid
3. Ensure package weight and dimensions are within UPS limits
4. For international shipments, verify country codes are ISO 2-letter format

### Label Generation Fails

**Problem**: "Account number required" or "Insufficient account balance"

**Solutions**:
1. Ensure UPS account number is configured (6 characters)
2. Verify account number is correct in your UPS account
3. Check that your UPS account has sufficient balance
4. For test environment, some features may be limited

### Tracking Lookup Fails

**Problem**: "Invalid tracking number" or "No tracking information"

**Solutions**:
1. Verify tracking number format (starts with 1Z)
2. Check that shipment has been picked up by UPS
3. Wait a few hours for tracking information to appear in UPS system
4. Ensure you're checking the correct environment

## API Rate Limits

UPS enforces rate limits on API requests:

- **Rating API**: Up to 100 requests per minute
- **Shipping API**: Up to 50 requests per minute
- **Tracking API**: Up to 100 requests per minute

The provider includes automatic retry logic with exponential backoff for rate-limited requests.

## Support

### Platform Support
- **Documentation**: See platform shipping documentation
- **Issues**: Report via platform issue tracker

### UPS Support
- **Developer Portal**: https://developer.ups.com
- **API Documentation**: https://developer.ups.com/api/reference
- **Developer Support**: developer@ups.com
- **Account Support**: 1-800-742-5877

## Version History

See [CHANGELOG.md](./CHANGELOG.md) for detailed version history.

## License

Proprietary - Copyright © 2025 Spwig. All rights reserved.

---

**Last Updated**: 2025-10-23
**Maintainer**: Spwig Platform Team
