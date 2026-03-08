# Changelog

All notable changes to the Canada Post Shipping Provider will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-10-24

### Added
- Provider logo (SVG/PNG format, 200x200px) for display in provider browse interface
- Logo metadata in manifest.json

## [1.0.0] - 2025-10-23

### Added

#### Authentication & API

- HTTP Basic Authentication implementation for Canada Post REST API
- XML-based request and response handling with proper namespace support
- Automatic environment detection (Development/Production)
- Base URL configuration based on environment selection
- Credential validation with format checking (10-digit customer number)
- Secure credential storage with encryption
- Credential redaction in logs (masks sensitive data)

#### Customer Types

- **Dual customer type support** - Contract and Non-Contract Shipping
- Automatic customer type detection based on credentials
  - Contract: Has customer_number + contract_id
  - Non-Contract: Has customer_number only (no contract_id)
- Customer type-specific API endpoint routing
  - Contract: `/rs/{customer_number}/{mobo}/shipment` (v8)
  - Non-Contract: `/rs/{customer_number}/ncshipment` (v4)
- MOBO (Mailed On Behalf Of) support for Contract customers
- Customer type indicated in connection test results

#### Rate Calculation

- Get Rates API implementation (`/rs/ship/price` v4)
- Support for all domestic, USA, and international service codes:
  - **Domestic (4 services):** DOM.RP, DOM.EP, DOM.XP, DOM.PC
  - **USA (2 services):** USA.EP, USA.XP
  - **International (3 services):** INT.XP, INT.IP.AIR, INT.IP.SURF
- Canadian postal code formatting and validation (A1A1A1 format)
- Parcel weight and dimension conversions (pounds/inches to kg/cm)
- Rate response parsing with service details:
  - Service name and code
  - Base price and taxes (GST, PST, HST)
  - Total charge in CAD
  - Expected delivery date
  - Transit time
  - Guaranteed delivery indicator
- Rate sorting by price (lowest to highest)
- Contract vs Non-Contract rate differences handled automatically

#### Label Generation

- Shipment creation API implementation
- Two-step label process:
  1. POST shipment creation (returns shipment-id and artifact links)
  2. GET label artifact download (PDF binary)
- Contract shipment creation (`/rs/{customer}/{mobo}/shipment` v8)
- Non-Contract shipment creation (`/rs/{customer}/ncshipment` v4)
- Complete address handling:
  - Sender information (name, company, phone, address)
  - Recipient information (name, company, phone, address)
  - Address validation and formatting
- Parcel characteristics transmission
- Service code selection from rate quotes
- Label artifact download via href links
- PDF label encoding to Base64 data URL
- Shipment ID tracking for future operations
- Label format: PDF (8.5" x 11" or 4" x 6" depending on service)

#### Tracking

- Package tracking API implementation (`/vis/track/pin/{tracking}/summary`)
- Real-time tracking information retrieval
- Tracking number validation and cleaning (remove spaces/dashes)
- Tracking event history with timestamps
- Status mapping to platform-standard statuses:
  - `in_transit` - Item in transit
  - `out_for_delivery` - Out for delivery
  - `delivered` - Successfully delivered
  - `exception` - Delivery exception or issue
  - `available_for_pickup` - Held at post office
- Delivery location information
- Expected delivery date parsing
- Service type identification from tracking data
- Destination postal code extraction

#### Options & Features

- Shipping options support (10+ option codes):
  - **SO** - Signature required
  - **COV** - Coverage/Insurance (up to $5,000 CAD)
  - **COD** - Collect on Delivery
  - **D2PO** - Deliver to Post Office
  - **HFP** - Card for Pickup (Hold for Pickup)
  - **DNS** - Do Not Safe Drop
  - **LAD** - Leave at Door
  - **PA18** - Proof of Age 18
  - **PA19** - Proof of Age 19
  - **RASE** - Return at Sender's Expense
- Option code validation
- Option amount support (for COV, COD)
- Service-specific option compatibility checking
- Multiple options per shipment

#### International Support

- International shipment support (USA and worldwide)
- Customs declaration generation
- Customs XML building with namespace support
- Required customs fields:
  - Currency code
  - Reason for export (DOC, SAM, REP, SOG, OTH)
  - Invoice number (optional)
