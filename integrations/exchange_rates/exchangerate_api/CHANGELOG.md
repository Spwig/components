# Changelog

All notable changes to the ExchangeRate-API provider will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-25

### Added

- Initial release of ExchangeRate-API provider integration
- Support for 160+ world currencies
- Real-time exchange rate fetching via ExchangeRate-API v6
- Free tier support with 30,000 requests per month
- Automatic plan detection via `/quota` endpoint
  - Detects free tier (≤30k requests)
  - Detects pro basic tier (50k-100k requests)
  - Detects pro advanced tier (>100k requests)
- Dynamic currency list fetching from `/codes` endpoint
- Any base currency support (not limited to USD)
- Encrypted credential storage using Fernet encryption
- Comprehensive error handling:
  - `invalid-key` - Invalid API key errors
  - `quota-reached` - Rate limit exceeded
  - `unsupported-code` - Unsupported currency
  - `inactive-account` - Account suspended
  - Network timeouts and connection errors
- Rate sanity checking and validation
  - Filters out non-positive rates
  - Filters out suspiciously high rates (>1,000,000)
- Test connection functionality via `/codes` endpoint
- Credential redaction for secure logging
- Full unit test coverage
- Full integration test coverage
- Complete setup wizard instructions
- Comprehensive README documentation

### Technical Details

- Provider key: `exchangerate_api`
- Provider class: `ExchangeRateAPIProvider`
- Base URL: `https://v6.exchangerate-api.com/v6`
- Timeout: 10 seconds
- Cache strategy: Respects platform's 24-hour cache
- Response format: JSON with `conversion_rates` object

### Capabilities

- Live rates: ✅ Yes
- Historical rates: ❌ No (Pro plans only)
- Cryptocurrency: ❌ No
- Commodities: ❌ No
- Base currency selection: ✅ Yes (any currency)
- Batch requests: ✅ Yes (all rates in one call)

### Rate Limits

- Free tier: 30,000 requests/month
- No per-minute limits
- Updates: Daily on free tier, hourly/real-time on Pro
- Quota reset: Monthly on signup anniversary day

### Dependencies

- Python >= 3.10
- Django >= 4.2
- requests >= 2.28.0

### Files

- `manifest.json` - Provider metadata and configuration
- `provider.py` - Main provider implementation (536 lines)
- `setup_instructions.html` - Wizard setup guide
- `README.md` - Complete documentation
- `CHANGELOG.md` - This file
- `logo.png` - Provider logo (200x200px)
- `tests/test_provider.py` - Unit tests
- `tests/test_rates.py` - Integration tests
- `tests/test_validation.py` - Validation tests

### Notes

- This is the initial public release
- Tested with ExchangeRate-API v6 endpoints
- Compatible with shop platform v1.0.0+
- Logo provided in PNG format (200x200px)

### Comparison with Other Providers

**Advantages:**
- 30x higher free tier than most competitors (30k vs 1k)
- 99.99% uptime in 2024
- Any base currency supported
- Simpler API response format
- No credit card required for free tier

**Limitations:**
- No historical data on free tier
- Daily updates only (hourly on Pro)
- No cryptocurrency support
- No commodities support

### Migration Notes

If migrating from another provider:
1. Rates are fetched in the same format (Decimal)
2. Currency codes use ISO 4217 standard
3. Base currency can be any supported currency
4. No special migration steps required

### Security

- API keys are encrypted using Fernet (symmetric encryption)
- Keys are redacted in logs (shows first 3 and last 3 chars only)
- All API requests use HTTPS
- Credentials validated before storage

### Performance

- Average response time: < 200ms
- Timeout: 10 seconds
- Supports batch fetching (all 160+ rates in one request)
- Platform caches rates for 24 hours
- Quota check is cached to avoid excessive API calls

---

## Future Versions

### Planned for 1.1.0

- Historical rate support (for Pro plan users)
- Pair conversion endpoint optimization
- Enhanced error messages with recovery suggestions
- Webhook support for rate change notifications (if API adds support)

### Under Consideration

- Cryptocurrency support (if API adds support)
- Time-series data visualization
- Custom refresh intervals per merchant
- Rate alert notifications

---

[1.0.0]: https://github.com/yourorg/shop/releases/tag/exchangerate-api-v1.0.0
