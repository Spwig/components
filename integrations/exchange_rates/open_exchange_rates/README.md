# Open Exchange Rates Provider

Real-time currency exchange rates from the Open Exchange Rates API.

## Features

- **200+ Currencies**: Support for all major world currencies
- **Real-time Rates**: Hourly updates on free tier, minute-by-minute on paid plans
- **Simple Integration**: Single App ID authentication
- **Reliable API**: 99.9% uptime SLA
- **Free Tier Available**: 1,000 requests per month at no cost

## Setup

1. Sign up at [openexchangerates.org/signup](https://openexchangerates.org/signup)
2. Get your App ID from the dashboard
3. Enter credentials in the setup wizard
4. Test connection
5. Start syncing rates!

## API Information

- **Base URL**: `https://openexchangerates.org/api`
- **Authentication**: App ID query parameter
- **Format**: JSON
- **Rate Limits**: 1,000 requests/month (free tier)

## Free Tier Limitations

- Hourly rate updates (not real-time)
- USD base currency only
- No historical data
- Limited to 1,000 API calls per month

## Paid Plans

### Unlimited Plan ($12/month)
- Minute-by-minute updates
- Any base currency
- Historical data back to 1999
- Unlimited API requests
- HTTPS support

### Enterprise Plan ($97/month)
- All Unlimited features
- Second-by-second updates
- OHLC candlestick data
- Priority support
- Dedicated account manager

## Supported Currencies

Over 200 currencies including:
- Major: USD, EUR, GBP, JPY, CHF, CAD, AUD
- Asian: CNY, INR, KRW, SGD, HKD, THB
- European: SEK, NOK, DKK, PLN, CZK
- Latin American: BRL, MXN, ARS, CLP
- Middle Eastern: SAR, AED, ILS
- African: ZAR, NGN, EGP
- And many more...

## API Documentation

- [Getting Started](https://docs.openexchangerates.org/docs/getting-started)
- [API Reference](https://docs.openexchangerates.org/reference/api-introduction)
- [Supported Currencies](https://docs.openexchangerates.org/reference/supported-currencies)
- [FAQ](https://openexchangerates.org/faq)

## Support

- **Email**: support@openexchangerates.org
- **Documentation**: https://docs.openexchangerates.org
- **Status Page**: https://status.openexchangerates.org
- **Twitter**: @OpenExchangeOrg

## Version History

See [CHANGELOG.md](CHANGELOG.md) for version history.

## License

This provider integration is provided by Spwig. Open Exchange Rates is a trademark of Open Exchange Rates Ltd.

## Provider Information

- **Provider Key**: `open_exchange_rates`
- **Version**: 1.0.0
- **Author**: Spwig
- **Maintained By**: Spwig Development Team
