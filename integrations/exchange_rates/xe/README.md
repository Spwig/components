# XE Currency Data API Provider

Premium exchange rate data from the global leader - XE.com. Trusted for 30+ years with 220+ currencies from 100+ authoritative sources.

## Overview

XE Currency Data API delivers enterprise-grade exchange rate data with unparalleled brand recognition and data quality:

- **30+ years of trust** - Global leader in currency information
- **220+ currencies** from 100+ authoritative sources
- **Mid-market rates** with no hidden markup
- **Historical data access** (package dependent)
- **Monthly average rates** for financial reporting
- **Automatic package detection** based on your subscription
- **Any base currency** supported (not limited to USD)

## Brand Value

### Why XE?

**Global Recognition**: XE.com is recognized worldwide as the go-to source for currency information. When customers see "Powered by XE," they trust the data.

**Data Quality**: Unlike providers that rely on a single source, XE aggregates data from 100+ authoritative sources including:
- Central banks
- Financial institutions
- Currency exchanges
- Market data providers

**Proven Track Record**: 30+ years serving millions of users globally - from consumers to major financial institutions.

## Features

### Supported Capabilities

- ✅ Live exchange rates (mid-market, no markup)
- ✅ 220+ world currencies
- ✅ Any base currency selection (not USD-only)
- ✅ Batch rate fetching (all rates in one request)
- ✅ Historical data (package dependent)
- ✅ Monthly average rates (package dependent)
- ✅ Automatic account detection
- ✅ Trial mode warnings
- ❌ Cryptocurrency rates
- ❌ Commodity prices

### Subscription Packages

XE offers various subscription tiers tailored to different business needs. Pricing is customized based on:
- Request volume requirements
- Update frequency needs (hourly, daily, real-time)
- Historical data access
- Support level