- Customs item details:
  - Item description (max 45 chars)
  - HS/Tariff code (6-10 digits)
  - Quantity
  - Unit value
  - Weight per item (kg)
  - Country of origin (ISO code)
- Multiple items per customs declaration
- Automatic customs requirement detection based on destination country
- Non-delivery handling instructions

#### Error Handling

- Comprehensive exception hierarchy:
  - `CanadaPostError` (base exception)
  - `CanadaPostAuthenticationError` (401 errors)
  - `CanadaPostValidationError` (validation failures)
  - `CanadaPostShipmentError` (shipment creation issues)
  - `CanadaPostTrackingError` (tracking lookup failures)
  - `CanadaPostServiceUnavailableError` (503/504 errors)
  - `CanadaPostAPIError` (generic API errors)
- XML error response parsing
- Error code extraction from XML messages
- Human-readable error messages
- Detailed error context for debugging
- Error logging with context information

#### Retry Logic

- Exponential backoff retry mechanism
- Configurable retry attempts (default: 3)
- Retryable status codes: 500, 502, 503, 504, 429
- Backoff delays: 1s, 2s, 4s (exponential)
- Non-retryable errors skip retry logic
- Request timeout protection (30s default, 60s for shipments)
- Connection error handling with automatic retry
- Rate limit respect (429 errors)

#### Manifest System

- Manifest support for Contract customers only
- Group-based shipment organization
- Shipment grouping with group-id parameter
- Transmit vs group-id endpoint differentiation
- Manifest artifact generation support
- Batch shipping workflow support
- Note: Full manifest UI implementation deferred to future release

#### Documentation

- Comprehensive README.md with:
  - Overview and features list
  - Customer type explanation (Contract vs Non-Contract)
  - Installation and configuration instructions
  - Detailed API information and endpoints
  - XML request/response examples with namespaces
  - Usage examples in Python
  - Service codes table (9 services)
  - Shipping options table (10+ options)
  - International shipping guide with customs
  - HS code examples and resources
  - Error handling documentation
  - Troubleshooting guide with solutions
  - Support resources and links
  - Performance optimization tips
  - Security best practices
- Interactive setup_instructions.html with:
  - 8-step setup wizard
  - Customer type selection interface
  - Visual customer type comparison cards
  - Credential requirements grid
  - Service codes reference tables
  - Options codes reference
  - Link to external resources
  - Troubleshooting section
  - Mobile-responsive Bootstrap design
  - Font Awesome icons throughout
- Detailed CHANGELOG.md (this file)

### Technical Details

#### Dependencies

- Python >= 3.8
- Django >= 4.2
- requests >= 2.31.0

#### Architecture

- Modular design with separate modules:
  - `auth.py` - Authentication client
  - `xml_builder.py` - XML request construction
  - `xml_parser.py` - XML response parsing
  - `utils.py` - Helper functions
  - `exceptions.py` - Exception classes
  - `retry.py` - Retry logic
- Provider class extends `ProviderBase`
- Thread-safe implementation
- XML namespace handling for all API versions
- Multipart artifact response handling
- Base64 encoding for binary PDF labels

#### API Versions

- Rate API: v4 (`application/vnd.cpc.ship.rate-v4+xml`)
- Contract Shipment API: v8 (`application/vnd.cpc.shipment-v8+xml`)
- Non-Contract Shipment API: v4 (`application/vnd.cpc.ncshipment-v4+xml`)
- Tracking API: v2 (`application/vnd.cpc.track+xml`)

#### Security

- HTTP Basic Authentication with base64 encoding
- All requests over HTTPS
- Credential encryption in database
- Password masking in logs
- Customer number partial masking (shows last 4 digits)
- No plaintext credential storage
- Request/response logging with sensitive data redaction

#### XML Handling

- Proper namespace declaration for all requests
- XML element ordering per Canada Post specifications
- UTF-8 encoding for all XML content
- Special character escaping in address fields
- XML schema validation
- Error message extraction from XML responses
- Robust XML parsing with error handling

#### Data Transformations

