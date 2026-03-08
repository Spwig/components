# Revolut Payment Provider

Accept online payments with Revolut's Merchant API. Support for cards, Revolut Pay, Apple Pay, Google Pay, and Pay by Bank across 30+ currencies.

## Features

- Card payments (Visa, Mastercard, Amex, Discover, Diners Club, JCB)
- Digital wallets (Apple Pay, Google Pay, Revolut Pay)
- Pay by Bank (Open Banking)
- Hosted checkout page
- Automatic and manual capture modes
- Full and partial refunds
- 3D Secure authentication
- Webhook support with HMAC-SHA256 verification
- Multi-currency processing (21 currencies)

## Requirements

- Python 3.10+
- `requests` library
- Revolut Business account with Merchant API access

## Configuration

### Required

- **Secret API Key**: Your Revolut Merchant API secret key
- **Environment**: Sandbox or Production

### Optional

- **Public API Key**: For Revolut Checkout Widget integration
- **Webhook Signing Secret**: For webhook signature verification
- **Capture Mode**: Automatic (default) or Manual

## API Usage

```python
from provider import RevolutProvider

provider = RevolutProvider(
    credentials={
        'secret_key': 'sk_live_...',
        'environment': 'production',
    }
)

# Test connection
result = provider.test_connection()

# Charge
result = provider.charge(
    amount=29.99,
    currency='GBP',
    payment_method={'type': 'card'},
    metadata={'order_id': 'ORD-123'}
)

# Refund
result = provider.refund(
    transaction_id='order-id',
    amount=10.00,
    reason='Customer request'
)
```

## Webhook Events

- `ORDER_COMPLETED` - Payment captured successfully
- `ORDER_AUTHORISED` - Payment authorised (manual capture mode)
- `ORDER_CANCELLED` - Order cancelled
- `ORDER_FAILED` - Payment failed
- `ORDER_PAYMENT_AUTHENTICATED` - 3DS authentication completed
- `ORDER_PAYMENT_DECLINED` - Payment declined
- `ORDER_PAYMENT_FAILED` - Payment attempt failed

## License

Proprietary - Spwig
