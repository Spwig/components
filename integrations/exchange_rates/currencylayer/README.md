# Currencylayer Provider

Real-time currency exchange rates from the Currencylayer API (powered by APILayer).

## Features

- **168 Currencies**: Support for all major world currencies
- **Real-time Rates**: Hourly updates on free tier, minute-by-minute on Business plan
- **Simple Integration**: Single Access Key authentication
- **Reliable API**: Powered by APILayer infrastructure
- **Free Tier Available**: 100 requests per month at no cost

## Setup

1. Sign up at [apilayer.com](https://apilayer.com?fpr=spwig)
2. Get your Access Key from the Currencylayer dashboard
3. Enter credentials in the setup wizard
4. Test connection
5. Start syncing rates!

## API Information

- **Base URL**: `https://api.currencylayer.com/api`
- **Authentication**: Access Key query parameter
- **Format**: JSON
- **Rate Limits**: 100 requests/month (free tier)

## Free Tier Limitations

- Hourly rate updates (not real-time)
- USD base currency only
- No historical data
- Limited to 100 API calls per month
- No HTTPS (HTTP only)

## Paid Plans

### Basic Plan ($9.99/month)
- 5,000 API requests per month
- Live rates
- USD base currency only
- HTTPS support
- Email support

### Professional Plan ($49.99/month)
- 100,000 API requests per month
- Live rates with historical data
- Any base currency
- HTTPS support
- Priority support

### Business Plan ($149.99/month)
- 1,000,000 API requests per month
- All Professional features
- Minute-by-minute updates
- Currency conversion endpoint
- Time-frame queries
- Dedicated support

## Supported Currencies

168 currencies including:
- Major: USD, EUR, GBP, JPY, CHF, CAD, AUD
- Asian: CNY, INR, KRW, SGD, HKD, THB
- European: SEK, NOK, DKK, PLN, CZK
- Latin American: BRL, MXN, ARS, CLP
- Middle Eastern: SAR, AED, ILS
- African: ZAR, NGN, EGP
- And many more...

## API Documentation

- [Getting Started](https://currencylayer.com/documentation)
- [API Reference](https://currencylayer.com/documentation)
- [Supported Currencies](https://currencylayer.com/currencies)
- [FAQ](https://currencylayer.com/faq)

## Support

- **Email**: support@apilayer.com
- **Documentation**: https://currencylayer.com/documentation
- **Website**: https://currencylayer.com

## Version History

See [CHANGELOG.md](CHANGELOG.md) for version history.

## License

This provider integration is provided by Spwig. Currencylayer is a product of APILayer.

## Provider Information

- **Provider Key**: `currencylayer`
- **Version**: 1.0.0
- **Author**: Spwig
- **Maintained By**: Spwig Development Team
