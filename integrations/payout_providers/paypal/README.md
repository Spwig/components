# PayPal Payouts Provider

PayPal Payouts API integration for processing affiliate commission payments.

## Features

- **Batch Payouts**: Send up to 15,000 payments in a single batch
- **Real-time Status**: Track payout status via webhooks
- **Multi-currency**: Support for 25+ currencies
- **Sandbox Testing**: Full sandbox environment support

## Supported Payout Methods

- PayPal (via recipient email address)

## Supported Currencies

USD, EUR, GBP, CAD, AUD, JPY, CNY, HKD, NZD, SGD, CHF, SEK, NOK, DKK, PLN, HUF, CZK, ILS, MXN, BRL, MYR, PHP, THB, TWD, RUB

## Requirements

- PayPal Business account
- Payouts feature enabled (may require PayPal approval)
- REST API credentials (Client ID and Secret)

## Fee Structure

PayPal charges 2% per payout with the following caps:
- USD: $20.00 max
- EUR: €18.00 max
- GBP: £15.00 max
- CAD/AUD: $25.00 max

## Webhook Events

Configure webhooks to receive real-time status updates:
- `PAYMENT.PAYOUTSBATCH.SUCCESS` - Batch completed successfully
- `PAYMENT.PAYOUTSBATCH.DENIED` - Batch was denied
- `PAYMENT.PAYOUTS-ITEM.SUCCEEDED` - Individual item completed
- `PAYMENT.PAYOUTS-ITEM.FAILED` - Individual item failed
- `PAYMENT.PAYOUTS-ITEM.UNCLAIMED` - Recipient hasn't claimed funds

## Documentation

- [PayPal Payouts API Docs](https://developer.paypal.com/docs/api/payments.payouts-batch/v1/)
- [PayPal Developer Dashboard](https://developer.paypal.com/)

## Version History

### 1.0.0
- Initial release
- Batch payout support
- Webhook integration
- Fee estimation
