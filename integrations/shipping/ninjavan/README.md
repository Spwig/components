# NinjaVan Shipping Provider

**Version**: 1.0.0
**Author**: Spwig
**License**: Proprietary

---

## Overview

Official NinjaVan shipping provider integration for Southeast Asian logistics. This provider uses OAuth 2.0 authentication with NinjaVan's Plugin APIs to create delivery orders, generate shipping labels, and receive real-time tracking updates via webhooks.

**Key Differences from Traditional Integrations:**
- Uses OAuth 2.0 authorization code flow (not API keys)
- No rate calculation capability (merchants use their existing NinjaVan account pricing)
- Requires integration audit for production access
- Each merchant hosts their own OAuth redirect and webhook endpoints

---

## Features

- **Order Creation**: Create delivery orders with multiple service types (Standard, Return, Marketplace, Corporate, International)
- **Label Generation**: Generate PDF waybills for shipments
- **Order Cancellation**: Cancel orders in "Pending Pickup" status
- **Real-time Tracking**: Webhook-based tracking updates (8 event types)
- **Multi-country Support**: Singapore, Malaysia, Thailand, Indonesia, Vietnam, Philippines, Myanmar
- **Advanced Features**: COD, pickup scheduling, time slots, temperature control, Ninja Points (PUDO)
- **OAuth 2.0**: Secure authentication with automatic token refresh
- **Webhook Security**: HMAC-SHA256 signature verification

---

## Supported Countries

| Country | Code | NinjaVan Coverage |
|---------|------|-------------------|
| Singapore | SG | Full coverage |
| Malaysia | MY | Full coverage |
| Thailand | TH | Full coverage |
| Indonesia | ID | Full coverage |
| Vietnam | VN | Full coverage |
| Philippines | PH | Full coverage |
| Myanmar | MM | Full coverage |

**Note**: Sandbox environment always uses `/sg` endpoint regardless of selected country.

---

## Prerequisites

### 1. NinjaVan Account

- **Required Account Type**: NinjaVan Postpaid Pro
- **Other Account Types**: Not supported by Plugin APIs
- **Sign Up**: Contact NinjaVan sales team in your country

### 2. OAuth Credentials

1. Log into NinjaVan Dashboard (sandbox or production)
2. Navigate to **Settings > IT Settings**
3. Click **REGENERATE CLIENT ID & KEY**
4. Copy Client ID and Client Secret (shown only once)

### 3. Redirect URI Registration

