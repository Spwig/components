# Changelog

All notable changes to the USPS Shipping Provider will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-10-24

### Added
- Provider logo (SVG/PNG format, 200x200px) for display in provider browse interface
- Logo metadata in manifest.json

## [1.0.0] - 2025-10-23

### Added

#### Core Features
- Initial release of USPS shipping provider integration
- OAuth 2.0 authentication with Client Credentials grant
- 8-hour token lifetime with automatic caching and refresh
- Support for Test (TEM) and Production environments

#### Shipping Operations
- Rate calculation for all USPS domestic mail classes
- Label generation with PDF, PNG, ZPL, and TIFF format support
- Package tracking with detailed event history
- Return label generation
- Extra services support (insurance, signature confirmation)

#### Mail Classes Supported
- USPS Ground Advantage™ (primary ground service)
- Priority Mail®
- Priority Mail Express®
- Parcel Select®
- USPS Connect® Local
- USPS Connect® Regional
- Media Mail®
- Library Mail
- Bound Printed Matter
- All corresponding return services

#### API Integration
- Rate calculation via `/prices/v3/base-rates/search`
- Label generation via `/labels/v3/label`
- Tracking via `/tracking/v3r2/tracking` (POST method)
- Multipart response parsing for labels
- Automatic status text mapping to platform statuses

#### Error Handling
- Comprehensive exception hierarchy with 10+ exception types
- Error code mapping for common USPS API errors
- Retry logic with exponential backoff
- Respects rate limits with Retry-After header support
- Detailed error logging for troubleshooting

#### Data Transformations
- Address formatting and ZIP code validation
- Parcel formatting with weight/dimension conversions
- Processing category auto-determination (MACHINABLE vs NONSTANDARD)
- Mail class name translations
- Date/time parsing for tracking events

#### Documentation
- Complete setup instructions with 6-step wizard guide
- Comprehensive README with usage examples
- API reference documentation
- Troubleshooting guide
- External resource links

### Technical Details

#### Dependencies
- Python >= 3.10
- Django >= 4.2
- requests >= 2.31.0
- python-dateutil >= 2.8.2

#### Architecture
- Modular design with separate auth, utils, documents, and retry modules
- Thread-safe OAuth token acquisition
- Multipart/form-data label response parser
- Status text pattern matching engine
- Configurable retry behavior

#### Security
- Encrypted credential storage
- Secure credential redaction in logs
- HTTPS-only API communication
- Token caching with automatic expiration

### Known Limitations

- **Domestic Only:** International shipping not supported in v1.0.0
- **No Webhooks:** USPS API doesn't provide webhook support
- **No Label Cancellation:** Labels cannot be voided via API
- **No Pickup Scheduling:** Carrier pickup not implemented in v1.0.0
- **Payment Account Required:** Label generation requires EPS/Permit/Meter account setup

### Notes

- Payment authorization token management (60-day lifetime) supported but not fully automated
- Test environment (TEM) available immediately; Production requires account approval
- Rate calculation and tracking work without payment account
- Label generation requires both OAuth credentials and payment authorization

### Migration Notes

- This is the initial release - no migration required
- Credentials must be configured through the connection wizard
- Payment account setup is optional for rates/tracking, required for labels

---

## Roadmap

### Planned for v1.1.0

- International shipping support
- Customs form generation
- Carrier pickup scheduling integration
- Address validation integration
- Enhanced extra services (registered mail, collect on delivery)
- Bulk rate calculations
- Smart Locker delivery support

### Planned for v1.2.0

- Payment authorization token automation
- Webhook simulator for tracking updates
- Advanced label customization options
- Return label automation
- Hazmat shipping support

---

## Support

For questions, issues, or feature requests:
- **Developer Portal:** https://developers.usps.com/
- **API Support:** https://emailus.usps.com/s/web-tools-inquiry
- **Platform Support:** Contact Spwig support team

---

**Format Version:** 1.0.0
**Last Updated:** 2025-10-23
