# Changelog - FedEx Shipping Provider

All notable changes to the FedEx shipping provider will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2025-10-24

### Added
- Provider logo (SVG format, 200x200px) for display in provider browse interface
- Logo metadata in manifest.json

## [1.1.0] - 2025-10-23

### Added
- **Setup Instructions**: Added comprehensive `setup_instructions.html` displayed in connection wizard Step 2
  - Step-by-step guide for creating FedEx developer account
  - Instructions for generating API credentials
  - Environment selection guidance (Test vs Production)
  - Links to FedEx Developer Portal and support resources
  - Pre-flight checklist before proceeding to credential entry

### Changed
- **Credential Schema**: Enhanced manifest.json with wizard-compatible credential_schema
  - Added field labels, help text, and placeholders for better UX
  - Added `account_number` field to credential form
  - Fields now properly labeled in Step 3 of connection wizard
- **Manifest Format**: Updated to include `credential_schema` and `signup_url` at root level

### Improved
- Connection wizard now provides clear guidance through 5-step setup process
- Better user experience for first-time FedEx API credential setup
- Credential fields now have descriptive labels and contextual help

## [1.0.0] - 2025-10-23

### Added
- Initial release of FedEx shipping provider component
- OAuth 2.0 authentication with automatic token refresh
- Rate calculation for domestic and international shipments
- Shipping label generation (PDF format)
- Real-time package tracking
- Support for multiple FedEx services (Priority Overnight, Standard Overnight, 2Day, Express Saver, Ground, etc.)
- International shipping with customs documentation
- Signature and insurance options
- Comprehensive error handling and retry logic
- Full test suite with unit and integration tests
- Detailed README with setup and configuration instructions

### Component Structure
- Migrated from embedded provider (`shipping/providers/fedex/`) to standalone component (`components/integrations/shipping/fedex/v1.0.0/`)
- Follows platform versioning standards with symlinked `current` directory
- Compatible with component update system

### Capabilities
- ✅ Rate calculation
- ✅ Label generation
- ✅ Tracking
- ✅ International shipping
- ✅ Insurance
- ✅ Signature confirmation
- ❌ Returns (not yet supported)
- ❌ Pickup scheduling (not yet supported)

### Requirements
- Python 3.12+
- requests >= 2.28.0
- python-dateutil >= 2.8.2
- Platform version >= 1.0.0

### Author
**Spwig**
- Email: support@spwig.com
- Website: https://spwig.com

---

## Future Releases

### [1.1.0] - Planned
- Add return label generation support
- Add pickup scheduling capability
- Enhanced international customs forms
- Support for additional label formats (ZPL, EPL)

### [1.2.0] - Planned
- Multi-piece shipment support
- Freight shipping integration
- Advanced rate shopping features
- Webhook improvements
