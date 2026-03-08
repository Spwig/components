# ExchangeRatesAPI.io Provider

Real-time currency exchange rates from the ExchangeRatesAPI.io (powered by APILayer).

## Features

- **168+ Currencies**: Support for all major world currencies
- **Precious Metals**: Gold (XAU), Silver (XAG), Platinum (XPT), Palladium (XPD)
- **Real-time Rates**: Hourly updates on free tier, minute-by-minute on paid plans
- **Simple Integration**: Single Access Key authentication
- **Reliable API**: 99.9% uptime SLA
- **Free Tier Available**: 250 requests per month at no cost
- **Powered by APILayer**: Professional-grade infrastructure

## Setup

1. Sign up at [apilayer.com](https://apilayer.com?fpr=spwig)
2. Subscribe to the Exchange Rates Data API (free plan available)
3. Get your Access Key from the dashboard
4. Enter credentials in the setup wizard
5. Test connection
6. Start syncing rates!

## API Information

- **Base URL**: `https://api.apilayer.com/exchangerates_data`
- **Authentication**: Access Key in apikey header
- **Format**: JSON
- **Rate Limits**: 250 requests/month (free tier)

## Free Tier Limitations

- Hourly rate updates (not real-time)
- **EUR base currency only** (automatic conversion for other bases)
- No historical data
- Limited to 250 API calls per month

**Important**: Like other APILayer products, ExchangeRatesAPI.io's free tier uses EUR (Euro) as the base currency, not USD. This provider automatically handles conversion for non-EUR base currencies using the formula:

```
GBP_USD = EUR_USD / EUR_GBP
```

## Paid Plans

### Basic Plan ($9.99/month)
- 5,000 requests per month
- Minute-by-minute updates
- Historical data
- EUR base currency only
- HTTPS support

### Professional Plan ($49.99/month)
- 100,000 requests per month
- All Basic features
- **Any base currency** (not just EUR)
- Time-series data
- Currency conversion endpoint
- Priority support

### Enterprise Plan ($299.99/month)
- 1,000,000 requests per month
- All Professional features
- Minute-by-minute updates
- Currency fluctuation data
- Dedicated support
- SLA guarantee

## Supported Currencies

Over 168 currencies including:
- Major: EUR, USD, GBP, JPY, CHF, CAD, AUD
- Asian: CNY, INR, KRW, SGD, HKD, THB
- European: SEK, NOK, DKK, PLN, CZK
- Latin American: BRL, MXN, ARS, CLP
- Middle Eastern: SAR, AED, ILS
- African: ZAR, NGN, EGP
- Precious Metals: XAU (Gold), XAG (Silver), XPT (Platinum), XPD (Palladium)
- And many more...

## API Documentation

- [Getting Started](https://apilayer.com/marketplace/exchangerates_data-api#documentation-tab)
- [API Reference](https://apilayer.com/marketplace/exchangerates_data-api#documentation-tab)
- [Supported Currencies](https://apilayer.com/marketplace/exchangerates_data-api#details-tab)
- [Pricing](https://apilayer.com/marketplace/exchangerates_data-api#pricing-tab)

## Error Handling

This provider handles all APILayer error codes:
- **101**: Invalid Access Key
- **103**: API function does not exist
- **104**: Rate limit reached
- **105**: Access forbidden
- **201**: Invalid base currency
- **202**: Invalid currency symbols
- **401**: Unauthorized (invalid credentials)
- **403**: Forbidden (insufficient permissions)
- **429**: Too many requests (rate limit)

## Support

- **Email**: support@apilayer.com
- **Documentation**: https://apilayer.com/marketplace/exchangerates_data-api
- **Support Center**: https://apilayer.com/marketplace/exchangerates_data-api#support-tab

## Version History

See [CHANGELOG.md](CHANGELOG.md) for version history.

## License

This provider integration is provided by Spwig. ExchangeRatesAPI.io is a trademark of APILayer.

## Provider Information

- **Provider Key**: `exchangeratesapi`
- **Version**: 1.0.0
- **Author**: Spwig
- **Maintained By**: Spwig Development Team
- **Base Currency**: EUR (free tier)
