# ExchangeRate-API Provider

Real-time currency exchange rates powered by ExchangeRate-API with 99.99% uptime and support for 160+ currencies.

## Overview

ExchangeRate-API is one of the most reliable and generous exchange rate providers available, offering:

- **30,000 free requests per month** - one of the highest free tiers
- **99.99% uptime** in 2024
- **160+ currencies** supported
- **Any base currency** (not limited to USD)
- **Simple, fast API** with v6 endpoints
- **Automatic plan detection** via /quota endpoint

## Features

### Supported Capabilities

- ✅ Live exchange rates (daily updates on free tier)
- ✅ Any base currency selection
- ✅ Batch rate fetching (all rates in one request)
- ✅ 160+ world currencies
- ✅ Dynamic currency list from API
- ✅ Auto-detection of account plan type
- ❌ Historical rates (Pro plans only)
- ❌ Cryptocurrency rates
- ❌ Commodities

### Free Tier

- **30,000 requests/month** - extremely generous
- **Daily rate updates**
- **All 160+ currencies**
- **Any base currency**
- **HTTPS encryption**
- **99.99% uptime**
- **No credit card required**

### Pro Plans

Starting at $9.99/month:

- **50,000 to 1M+ requests/month**
- **Hourly or real-time updates**
- **Historical data** (select plans)
- **Enhanced features**
- **Priority support**