Before OAuth will work, you must email `devsupport@ninjavan.co` with:
- **Plugin Name**: "Spwig Shop Platform"
- **Country of Integration**: Your country (e.g., Singapore)
- **Redirect URI**: `https://{your-domain}/shipping/ninjavan/oauth/callback/`
- **Required Scopes**: See [OAuth Scopes](#oauth-scopes) below

NinjaVan will respond within 1-2 business days with confirmation.

### 4. HTTPS Requirement

Your shop domain must use HTTPS for:
- OAuth redirect URI
- Webhook endpoint

---

## Installation

This provider is installed via the platform's component update system:

1. Navigate to **Admin > Shipping > Providers > Browse**
2. Find "NinjaVan" in the available providers list
3. Click **Install**
4. Follow the 9-step OAuth setup wizard

---

## Configuration

### Required Credentials

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **Client ID** | Text | Yes | OAuth Client ID from NinjaVan Dashboard |
| **Client Secret** | Password | Yes | OAuth Client Secret (shown once during generation) |
| **Country Code** | Select | Yes | Country where your NinjaVan account is registered |
| **Environment** | Select | Yes | `sandbox` or `production` |

### OAuth Tokens (Auto-managed)

The following tokens are automatically managed by the provider:
- `oauth_access_token` - For API requests (auto-refreshed)
- `oauth_refresh_token` - For obtaining new access tokens
- `oauth_expires_at` - Token expiration timestamp

Tokens are automatically refreshed 5 minutes before expiry or on 401 errors.

### Environments

**Sandbox** (Testing):
- Dashboard: `https://dashboard-sandbox.ninjavan.co`
- API Base: `https://api-sandbox.ninjavan.co/sg` (always /sg)
- Use for development and testing
- Only "Pending Pickup" and "Cancelled" webhooks testable

**Production** (Live):
- Dashboard: `https://dashboard.ninjavan.co`
- API Base: `https://api.ninjavan.co/{countryCode}`
- Requires passing integration audit
- Real shipments and charges apply

---

## OAuth Setup Process

### Step 1: Generate Credentials

1. Log into NinjaVan Dashboard
2. Go to **Settings > IT Settings**
3. Click **REGENERATE CLIENT ID & KEY**
4. Save Client ID and Client Secret securely

### Step 2: Register Redirect URI

Email `devsupport@ninjavan.co`:

```
Subject: Plugin API Integration - OAuth Redirect URI Registration

Hello NinjaVan Team,

I would like to register my OAuth redirect URI for Plugin API integration.

Plugin Name: Spwig Shop Platform
Country of Integration: Singapore
Environment: Sandbox
Redirect URI: https://myshop.example.com/shipping/ninjavan/oauth/callback/

Required Scopes:
- SHIPPER_PUBLIC_APIS_CREATE_ORDER
- SHIPPER_PUBLIC_APIS_CANCEL_ORDER
- SHIPPER_PUBLIC_APIS_GET_AWB
- SHIPPER_PUBLIC_APIS_GET_SHIPPER_SETTINGS
- SHIPPER_PUBLIC_APIS_GET_SUBSCRIPTIONS
- SHIPPER_PUBLIC_APIS_CREATE_SUBSCRIPTIONS
- SHIPPER_PUBLIC_APIS_DELETE_SUBSCRIPTIONS

Thank you!
```

### Step 3: Complete OAuth Authorization

1. Enter credentials in provider configuration
2. Click **Connect to NinjaVan**
3. Log into NinjaVan Dashboard
4. Review permissions and click **Authorize**
5. You'll be redirected back with tokens automatically exchanged

### Step 4: Webhooks Auto-configured

The provider automatically subscribes to all tracking events:
- Webhook URL: `https://{your-domain}/shipping/ninjavan/webhooks/`
- Signature verification: HMAC-SHA256
- 8 event types subscribed

---

## OAuth Scopes

The following scopes are required for full functionality:

| Scope | Purpose |
|-------|---------|
| `SHIPPER_PUBLIC_APIS_CREATE_ORDER` | Create delivery orders |
| `SHIPPER_PUBLIC_APIS_CANCEL_ORDER` | Cancel orders (Pending Pickup only) |
| `SHIPPER_PUBLIC_APIS_GET_AWB` | Generate waybill/label PDFs |
| `SHIPPER_PUBLIC_APIS_GET_SHIPPER_SETTINGS` | Fetch merchant service settings |
| `SHIPPER_PUBLIC_APIS_GET_SUBSCRIPTIONS` | List active webhook subscriptions |
| `SHIPPER_PUBLIC_APIS_CREATE_SUBSCRIPTIONS` | Subscribe to webhook events |
| `SHIPPER_PUBLIC_APIS_DELETE_SUBSCRIPTIONS` | Remove webhook subscriptions |

---

## Integration Audit Requirements

**Production access requires passing NinjaVan's integration audit.**

### Audit Process

1. **Create Test Orders**: Generate at least 3 test orders via your integrated UI (not Postman)
2. **Order Requirements**:
   - Accurate addresses with valid postal codes
   - Valid phone numbers and email addresses
   - Proper package dimensions and weight
3. **Submit Orders**: Use audit link provided by NinjaVan
4. **QA Review**: Wait 3-5 business days for NinjaVan QA team review

### Audit Focus Areas

NinjaVan evaluates:
- **Authentication**: OAuth login flow, token handling, disconnection cleanup
- **Webhook APIs**: Subscription timing and event processing
- **Error Handling**: Success (200) and failure (400, 401, 5xx) responses
- **Token Refresh**: Automatic refresh 5 minutes before expiry or on 401

### After Approval

1. Regenerate tokens for production in NinjaVan Dashboard
2. Reconfigure provider with production credentials
3. Re-email `devsupport@ninjavan.co` with production redirect URI
4. Complete OAuth flow again for production

---

## Usage

### Initialize Provider

```python
from shipping.providers.ninjavan import NinjaVanProvider

credentials = {
    'client_id': 'your_client_id_here',
    'client_secret': 'your_client_secret_here',
    'country_code': 'sg',
    'environment': 'sandbox',
    # OAuth tokens managed automatically
    'oauth_access_token': 'token...',
    'oauth_refresh_token': 'refresh...',
    'oauth_expires_at': 1234567890
}

provider = NinjaVanProvider(credentials)
```

### Test Connection

```python
result = provider.test_connection()

if result['success']:
    print(f"✓ {result['message']}")
    print(f"Environment: {result['details']['environment']}")
    print(f"Service Types: {result['details']['service_types']}")
else:
    print(f"✗ Connection failed: {result['message']}")
```

**Expected Response:**

```python
{
    'success': True,
    'message': 'Successfully connected to NinjaVan',
    'details': {
        'environment': 'sandbox',
        'country_code': 'SG',
        'service_types': ['Standard', 'Return', 'Marketplace'],
        'tracking_prefix': 'NVSGMA',
        'shipper_id': 123456
    }
}
```

### Create Order & Generate Label

```python
shipment_data = {
    'service_type': 'Parcel',
    'service_level': 'Standard',
    'origin': {
        'name': 'My Store',
        'company': 'My Company Pte Ltd',
        'address1': '1 Orchard Road',
        'address2': '#01-01',
        'city': 'Singapore',
        'state': 'Singapore',
        'postal_code': '238824',
        'country': 'SG',
        'phone': '+6512345678',
        'email': 'store@example.com'
    },
    'destination': {
        'name': 'John Doe',
        'address1': '10 Anson Road',
        'address2': '#05-10',
        'city': 'Singapore',
        'state': 'Singapore',
        'postal_code': '079903',
        'country': 'SG',
        'phone': '+6587654321',
        'email': 'john@example.com'
    },
    'parcels': [{
        'weight': 2500,      # grams
        'length': 30,        # cm
        'width': 20,
        'height': 15,
        'value': 150.00,
        'currency': 'SGD',
        'description': 'Electronics'
    }],
    'reference': 'ORDER-12345',
    'cod_amount': 0,  # Cash on delivery (optional)
    'instructions': 'Handle with care'
}

label = provider.buy_label(shipment_data)
```

**Expected Response:**

```python
{
    'tracking_number': 'NVSGMA123456789',
    'label_data': 'JVBERi0xLjQKJeLjz9MKMSAwIG9iago8P...',  # Base64 PDF
    'label_format': 'PDF',
    'cost': {
        'amount': 8.50,
        'currency': 'SGD'
    },
    'carrier': 'NinjaVan',
    'service_name': 'Standard'
}
```

### Cancel Order

```python
result = provider.void_label('NVSGMA123456789')

if result['success']:
    print(f"Order cancelled: {result['tracking_number']}")
else:
    print(f"Cancellation failed: {result['message']}")
```

**Note**: Only orders in "Pending Pickup" status can be cancelled.

### Get Tracking Information

```python
tracking = provider.get_tracking('NVSGMA123456789')

print(f"Status: {tracking['status']}")
print(f"Current Location: {tracking['current_location']}")
print(f"Estimated Delivery: {tracking['estimated_delivery']}")

for event in tracking['events']:
    print(f"{event['timestamp']}: {event['status']} - {event['description']}")
```

**Expected Response:**

```python
{
    'tracking_number': 'NVSGMA123456789',
    'status': 'in_transit',
    'status_detail': 'Package is on the way',
    'carrier': 'NinjaVan',
    'current_location': 'Singapore Central Sorting Facility',
    'estimated_delivery': '2025-10-25',
    'events': [
        {
            'timestamp': '2025-10-23T14:30:00Z',
            'status': 'Pending Pickup',
            'description': 'Order created and ready for pickup',
            'location': 'Shipper Location'
        },
        {
            'timestamp': '2025-10-23T16:45:00Z',
            'status': 'In Transit',
            'description': 'Package picked up by NinjaVan',
            'location': 'Singapore Central Hub'
        }
    ]
}
```

---

## Webhook Configuration

Webhooks are automatically configured when you connect your NinjaVan account.

### Webhook Endpoint

Your webhook endpoint: `https://{your-domain}/shipping/ninjavan/webhooks/`

### Supported Events

| Event | Status Mapping | Description |
|-------|----------------|-------------|
| `Pending Pickup` | `pending` | Order created, awaiting pickup |
| `On Hold` | `on_hold` | Shipment temporarily held |
| `In Transit` | `in_transit` | Package in transit |
| `Out for Delivery` | `out_for_delivery` | Out for delivery to recipient |
| `Delivered, Received by Customer` | `delivered` | Successfully delivered |
| `Delivery Fail` | `delivery_failed` | Delivery attempt failed |
| `Cancelled` | `cancelled` | Order cancelled |
| `Returned to Sender` | `returned` | Package returned to shipper |

### Webhook Payload Example

```json
{
  "tracking_number": "NVSGMA123456789",
  "status": "Delivered, Received by Customer",
  "timestamp": "2025-10-25T11:23:45Z",
  "shipper_id": 123456,
  "delivery_address": {
    "address": "10 Anson Road, #05-10",
    "city": "Singapore",
    "postal_code": "079903"
  },
  "proof_of_delivery_url": "https://..."
}
```

### Signature Verification

All webhooks are verified using HMAC-SHA256:

```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, client_secret):
    """Verify NinjaVan webhook signature"""
    expected = hmac.new(
        client_secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
```

**Signature Header**: `X-Ninjavan-Hmac-Sha256`

---

## API Endpoints Used

### OAuth & Authentication

- **Token Exchange**: `POST /1.0/oauth/token`
  - Exchange authorization code for access token
  - Refresh expired access token

- **Logout**: `POST /global/aaa/1.0/logout`
  - Invalidate access and refresh tokens

### Order Management

- **Create Order**: `POST /{countryCode}/plugins/4.2/orders`
  - Create delivery order with tracking number
  - Supports all service types

- **Cancel Order**: `DELETE /{countryCode}/plugins/2.2/orders/{trackingNo}`
  - Cancel order (Pending Pickup only)

### Label Generation

- **Generate Waybill**: `GET /{countryCode}/plugins/2.0/waybills?tids={trackingNo}`
  - Returns PDF waybill
  - Can request multiple tracking numbers

### Configuration

- **Shipper Settings**: `GET /{countryCode}/plugins/2.0/shippers/settings`
  - Fetch merchant's service types, levels, and settings

### Webhook Management

- **List Subscriptions**: `GET /{countryCode}/plugins/2.1/shippers/webhooks`
- **Create Subscription**: `POST /{countryCode}/plugins/2.1/shippers/webhooks`
- **Delete Subscription**: `DELETE /{countryCode}/plugins/2.1/shippers/webhooks/{id}`

---

## Service Types Supported

| Service Type | Description | Use Case |
|--------------|-------------|----------|
| **Parcel** | Standard parcel delivery | Most common use case |
| **Return** | Return shipments | Customer returns |
| **Marketplace** | Marketplace orders | E-commerce platforms |
| **Corporate** | Corporate shipments | B2B deliveries |
| **International** | Cross-border shipping | International orders |
| **B2B** | Business-to-business | Commercial shipments |

### Service Levels

Service levels vary by country and account type:
- **Standard** - Regular delivery (most countries)
- **Express** - Faster delivery (select countries)
- **Same Day** - Same-day delivery (major cities)
- **Next Day** - Next-day delivery

Check your account's available service levels using `test_connection()`.

---

## Advanced Features

### Cash on Delivery (COD)

```python
shipment_data = {
    'service_type': 'Parcel',
    'cod_amount': 150.00,
    'cod_currency': 'SGD',
    # ... other fields
}
```

### Pickup Scheduling

```python
shipment_data = {
    'service_type': 'Parcel',
    'pickup_date': '2025-10-24',
    'pickup_timeslot': {
        'start_time': '14:00',
        'end_time': '18:00'
    },
    # ... other fields
}
```

### Delivery Time Slots

```python
shipment_data = {
    'service_type': 'Parcel',
    'delivery_timeslot': {
        'start_time': '09:00',
        'end_time': '12:00'
    },
    # ... other fields
}
```

### Temperature Control (Cold Chain)

```python
shipment_data = {
    'service_type': 'Parcel',
    'temperature_control': True,
    'temperature_range': 'CHILLED',  # or 'FROZEN'
    # ... other fields
}
```

### Ninja Points (PUDO)

```python
shipment_data = {
    'service_type': 'Parcel',
    'ninja_point': {
        'id': 'NP12345',
        'name': 'Junction 8 Collection Point',
        'address': '9 Bishan Place'
    },
    # ... other fields
}
```

---

## Error Handling

### Common Errors

| Error | HTTP Code | Cause | Solution |
|-------|-----------|-------|----------|
| Invalid grant | 401 | Authorization code already used or expired | Re-initiate OAuth flow |
| Invalid client | 401 | Wrong Client ID or Secret | Verify credentials in NinjaVan Dashboard |
| Unauthorized | 401 | Access token expired | Token auto-refreshed by provider |
| Forbidden | 403 | Insufficient permissions or not audited | Check scopes or complete audit |
| Service not supported | 400 | Service type not enabled for account | Contact NinjaVan to enable service |
| Duplicate tracking ID | 400 | Tracking number already exists | Check for duplicate orders |
| Invalid timeslot | 400 | Invalid pickup/delivery time | Use valid time format (HH:MM) |
| Missing dimension | 400 | Weight or size missing | Provide all parcel dimensions |

### Error Response Format

```python
{
    'success': False,
    'message': 'User-friendly error message',
    'error_code': 'INVALID_SERVICE_TYPE',
    'details': {
        'http_status': 400,
        'api_response': {...}
    }
}
```

### Retry Logic

The provider includes automatic retry with exponential backoff for:
- Network timeouts
- 5xx server errors
- 429 rate limit errors

**Does not retry**:
- 400 validation errors
- 401 authentication errors (triggers token refresh instead)
- 403 authorization errors
- 404 not found errors

---

## Rate Limiting

### Known Rate Limits

- **OAuth Token API**: Rate limited (exact limit unspecified by NinjaVan)
- **Waybill Generation API**: Rate limited (exact limit unspecified)
- **Other Plugin APIs**: No explicit rate limits documented

### 429 Error Handling

If you receive a 429 error:
1. Provider automatically retries with exponential backoff
2. NinjaVan recommends waiting a few hours before retry
3. Contact `devsupport@ninjavan.co` if persistent

---

## Troubleshooting

### OAuth Authorization Fails

**Problem**: Redirect URI not registered or invalid state parameter

**Solutions**:
1. Verify you emailed `devsupport@ninjavan.co` with redirect URI
2. Check HTTPS is enabled on your domain
3. Ensure redirect URI exactly matches what you provided to NinjaVan
4. Clear browser cookies and try again

### Token Refresh Fails

**Problem**: "Invalid refresh token" error

**Solutions**:
1. Re-initiate OAuth flow to obtain new tokens
2. Check if tokens were revoked in NinjaVan Dashboard
3. Verify Client ID and Secret haven't changed

### Connection Test Fails

**Problem**: "Insufficient permissions" or 403 Forbidden

**Solutions**:
1. Verify all required scopes were granted during OAuth
2. For production: ensure you passed integration audit
3. Check environment setting matches credentials (sandbox vs production)

### Order Creation Fails

**Problem**: "Service level not supported" error

**Solutions**:
1. Use `test_connection()` to check available service types
2. Contact NinjaVan to enable required service types
3. Verify service level is available in your country

### Webhooks Not Received

**Problem**: No webhook events received

**Solutions**:
1. Check webhook endpoint is accessible via HTTPS
2. Verify signature verification logic is correct
3. Check webhook subscriptions: `GET /{countryCode}/plugins/2.1/shippers/webhooks`
4. In sandbox: Only "Pending Pickup" and "Cancelled" webhooks work
5. Ensure no firewall blocking NinjaVan webhook IPs

### Label Generation Fails

**Problem**: Waybill API returns 404 or empty response

**Solutions**:
1. Wait a few minutes after order creation
2. Verify order reached "Pending Pickup" status via webhook
3. Check tracking number is correct
4. Try again with longer delay

---

## Security Considerations

### Credential Storage

- **Encryption**: All credentials encrypted using Fernet encryption
- **Database**: Stored in encrypted provider credentials table
- **Logs**: Credentials automatically redacted in logs
- **Never logged**: OAuth tokens, Client Secret

### Token Management

- **Storage**: Tokens encrypted in database
- **Expiration**: Auto-refresh 5 minutes before expiry
- **Thread-safe**: Token refresh uses threading locks
- **Revocation**: Tokens cleared on provider disconnection

### Webhook Security

- **Signature Verification**: Always verify HMAC-SHA256 signature
- **Constant-time Comparison**: Use `hmac.compare_digest()` to prevent timing attacks
- **HTTPS Required**: Webhook endpoint must use HTTPS
- **Invalid Signatures**: Automatically rejected with 401 response

### OAuth State Parameter

- **Generation**: Unique state generated per OAuth flow
- **Storage**: Stored in session
- **Verification**: State verified on callback to prevent CSRF
- **Expiration**: State expires after 10 minutes

---

## Testing

### Run Unit Tests

```bash
./shop_venv/bin/python manage.py test shipping.providers.ninjavan.tests --keepdb -v 2
```

### Manual Testing (Sandbox)

```python
from shipping.providers.ninjavan import NinjaVanProvider

# Use sandbox credentials
provider = NinjaVanProvider({
    'client_id': 'sandbox_client_id',
    'client_secret': 'sandbox_client_secret',
    'country_code': 'sg',
    'environment': 'sandbox',
    'oauth_access_token': 'token...',
    'oauth_refresh_token': 'refresh...',
    'oauth_expires_at': 1234567890
})

# Test connection
result = provider.test_connection()
print(f"Connection: {result['success']}")

# Create test order
shipment = {
    'service_type': 'Parcel',
    'service_level': 'Standard',
    # ... (see Usage section for full example)
}

label = provider.buy_label(shipment)
print(f"Tracking: {label['tracking_number']}")
```

### Sandbox Limitations

- Always uses `/sg` endpoint regardless of country
- Only "Pending Pickup" and "Cancelled" webhooks testable
- Other webhooks require operational activities not feasible in sandbox
- Some features may have limited functionality

---

## Capabilities

```python
capabilities = {
    "rates": False,          # Plugin APIs don't support pricing lookups
    "labels": True,          # Create orders + generate waybills
    "tracking": True,        # Webhook-based status updates
    "international": True,   # Multi-country support
    "returns": True,         # Return service type supported
    "insurance": True        # Insurance available (check account)
}
```

### Why No Rate Calculation?

NinjaVan Plugin APIs are designed for merchants who already have NinjaVan accounts with established pricing. The APIs don't expose rate calculation endpoints because:
- Merchants already know their negotiated rates
- Pricing is account-specific and pre-negotiated
- Focus is on order creation and fulfillment, not shopping

---

## Support

### Platform Support

- **Documentation**: See platform shipping documentation
- **Issues**: Report via platform issue tracker

### NinjaVan Support

- **API Documentation**: https://api-docs.ninjavan.co/en
- **Plugin Integration Guide**: https://api-docs.ninjavan.co/en#tag/Plugin-integration
- **Plugin APIs**: https://api-docs.ninjavan.co/en#tag/Plugin-APIs
- **Developer Support**: devsupport@ninjavan.co
- **Sandbox Dashboard**: https://dashboard-sandbox.ninjavan.co
- **Production Dashboard**: https://dashboard.ninjavan.co

---

## Version History

See [CHANGELOG.md](./CHANGELOG.md) for detailed version history.

---

## License

Proprietary - Copyright © 2025 Spwig. All rights reserved.

---

**Last Updated**: 2025-10-23
**Maintainer**: Spwig Platform Team
