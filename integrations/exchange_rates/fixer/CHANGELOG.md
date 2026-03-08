# Changelog

All notable changes to the Fixer.io exchange rate provider will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-24

### Added
- Initial release of Fixer.io provider
- Support for 170+ currencies via Fixer.io API (APILayer)
- Real-time exchange rates with hourly updates (free tier)
- Automatic conversion for non-EUR base currencies
- Free tier support (100 requests/month)
- Encrypted credential storage (Fernet encryption)
- Comprehensive error handling for all Fixer.io error codes:
  - 101: Invalid Access Key
  - 103: API function does not exist
  - 104: Rate limit reached
  - 105: Access forbidden
  - 201: Invalid base currency
  - 202: Invalid currency symbols
- HTTP error handling (401, 403, 429, timeout)
- Rate sanity checking and validation
- Test connection via symbols endpoint
- Full unit and integration test coverage
- EUR base currency for free tier (automatic conversion for other bases)
- Credential validation and redaction for secure logging
- Support for get_rate() and get_rates() abstract methods
- Support for get_supported_currencies() method
- Detailed setup instructions with 4-step wizard

### Technical Details
- Base URL: https://data.fixer.io/api
- Authentication: access_key query parameter
- Response format: JSON with success boolean
- API error format: {"success": false, "error": {"code": 101, "info": "message"}}
- Base currency: EUR (free tier only)
- Conversion formula: GBP_USD = EUR_USD / EUR_GBP

### Dependencies
- Python >= 3.10
- Django >= 4.2
- requests >= 2.28.0

### Notes
- Free tier limited to EUR base currency
- Paid plans (Professional and above) support any base currency
- Historical data requires Basic plan or higher
- Provider automatically handles EUR-to-other-currency conversions