[View all pricing plans →](https://www.exchangerate-api.com/#pricing_table)

## Setup Instructions

### 1. Sign Up

1. Visit [exchangerate-api.com](https://www.exchangerate-api.com)
2. Click "Get Free API Key"
3. Enter your email address
4. Click "Get Free Key"

### 2. Verify Email

Check your inbox for a verification email from ExchangeRate-API and click the verification link.

### 3. Get Your API Key

Your API Key is displayed on your dashboard immediately. It looks like:

```
1137a55f91aad6c1244b0ac4
```

### 4. Configure in Shop

1. Go to **Settings > Exchange Rates** in your shop admin
2. Click "Add Provider" and select "ExchangeRate-API"
3. Paste your API Key
4. Click "Test Connection" to verify
5. Save and activate

## API Details

### Endpoints Used

This provider uses the ExchangeRate-API v6 endpoints:

- **Latest rates**: `GET /v6/{KEY}/latest/{BASE}`
- **Supported codes**: `GET /v6/{KEY}/codes`
- **Quota info**: `GET /v6/{KEY}/quota`

### Response Format

```json
{
  "result": "success",
  "base_code": "USD",
  "conversion_rates": {
    "EUR": 0.8601,
    "GBP": 0.7515,
    "JPY": 152.81,
    ...
  }
}
```

### Error Handling

The provider handles all common error scenarios:

- `invalid-key` - Invalid API key
- `quota-reached` - Monthly limit exceeded
- `unsupported-code` - Currency not supported
- `inactive-account` - Account suspended
- Network errors and timeouts

## Usage

### Fetching Rates

The provider automatically fetches and caches exchange rates. Rates are updated based on your plan:

- **Free tier**: Daily updates
- **Pro plans**: Hourly or real-time

### Base Currency

Unlike some providers, ExchangeRate-API supports **any base currency**, not just USD. This means:

- No complex cross-rate calculations needed
- More accurate rates
- Simpler implementation
- Better performance

### Plan Detection

The provider automatically detects your plan type by checking the `/quota` endpoint:

- **Free**: ≤30,000 requests/month
- **Pro Basic**: 50,000-100,000 requests/month
- **Pro Advanced**: >100,000 requests/month

## Rate Limits

### Free Tier

- **30,000 requests/month**
- Resets on your signup anniversary day
- No per-minute limits
- Daily rate updates

### Monitoring Usage

The provider automatically tracks your usage via the `/quota` endpoint:

```python
{
    'plan_quota': 30000,
    'requests_remaining': 28543,
    'refresh_day_of_month': 15,
    'plan_type': 'free'
}
```

## Supported Currencies

The provider dynamically fetches the list of supported currencies from the `/codes` endpoint. Currently supports 160+ currencies including:

### Major Currencies
- USD, EUR, GBP, JPY, CHF, CAD, AUD, NZD
- CNY, INR, BRL, ZAR, MXN, SGD, HKD, KRW

### European Currencies
- SEK, NOK, DKK, PLN, CZK, HUF, RON, BGN
- HRK, RUB, TRY, ISK, ALL, RSD, MKD, BAM

### Asian Currencies
- THB, MYR, IDR, PHP, VND, PKR, LKR, NPR
- BDT, MMK, LAK, KHR, MNT, AZN, AMD, GEL

### African Currencies
- EGP, MAD, NGN, KES, GHS, ETB, UGX, TZS
- ZMW, BWP, NAD, MUR, DZD, TND, LYD, AOA

### Americas
- ARS, CLP, COP, PEN, VES, BOB, PYG, UYU
- CRC, GTQ, HNL, DOP, TTD, JMD, BSD, BBD

And many more...

## Troubleshooting

### "Invalid API Key"

- Verify you copied the entire key (24 characters)
- Check for extra spaces before/after
- Ensure you verified your email address
- Try generating a new key in your dashboard

### "Quota Reached"

- You've exceeded your monthly limit (30,000 on free tier)
- Wait for your quota to reset on your refresh day
- Or upgrade to a Pro plan for higher limits

### "Connection Timeout"

- Check your internet connection
- Verify no firewall blocking HTTPS to exchangerate-api.com
- Try again in a few moments

### Rates Not Updating

- Free tier updates daily (not real-time)
- Check your last sync time in provider dashboard
- Manual sync available in admin panel
- Consider Pro plan for hourly/real-time updates

## Advantages Over Other Providers

### vs Currencylayer
- ✅ **30x higher free tier** (30k vs 1k requests)
- ✅ **Any base currency** (not just USD)
- ✅ **Better uptime** (99.99% vs varying)
- ✅ **Simpler response format**

### vs Open Exchange Rates
- ✅ **30x higher free tier** (30k vs 1k requests)
- ✅ **Better free tier features**
- ✅ **No credit card for free tier**

### vs Fixer.io
- ✅ **300x higher free tier** (30k vs 100 requests)
- ✅ **Better uptime**
- ✅ **More modern API (v6)**

## Best Practices

### 1. Cache Aggressively

The platform automatically caches rates for 24 hours. Don't manually fetch rates on every page load.

### 2. Monitor Usage

Check your `/quota` regularly to avoid hitting limits:

```python
provider.get_rate_limits()
```

### 3. Handle Errors Gracefully

Always wrap rate fetching in try-catch to handle API errors:

```python
try:
    rate = provider.get_rate('USD', 'EUR')
except Exception as e:
    logger.error(f"Failed to fetch rate: {e}")
    # Use cached rate or fallback
```

### 4. Upgrade When Needed

If you're consistently hitting the 30k limit, upgrade to a Pro plan. The cost is minimal compared to the value.

## Support

### Documentation

- [API Documentation](https://www.exchangerate-api.com/docs)
- [FAQ](https://www.exchangerate-api.com/#faq)
- [Pricing Plans](https://www.exchangerate-api.com/#pricing_table)

### Getting Help

- [Support Page](https://www.exchangerate-api.com/docs/support)
- Email: support@exchangerate-api.com
- Response time: Usually within 24 hours

### Provider Issues

For issues with this provider integration:

- Check logs in `/var/log/shop/exchange_rates.log`
- Test connection in admin panel
- Verify API key is correct
- Check quota hasn't been exceeded

## License

This provider integration is proprietary to Spwig. The ExchangeRate-API service has its own terms of service at [exchangerate-api.com/terms](https://www.exchangerate-api.com/terms).

## Version

**1.0.0** - Initial Release (2025-10-25)

See [CHANGELOG.md](CHANGELOG.md) for version history.
