# Changelog - NinjaVan Shipping Provider

All notable changes to the NinjaVan shipping provider will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-10-24

### Added
- Provider logo (SVG/PNG format, 200x200px) for display in provider browse interface
- Logo metadata in manifest.json

---

## [1.0.0] - 2025-10-23

### Added

#### Authentication & OAuth
- OAuth 2.0 authorization code flow with automatic token refresh
- Secure token storage with encryption
- Token refresh mechanism (auto-refresh 5 minutes before expiry or on 401 errors)
- OAuth state parameter generation and verification for CSRF protection
- Thread-safe token refresh with locking mechanism
- Support for dynamic token lifetimes (minimum 1 hour as per NinjaVan specs)
- Logout functionality to invalidate tokens on provider disconnection

#### Order Management
- Order creation API (`POST /{countryCode}/plugins/4.2/orders`)
- Support for multiple service types:
  - **Parcel** - Standard parcel delivery
  - **Return** - Return shipments
  - **Marketplace** - Marketplace orders
  - **Corporate** - Corporate shipments
  - **International** - Cross-border shipping
  - **B2B** - Business-to-business deliveries
- Order cancellation API (`DELETE /{countryCode}/plugins/2.2/orders/{trackingNo}`)
  - Only works for orders in "Pending Pickup" status
- Cash on Delivery (COD) support
- Pickup scheduling with time slot selection
- Delivery time slot preferences
- Temperature-controlled shipments (Cold Chain)
- Ninja Points (PUDO - Pick Up Drop Off) integration
- Multiple parcel support in single order

#### Label Generation
- Waybill generation API (`GET /{countryCode}/plugins/2.0/waybills`)
- PDF format labels (base64-encoded)
- Support for batch waybill generation (multiple tracking numbers)
- Automatic waybill fetching after order creation

#### Tracking & Webhooks
- Webhook-based tracking updates (V2 API)
- Webhook subscription management:
  - List subscriptions (`GET /{countryCode}/plugins/2.1/shippers/webhooks`)
  - Create subscriptions (`POST /{countryCode}/plugins/2.1/shippers/webhooks`)
  - Delete subscriptions (`DELETE /{countryCode}/plugins/2.1/shippers/webhooks/{id}`)
- Auto-subscribe to all tracking events on provider activation
- Auto-cleanup webhook subscriptions on provider deactivation
- Support for 8 tracking event types:
  - Pending Pickup
  - On Hold
  - In Transit
  - Out for Delivery
  - Delivered, Received by Customer
  - Delivery Fail
  - Cancelled
  - Returned to Sender
- HMAC-SHA256 webhook signature verification
- Webhook signature validation using Client Secret
- Constant-time signature comparison to prevent timing attacks
- Database storage of webhook events for tracking queries

#### Multi-Country Support
- Support for 7 Southeast Asian countries:
  - **Singapore (SG)** - Full coverage
  - **Malaysia (MY)** - Full coverage
  - **Thailand (TH)** - Full coverage
  - **Indonesia (ID)** - Full coverage
  - **Vietnam (VN)** - Full coverage
  - **Philippines (PH)** - Full coverage
  - **Myanmar (MM)** - Full coverage
- Country-specific API endpoint routing
- Sandbox environment: Always uses `/sg` endpoint
- Production environment: Uses country-specific endpoints (`/{countryCode}`)

#### Configuration & Settings
- Shipper settings API (`GET /{countryCode}/plugins/2.0/shippers/settings`)
- Fetch available service types and levels for account
- Retrieve tracking prefix(es)
- Get pickup and delivery configuration
- Connection testing with shipper settings validation

#### Error Handling
- Comprehensive error handling with custom exception classes:
  - `NinjaVanError` - Base exception
  - `NinjaVanOAuthError` - OAuth-specific errors
  - `NinjaVanScopeError` - Missing or invalid scope errors
  - `NinjaVanAuthenticationError` - Token expired/invalid
  - `NinjaVanValidationError` - Request validation errors
  - `NinjaVanAPIError` - General API errors
- HTTP status code mapping (400, 401, 403, 404, 429, 5xx)
- User-friendly error messages with actionable solutions
- Detailed error logging with context
- Automatic credential redaction in logs

#### Retry Logic
- Exponential backoff with jitter
- Maximum 3 retry attempts
- Base delay: 1 second
- Retry on:
  - Network timeouts
  - Connection errors
  - 5xx server errors
  - 429 rate limit errors
- Do NOT retry:
  - 400 validation errors
  - 401 authentication errors (trigger token refresh instead)
  - 403 authorization errors
  - 404 not found errors

#### Security Features
- Fernet encryption for stored credentials
- Secure token storage in encrypted database fields
- HMAC-SHA256 webhook signature verification
- HTTPS requirement for OAuth redirect URI and webhooks
- OAuth state parameter for CSRF protection
- Constant-time signature comparison
- Automatic credential redaction in logs and error messages
- Client Secret never logged or exposed

#### Documentation
- Comprehensive README with setup instructions
- 9-step OAuth setup wizard (HTML)
- Integration audit requirements and guidelines
- API endpoint documentation
- Code examples for all major operations
- Troubleshooting guide
- Security best practices
- Support contact information

