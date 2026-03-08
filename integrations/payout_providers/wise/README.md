# Wise Payout Provider

Send affiliate commission payouts via Wise (formerly TransferWise).

## Features

- Low-cost international transfers to 170+ countries
- Real mid-market exchange rates with no hidden markup
- Transparent, upfront fees
- Quote-based transfers
- Webhook notifications for transfer status updates
- Sandbox environment for testing

## Requirements

- Wise Business account with completed verification
- Two-factor authentication enabled
- API token with "Full access" permissions
- Sufficient balance in your sending currency

## Supported Currencies

Wise supports sending to 49 currencies including:
- Major: USD, EUR, GBP, AUD, CAD, JPY, CHF
- European: SEK, NOK, DKK, PLN, CZK, HUF, RON, BGN
- Asia-Pacific: SGD, HKD, INR, IDR, MYR, PHP, THB, VND, KRW, JPY
- Americas: MXN, BRL, ARS, CLP, COP
- Middle East/Africa: AED, ZAR, KES, NGN, EGP, MAD

## API Flow

1. **Create Quote** - Get exchange rate and fee estimate
2. **Create Recipient** - Set up the destination bank account
3. **Create Transfer** - Link quote and recipient
4. **Fund Transfer** - Pay from your Wise balance

## Fee Structure

- **Exchange rate**: Real mid-market rate (no markup)
- **Transfer fee**: Varies by corridor (typically 0.3% - 2%)
- **Fee transparency**: Exact fees shown before each transfer

## Webhook Events

- `transfers#state-change` - Transfer status updates
- `transfers#active-cases` - Issues requiring attention
- `balances#credit` - Balance credited

## Links

- [Wise Business](https://wise.com/business/)
- [API Documentation](https://docs.wise.com/api-docs/api-reference)
- [Pricing Calculator](https://wise.com/us/pricing/)
- [Sandbox Environment](https://sandbox.transferwise.tech)