**Contact XE for pricing**: [https://www.xe.com/xecurrencydata/](https://www.xe.com/xecurrencydata/)

### 7-Day Trial

**⚠️ IMPORTANT**: Trial accounts are for testing only and return **MOCK RATES**, not real market data.

**Trial limitations**:
- ❌ **MOCK RATES** - Not actual exchange rates
- ❌ Not suitable for production use
- ❌ Limited to 100 requests
- ⏰ 7-day access only

**To use real exchange rates**, you must upgrade to a paid subscription package.

## Setup Instructions

### 1. Sign Up

Visit [XE Currency Data API](https://www.xe.com/xecurrencydata/) and sign up for an account.

- For testing: Start with 7-day trial (mock rates only)
- For production: Contact sales for subscription package

### 2. Get Your Credentials

Unlike other providers, XE requires **two credentials**:

**Account ID** (Username):
- Provided when you sign up
- Not secret - may appear in logs
- Used as username for HTTP Basic Auth
- Example: `spwig686304491`

**API Key** (Password):
- Provided along with Account ID
- Secret - will be encrypted when stored
- Used as password for HTTP Basic Auth
- Example: `ajd6ph4c3djpqt10p22if94tni`

### 3. Configure in Shop

1. Go to **Settings > Exchange Rates** in your shop admin
2. Click "Add Provider" and select "XE Currency Data API"
3. Enter **both** your Account ID and API Key
4. Click "Test Connection" to verify
5. **Check for trial warning** if using trial account
6. Save and activate

## API Details

### Endpoints Used

This provider uses the XE Currency Data API v1:

- **Account info**: `GET /v1/account_info.json` (FREE - doesn't count against quota!)
- **Currencies list**: `GET /v1/currencies.json`
- **Live rates**: `GET /v1/convert_from.json?from={BASE}&to={TARGETS}&amount=1`
- **Historical rates**: `GET /v1/historic_rate.json?from={BASE}&to={TARGETS}&date=YYYY-MM-DD`

### Authentication

**HTTP Basic Authentication**:
- Username: Your Account ID
- Password: Your API Key

### Response Format

**Convert From Response**:
```json
{
  "terms": "https://www.xe.com/legal/",
  "privacy": "https://www.xe.com/privacy.php",
  "from": "USD",
  "amount": 1.0,
  "timestamp": "2024-10-25T12:00:00Z",
  "to": [
    {
      "quotecurrency": "EUR",
      "mid": 0.8601
    },
    {
      "quotecurrency": "GBP",
      "mid": 0.7515
    }
  ]
}
```

**Account Info Response**:
```json
{
  "id": "spwig686304491",
  "organization": "Spwig",
  "package": "trial",
  "service_start_timestamp": "2025-10-25T00:00:00Z"
}
```

### Error Handling

The provider handles all common error scenarios:

- `401 Unauthorized` - Invalid Account ID or API Key
- `403 Forbidden` - Quota exceeded or account suspended
- `404 Not Found` - Invalid currency code
- `429 Too Many Requests` - Rate limited
- Network errors and timeouts

## Usage

### Fetching Rates

The provider automatically fetches and caches exchange rates. Update frequency depends on your package:

- **Trial**: Mock data (not real rates)
- **Basic packages**: Daily updates
- **Premium packages**: Hourly or real-time updates

### Base Currency

XE supports **any base currency**, not just USD. This means:
- More accurate rates (no cross-calculations)
- Better performance
- Simpler implementation

### Account Detection

The provider automatically detects your account package by calling the `/account_info` endpoint:

- **Package type** (trial, basic, premium, enterprise)
- **Trial mode detection** (shows prominent warnings)
- **Historical data support** (based on package)
- **Service start date**

**Best part**: The account info endpoint is **FREE** and doesn't count against your quota!

### Trial Mode Warnings

If you're using a trial account, the provider will:

1. ✅ Detect trial mode automatically
2. ⚠️  Show prominent warnings in admin UI
3. ⚠️  Log warnings when fetching rates
4. ✅ Still allow activation (for testing)
5. 🔗 Provide upgrade links

**Example warning**:
```
⚠️  XE TRIAL MODE: This account returns MOCK RATES, not real market data.
Upgrade at https://www.xe.com/xecurrencydata/ for production use.
```

## Rate Limits

Rate limits are **package-specific** and not exposed via the API.

**What we know**:
- **Trial**: 100 requests total (7 days)
- **Paid packages**: Varies by subscription

**Check your quota**: Log into your XE dashboard to see current usage and limits.

## Supported Currencies

The provider dynamically fetches the list of supported currencies from the `/currencies` endpoint. Currently supports **220+ currencies** including:

### Major Currencies
- USD, EUR, GBP, JPY, CHF, CAD, AUD, NZD
- CNY, INR, BRL, ZAR, MXN, SGD, HKD, KRW

### Regional Coverage
- **Europe**: All EU currencies plus SEK, NOK, DKK, PLN, CZK, HUF, RON, etc.
- **Asia**: THB, MYR, IDR, PHP, VND, PKR, LKR, NPR, BDT, etc.
- **Africa**: EGP, MAD, NGN, KES, GHS, ETB, UGX, TZS, ZMW, etc.
- **Americas**: ARS, CLP, COP, PEN, BOB, PYG, UYU, CRC, etc.
- **Middle East**: AED, SAR, QAR, KWD, BHD, OMR, JOD, ILS, etc.

And many more...

## Troubleshooting

### "Authentication failed"

- Verify you entered **both** Account ID and API Key
- Check for extra spaces before/after credentials
- Ensure you copied complete credentials (no truncation)
- Verify account is active (not suspended or expired)

### "Quota exceeded"

- You've exceeded your package's monthly request limit
- Trial accounts: Limited to 100 requests total
- Paid accounts: Check your dashboard for quota
- Consider upgrading to a higher-volume package

### "Trial mode warning"

This is **expected** for trial accounts. Trial accounts return MOCK RATES for testing purposes only.

**To resolve**: Upgrade to a paid subscription package at [xe.com/xecurrencydata](https://www.xe.com/xecurrencydata/)

### "Historical rates not supported"

Historical data is only available on certain packages:
- ✅ Trial (for testing only - mock data)
- ✅ Premium packages
- ✅ Enterprise packages
- ❌ Basic packages (typically)

**To resolve**: Upgrade your package or disable historical rate features.

### "Connection Timeout"

- Check your internet connection
- Verify no firewall blocking HTTPS to xecdapi.xe.com
- Try again in a few moments
- XE can be slower due to multi-source aggregation (15-second timeout)

## Advantages Over Other Providers

### vs ExchangeRate-API
- ✅ **Better brand recognition** - XE is globally known
- ✅ **Higher data quality** - 100+ sources vs fewer
- ✅ **Historical data** - Available on most paid plans
- ✅ **Monthly averages** - Unique for financial reporting
- ❌ **No generous free tier** - Trial only (mock rates)
- ❌ **Pricing not public** - Contact required

### vs Currencylayer / Open Exchange Rates / Fixer
- ✅ **Global brand trust** - 30+ years, millions of users
- ✅ **More currencies** - 220+ vs 170-180
- ✅ **Better data quality** - Multi-source aggregation
- ✅ **Historical + monthly averages**
- ❌ **No free tier** - Trial with mock rates only
- ❌ **Must contact for pricing**

## Best Practices

### 1. Use Trial for Testing Only

**DO**:
- ✅ Test integration with trial account
- ✅ Verify setup process
- ✅ Check UI/UX with mock data
- ✅ Train staff on features

**DON'T**:
- ❌ Use trial rates in production
- ❌ Show trial rates to customers
- ❌ Make financial decisions on mock data
- ❌ Rely on trial for live site

### 2. Upgrade Before Production

**Before going live**:
1. Contact XE sales for subscription package
2. Upgrade account from trial
3. Update credentials if needed
4. Verify real rates are being received
5. Monitor for removal of trial warnings

### 3. Cache Aggressively

The platform automatically caches rates. Don't manually fetch on every page load.

**Default caching**: 24 hours (configurable by merchant)

### 4. Monitor Your Quota

- Log into XE dashboard regularly
- Check request usage vs limit
- Plan for traffic spikes
- Upgrade proactively if approaching limit

### 5. Leverage Brand Value

XE's brand is valuable to your customers:
- Display "Powered by XE" badge
- Link to XE for rate transparency
- Mention 100+ sources in marketing
- Highlight 30+ years of trust

## Use Cases

### E-commerce Multi-Currency Pricing

XE's mid-market rates ensure fair pricing for international customers without hidden markup.

```python
# Get current rate
rate = provider.get_rate('USD', 'EUR')
eur_price = usd_price * rate
```

### Financial Reporting

Use monthly average rates for consistent financial reporting:

```python
# Get historical average for month
avg_rate = provider.get_monthly_average('USD', 'EUR', '2025-10')
```

### Historical Analysis

Analyze currency trends for business intelligence:

```python
# Get historical rate
historical_rate = provider.get_rate('USD', 'EUR', date='2025-01-01')
```

### Price Transparency

Show customers the source of exchange rates to build trust:

```
"Prices converted using mid-market rates from XE.com -
trusted globally for 30+ years with data from 100+ sources."
```

## Support

### XE Support

- **Sales inquiries**: [Contact form](https://www.xe.com/xecurrencydata/#contact)
- **Documentation**: [API Docs](https://xecdapi.xe.com/docs/v1)
- **General**: [XE.com](https://www.xe.com)

### Provider Integration Support

For issues with this provider integration:

- Check logs in `/var/log/shop/exchange_rates.log`
- Test connection in admin panel
- Verify both credentials are correct
- Check for trial mode warnings
- Review quota limits in XE dashboard

## Security

- **Dual credentials** encrypted using Fernet (symmetric encryption)
- **Account ID** shown in logs (not secret - it's the username)
- **API Key** redacted in logs (secret - it's the password)
- All API requests use **HTTPS**
- Credentials validated before storage

## Performance

- **Average response time**: 300-500ms (slower due to multi-source aggregation)
- **Timeout**: 15 seconds (higher than other providers)
- **Batch fetching**: All 220+ rates in one request
- **Platform caching**: 24 hours default
- **Account info caching**: In-memory (doesn't count against quota)

## License

This provider integration is proprietary to Spwig. The XE Currency Data API service has its own terms of service at [xe.com/legal](https://www.xe.com/legal/).

## Version

**1.0.0** - Initial Release (2025-10-25)

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

**Ready to get started?**

1. [Sign up for XE Currency Data API →](https://www.xe.com/xecurrencydata/)
2. Get your Account ID and API Key
3. Configure in Settings > Exchange Rates
4. Test with trial (mock rates)
5. Upgrade to production package
6. Launch with confidence! 🚀