### Component Structure
- Standalone component at `components/integrations/shipping/ninjavan/v1.0.0/`
- Follows platform versioning standards with symlinked `current` directory
- Compatible with component update system
- Modular architecture:
  - `provider.py` - Main provider class (380 lines)
  - `auth.py` - OAuth client (245 lines)
  - `webhooks.py` - Webhook subscription manager and receiver (310 lines)
  - `utils.py` - Helper functions (country routing, signature verification, transforms) (180 lines)
  - `exceptions.py` - Custom exception classes (95 lines)
  - `retry.py` - Retry logic with exponential backoff (85 lines)
  - `manifest.json` - Component metadata with OAuth and webhook configuration

### Capabilities

#### Supported
- ✅ Order creation and management
- ✅ Shipping label generation (PDF waybills)
- ✅ Real-time tracking via webhooks
- ✅ International shipping (7 countries)
- ✅ Returns
- ✅ Insurance (account-dependent)
- ✅ Cash on Delivery (COD)
- ✅ Pickup scheduling
- ✅ Delivery time slots
- ✅ Temperature control (Cold Chain)
- ✅ Ninja Points (PUDO)

#### Not Supported
- ❌ Rate calculation - Plugin APIs do not expose pricing endpoints. Merchants use their existing NinjaVan account pricing which is pre-negotiated and account-specific.

### Requirements
- **Python**: 3.8+
- **Django**: 3.2+
- **Dependencies**:
  - requests >= 2.28.0
  - cryptography >= 3.4.0 (for Fernet encryption)
- **Platform Version**: 1.0.0 or higher
- **NinjaVan Account**: Postpaid Pro account required
- **HTTPS**: Required for OAuth redirect URI and webhooks

### Integration Requirements

#### OAuth Setup
1. Generate Client ID and Client Secret in NinjaVan Dashboard (Settings > IT Settings)
2. Email `devsupport@ninjavan.co` to register OAuth redirect URI
3. Wait for confirmation (1-2 business days)
4. Complete OAuth authorization flow via NinjaVan Dashboard login
5. Tokens automatically managed with refresh mechanism

#### Integration Audit (Production Access)
NinjaVan requires passing an integration audit before granting production access:
1. Create 3+ test orders via integrated UI (not Postman)
2. Orders must include accurate addresses, valid contact info, and proper dimensions
3. Submit orders via audit link provided by NinjaVan
4. Pass NinjaVan QA review (3-5 business days)
5. Audit evaluates:
   - OAuth authentication flow and token handling
   - Webhook subscription timing and event processing
   - Error handling (success and failure scenarios)
   - Token refresh mechanism (5 minutes before expiry or on 401)

### API Information
- **Sandbox Base URL**: `https://api-sandbox.ninjavan.co/sg` (always `/sg`)
- **Production Base URL**: `https://api.ninjavan.co/{countryCode}`
- **Sandbox Dashboard**: `https://dashboard-sandbox.ninjavan.co`
- **Production Dashboard**: `https://dashboard.ninjavan.co`
- **OAuth Token URL**: `/1.0/oauth/token`
- **Logout URL**: `/global/aaa/1.0/logout`
- **Documentation**: https://api-docs.ninjavan.co/en#tag/Plugin-APIs

### Known Limitations
- **Rate Calculation**: Not supported - Plugin APIs don't expose pricing endpoints
- **Tracking API**: No direct tracking API - relies on webhook events stored in database
- **Order Cancellation**: Only works for orders in "Pending Pickup" status
- **Sandbox Endpoints**: Sandbox always uses `/sg` endpoint regardless of country code
- **Sandbox Webhooks**: Only "Pending Pickup" and "Cancelled" webhooks testable in sandbox
- **Rate Limits**: OAuth token and waybill APIs are rate-limited (exact limits unspecified). 429 errors require waiting a few hours before retry.

### Author
**Spwig**
- Email: support@spwig.com
- Website: https://spwig.com

---

## Future Releases

### [1.1.0] - Planned
- Enhanced error reporting with more detailed API error messages
- Support for bulk order creation
- Advanced filtering for webhook event queries
- Performance optimizations for high-volume merchants
- Additional service type support (as NinjaVan adds them)

### [1.2.0] - Planned
- Multi-piece shipment support (single order with multiple tracking numbers)
- Enhanced COD features (partial COD, COD verification)
- Pickup request API integration (schedule pickups via API)
- Address validation API integration
- Real-time delivery slot availability checking

### [1.3.0] - Planned
- Order modification API (update order details before pickup)
- Proof of delivery retrieval and storage
- Enhanced reporting and analytics
- Webhook retry mechanism for failed deliveries
- Support for NinjaVan's upcoming API features

---

## Migration Notes

### From Other Providers
If migrating from FedEx, UPS, or USPS providers:
- **Authentication**: NinjaVan uses OAuth 2.0 instead of API keys
- **Rate Calculation**: Not available in NinjaVan - use your account pricing
- **Tracking**: Webhook-based instead of polling API
- **Setup**: Requires external registration with NinjaVan support
- **Production Access**: Requires passing integration audit

### Breaking Changes
N/A - Initial release

---

## Support

### NinjaVan Support
- **Developer Support**: devsupport@ninjavan.co
- **API Documentation**: https://api-docs.ninjavan.co/en
- **Plugin Integration Guide**: https://api-docs.ninjavan.co/en#tag/Plugin-integration

### Platform Support
- **Documentation**: See platform shipping documentation
- **Issues**: Report via platform issue tracker

---

## Acknowledgments

Special thanks to:
- NinjaVan Developer Support team for API documentation and audit process guidance
- Spwig Platform Team for component architecture and OAuth framework
- Beta testers for feedback during development

---

**Release Date**: 2025-10-23
**Component Version**: 1.0.0
**License**: Proprietary - Copyright © 2025 Spwig. All rights reserved.
