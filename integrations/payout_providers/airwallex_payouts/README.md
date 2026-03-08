# Airwallex Transfers Provider

Airwallex Transfers API integration for processing affiliate commission payments via bank transfer.

## Features

- **Global Coverage**: Send payments to 200+ countries
- **Multi-currency**: Support for 40+ currencies
- **Transfer Methods**: LOCAL (fast, low-fee) and SWIFT options
- **Real-time Status**: Track transfers via webhooks
- **Demo Environment**: Full sandbox for testing

## Supported Payout Methods

- Bank Transfer (automatic routing)
- Local Bank Transfer (domestic ACH, Faster Payments, etc.)
- SWIFT Bank Transfer (international wire)

## Supported Currencies

USD, EUR, GBP, AUD, CAD, SGD, HKD, CNY, JPY, NZD, CHF, SEK, NOK, DKK, PLN, CZK, HUF, RON, BGN, HRK, TRY, ZAR, MXN, BRL, INR, IDR, MYR, PHP, THB, VND, KRW, TWD, ILS, AED, SAR, QAR, KWD, BHD, OMR

## Requirements

- Airwallex Business account (requires KYB verification)
- API credentials (Client ID and API Key)
- Funded Airwallex wallet

## Fee Structure

Fees vary by transfer method and corridor:

**Local Transfers:**
- Often free or low-cost for major currencies
- USD domestic: $0
- EUR/GBP: ~$0.50
- Others: ~$2.00

**SWIFT Transfers:**
- Approximately $15.00 per transfer
- Additional correspondent bank fees may apply

## Transfer Times

**Local Transfers:**
- AU, GB, SG, HK: Instant to 1 business day
- US, CA, EU: Same day to 1 business day
- Others: 1-2 business days

**SWIFT Transfers:**
- 3-5 business days globally

## Webhook Events

Configure webhooks to receive real-time status updates:
- `transfer.ready_for_funding` - Transfer awaiting funding
- `transfer.batch_confirmed` - Batch transfer confirmed
- `transfer.completed` - Transfer completed successfully
- `transfer.failed` - Transfer failed
- `transfer.returned` - Transfer returned to sender

## Documentation

- [Airwallex Transfers API](https://www.airwallex.com/docs/payouts__create-a-transfer)
- [Airwallex Dashboard](https://www.airwallex.com/app/)

## Version History

### 1.0.0
- Initial release
- LOCAL and SWIFT transfer support
- Webhook integration
- Fee estimation
- Beneficiary management
