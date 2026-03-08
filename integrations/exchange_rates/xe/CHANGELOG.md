# Changelog

All notable changes to the XE Currency Data API provider will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-10-25

### Fixed

- **Provider inheritance**: XEProvider now properly inherits from `ExchangeRateProviderBase`
- **Abstract methods**: Implemented `credential_schema` as `@property` (required abstract method)
- **Abstract methods**: Changed `capabilities` from method to `@property` (required abstract method)
- **Method signatures**: Updated `validate_credentials` to raise `ValueError` instead of returning dict
- **Method decorators**: Removed `@staticmethod` from `validate_credentials` and `redact_credentials`

### Changed

- **UI/UX**: All alert boxes now use theme-aware CSS classes (`messagelist .warning/.info`)
- **CSS**: Removed inline CSS styles for better dark/light theme support
- **Security**: Placeholder credentials changed to generic examples (no real test credentials in docs)

### Technical

- Provider now loads correctly in `ProviderRegistry`
- Fully compatible with `ExchangeRateProviderBase` abstract interface
- All abstract methods properly implemented

## [1.0.0] - 2025-10-25

### Added

- Initial release of XE Currency Data API provider integration
- **Dual credential authentication system** (Account ID + API Key)
  - Account ID as username (not secret - shown in logs)
  - API Key as password (secret - encrypted and redacted)
  - HTTP Basic Authentication implementation
- **Automatic account package detection** via `/account_info` endpoint
  - Detects trial, basic, premium, enterprise packages
  - Free endpoint - doesn't count against quota
  - In-memory caching for performance
- **Trial mode detection and warning system**
  - Automatic detection when package contains "trial"
  - Prominent warnings in admin UI with yellow alert styling
  - Console warnings when fetching rates
  - Mock rate flag in responses
  - Clear activation/upgrade messaging
- Support for **220+ currencies** from 100+ authoritative sources
- **Dynamic capability detection** based on subscription package
- **Batch rate fetching** with comma-separated targets
- **Historical rate support** (package dependent)
- Encrypted credential storage using Fernet encryption
- **Comprehensive error handling**
- **Rate sanity checking and validation**
- Test connection functionality via `/account_info`
- **Credential redaction for secure logging**
- Rate limit information (package-specific)
- Complete setup wizard with trial warning banner
- Comprehensive README documentation

---

[1.0.1]: https://github.com/yourorg/shop/compare/xe-v1.0.0...xe-v1.0.1
[1.0.0]: https://github.com/yourorg/shop/releases/tag/xe-v1.0.0
