# Changelog

All notable changes to the Open Exchange Rates provider will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-24

### Added
- Initial release of Open Exchange Rates provider
- Support for 200+ world currencies
- Real-time exchange rate fetching from Open Exchange Rates API
- Automatic currency conversion for non-USD base currencies
- Connection testing with App ID validation
- Comprehensive error handling for API errors and rate limits
- Support for free tier (1,000 requests/month)
- Setup wizard integration with step-by-step instructions
- Full test coverage with unit and integration tests

### Features
- Live exchange rates (hourly updates on free tier)
- Simple App ID authentication
- Automatic rate validation and sanity checking
- Decimal precision for accurate currency calculations
- Fallback to default currency list if API unavailable
- Detailed error messages for troubleshooting

### Known Limitations
- Free tier only supports USD as base currency (converted automatically for other bases)
- No historical data support on free tier
- No cryptocurrency support
- Rate updates every hour on free tier (upgrade for faster updates)

### Security
- Credentials encrypted at rest using Fernet encryption
- App ID redacted in logs
- HTTPS-only API connections
- Input validation for all user-provided data

## [Unreleased]

### Planned for v1.1.0
- Historical rate support for paid plans
- Caching layer to reduce API calls
- Batch rate fetching optimization
- WebSocket support for real-time updates (Enterprise plan)

### Planned for v1.2.0
- Cryptocurrency support
- Time-series data integration
- OHLC candlestick data support
- Advanced rate change alerts