- **Weight conversion:** pounds (lb) → kilograms (kg)
- **Length conversion:** inches (in) → centimeters (cm)
- **Postal code formatting:** Uppercase, space normalization
- **Phone formatting:** Digit-only extraction
- **Currency handling:** CAD (Canadian dollars) throughout
- **Date parsing:** ISO 8601 to Django datetime objects
- **Status mapping:** Canada Post statuses → platform statuses

### Known Limitations

- **Pickup Scheduling:** Not implemented in v1.0.0 (planned for v1.1.0)
- **Label Cancellation:** Requires shipment ID, not tracking number
  - Must store shipment_id from buy_label response
  - Cannot void by tracking number alone
- **Multi-Parcel Shipments:** Only first parcel used
  - Multi-parcel support deferred to future release
- **No Webhooks:** Canada Post API doesn't support webhooks
  - Must poll tracking API for updates
- **Manifest UI:** Basic support only
  - Full manifest management UI deferred to future release
- **Return Labels:** Supported via API, UI integration pending

### Platform Integration

- Implements standard shipping provider interface
- Compatible with platform's shipping management system
- Integrates with order fulfillment workflow
- Works with multi-currency support (CAD primary)
- Supports international shipping with customs
- Compatible with versioned component system
- Distributed via update server
- Follows platform security standards

### Testing

- Connection test implementation
- Test environment support (ct.soa-gw.canadapost.ca)
- Production environment support (soa-gw.canadapost.ca)
- Debug logging for troubleshooting
- XML request/response logging (truncated for security)
- Test credentials support in Developer Portal
- Sandbox postal codes for testing

### Notes

- **XML-based API:** Canada Post uses XML, not JSON
  - All requests and responses are XML format
  - Requires proper namespace handling
  - Different namespaces for different API versions
- **Customer Type Critical:** Contract vs Non-Contract affects:
  - API endpoints used
  - Available features (manifests)
  - Pricing (discounted vs retail)
  - Billing method (account vs credit card)
- **Postal Code Format:** Canadian postal codes must be A1A1A1 format
  - Case insensitive but normalized to uppercase
  - Space optional but standardized
- **Service Availability:** Not all services available for all routes
  - Use Get Rates to determine available services
  - International services require customs declarations
- **Label Artifacts:** Labels accessed via href links, not inline
  - Requires second GET request to download PDF
  - Artifact links contain security tokens
- **Tracking Delay:** New tracking numbers may take 30-60 minutes to appear
- **Weight Limits:** Vary by service (typically 30 kg domestic)

### Migration Notes

- This is the initial release - no migration required
- Credentials must be configured through setup wizard or admin interface
- Customer type automatically detected from credentials
- Environment selection required (Development vs Production)
- No data migration from other providers

---

## Roadmap

### Planned for v1.1.0

- Carrier pickup scheduling integration
- Enhanced return label automation
- Multi-parcel shipment support
- Full manifest management UI
- Label cancellation by tracking number (with shipment ID mapping)
- Address validation integration
- Batch rate calculation optimization
- Smart Locker delivery support (FlexDelivery)

### Planned for v1.2.0

- Automated customs form generation for common products
- HS code lookup and suggestion
- Webhook simulator for tracking updates
- Advanced shipping options:
  - Age verification (PA18, PA19)
  - Alcohol shipment support
  - Dangerous goods declarations
- Enhanced error recovery
- Rate caching and optimization
- Bulk shipment import

### Planned for v2.0.0

- Real-time rate shopping across multiple carriers
- Hybrid JSON/XML API support (if Canada Post releases JSON API)
- Machine learning rate predictions
- Carbon offset calculation and reporting
- Advanced analytics and reporting
- Multi-contract support for enterprise customers

---

## Support

For questions, issues, or feature requests:

- **Developer Portal:** https://www.canadapost-postescanada.ca/information/app/wtz/business/productsServices/developers/default
- **API Documentation:** https://www.canadapost-postescanada.ca/cpc/doc/en/business/developers/apis/docs/index.htm
- **Platform Support:** Contact Spwig support team
- **Developer Support:** developer@canadapost.ca
- **Business Support:** 1-866-607-6301

---

**Changelog Format Version:** 1.0.0 (Keep a Changelog)
**Last Updated:** 2025-10-23
**Maintained by:** Spwig Development Team
