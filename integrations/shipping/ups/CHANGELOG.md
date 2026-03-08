# Changelog

All notable changes to the UPS Shipping Provider will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-10-24

### Added
- Provider logo (SVG/PNG format, 200x200px) for display in provider browse interface
- Logo metadata in manifest.json

## [1.0.0] - 2025-10-23

### Added
- Initial release of UPS shipping provider integration
- OAuth 2.0 authentication with automatic token refresh and caching
- Rate calculation for domestic and international shipments via Rating API
- Support for all major UPS services (Ground, Express, International)
- Shipping label generation in multiple formats (PDF, PNG, ZPL)
- Real-time package tracking with 1Z tracking number support
- Address validation capabilities
- Insurance and signature confirmation options
- Comprehensive error handling with UPS-specific exception types
- Automatic retry logic with exponential backoff for transient failures
- Thread-safe token acquisition and caching
- Webhook signature verification (HMAC SHA-256)
- Webhook event handling for tracking updates
- Support for both test and production environments
- Complete setup instructions in connection wizard
- Detailed API request/response logging
- Label cancellation (void shipment) support

### Technical Details
- Python 3.10+ compatibility
- Django 4.2+ compatibility
- REST API integration with UPS API v1
- Base64-encoded label handling
- Decimal precision for currency calculations
- Timezone-aware datetime handling
- Django internationalization (i18n) support

### Capabilities
- ✅ Rates: Calculate shipping rates
- ✅ Labels: Generate shipping labels
- ✅ Tracking: Real-time tracking updates
- ✅ International: Cross-border shipping
- ❌ Returns: Not supported (planned for v1.1.0)
- ❌ Pickup: Pickup scheduling not supported (planned for v1.1.0)
- ✅ Insurance: Shipment insurance
- ✅ Signature: Signature confirmation

### API Endpoints Used
- `POST /security/v1/oauth/token` - OAuth authentication
- `POST /api/rating/v1/Rate` - Rate calculation
- `POST /api/shipments/v1/ship` - Label generation
- `DELETE /api/shipments/v1/void/cancel/{id}` - Label cancellation
- `GET /api/track/v1/details/{tracking}` - Tracking lookup
- `POST /api/addressvalidation/v1/1` - Address validation

### Dependencies
- requests >= 2.28.0
- python-dateutil >= 2.8.2

### Known Limitations
- Return label generation not yet supported
- Pickup scheduling not yet supported
- International customs forms require manual handling
- Some advanced service options may not be available in test environment

### Security
- API credentials encrypted at rest (handled by platform)
- OAuth tokens cached with 55-minute TTL
- Sensitive credentials redacted in logs
- HMAC signature verification for webhooks
- Thread-safe token refresh mechanism

---

## Future Releases

### Planned for v1.1.0
- Return label generation
- Pickup scheduling
- Enhanced international shipping with customs forms
- Additional service options (Saturday delivery, etc.)
- Freight shipping support
- Batch label generation

### Under Consideration
- Rate shopping across multiple carriers
- Automatic service selection based on delivery time
- Package consolidation
- Multi-piece shipment support
- Hazardous materials handling
- Carbon neutral shipping options

---

**Release Notes Format**:
- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Features removed in this release
- **Fixed**: Bug fixes
- **Security**: Security improvements

---

**Maintained by**: Spwig Platform Team
**Release Date**: October 23, 2025
**License**: Proprietary
