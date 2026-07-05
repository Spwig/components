# AirWallex Payment Provider

Global payment processing with 160+ payment methods across 130+ countries.

## Features

- **Global Coverage**: Process payments in 130+ countries with 160+ local payment methods
- **Multi-Currency**: Support for USD, EUR, GBP, and 10+ major currencies
- **Competitive FX Rates**: Save on international transactions with competitive exchange rates
- **Full Payment Lifecycle**: Authorization, capture, refunds (full & partial)
- **Real-Time Notifications**: Webhook integration for instant payment updates
- **3D Secure**: Built-in support for secure card authentication
- **Recurring Payments**: Support for subscription and recurring billing

## Requirements

- Python 3.8+
- `requests` library (automatically installed)

## Configuration

### Required Fields

- **Client ID**: Your AirWallex Client ID from Developer settings
- **API Key**: Your AirWallex API Key (keep this secret!)
- **Environment**: Choose `demo` for testing or `production` for live transactions

### Optional Fields

- **Webhook Secret**: For webhook signature verification (recommended)
- **Auto Capture**: Automatically capture authorized payments (default: true)
- **Payment Descriptor**: Text shown on customer's bank statement (max 22 chars)

## Getting Started

### 1. Create AirWallex Account

Visit [www.airwallex.com](https://www.airwallex.com) and sign up for a business account.

### 2. Get API Credentials

1. Log into your AirWallex Dashboard
2. Navigate to **Settings → Developer → API Keys**
3. Copy your **Client ID**
4. Create a new **API Key** with appropriate permissions
5. Save these credentials securely

### 3. Configure Webhook (Recommended)

1. Go to **Developer → Webhooks** in your dashboard
2. Add your webhook URL: `https://yourdomain.com/webhooks/payments/airwallex/`
3. Select events: `payment_intent.*` and `refund.*`
4. Enable signing secret and copy the secret key

### 4. Test Your Integration

Use AirWallex's test cards in Demo/Sandbox mode:
- **Success**: 4012 0000 3333 0026
- **3D Secure**: 4000 0027 6000 3184
- **Declined**: 4000 0000 0000 0002

## API Usage

### Initialize Provider

```python
from provider import AirWallexProvider

config = {
    'client_id': 'your_client_id',
    'api_key': 'your_api_key',
    'environment': 'demo',  # or 'production'
    'webhook_secret': 'your_webhook_secret',  # optional
    'auto_capture': True
}

provider = AirWallexProvider(config)
```

### Create Payment

```python
result = provider.create_payment(
    amount=Decimal('100.00'),
    currency='USD',
    order_id='order_12345',
    customer_email='customer@example.com',
    description='Order Payment'
)

if result['success']:
    payment_intent_id = result['payment_intent_id']
    client_secret = result['client_secret']
    # Use client_secret on frontend to complete payment
```

### Capture Payment

```python
result = provider.capture_payment(payment_intent_id)

if result['success']:
    print(f"Payment captured: {result['status']}")
```

### Process Refund

```python
# Full refund
result = provider.refund_payment(payment_intent_id)

# Partial refund
result = provider.refund_payment(
    payment_intent_id,
    amount=Decimal('50.00'),
    reason='Customer request'
)
```

### Handle Webhooks

```python
# Verify webhook signature
is_valid = provider.verify_webhook(
    payload=request.body,
    timestamp=request.headers.get('x-timestamp'),
    signature=request.headers.get('x-signature')
)

if is_valid:
    event_data = json.loads(request.body)
    result = provider.process_webhook(event_data)

    if result['event_type'] == 'payment.succeeded':
        # Update order status
        order_id = result['merchant_order_id']
        # Mark order as paid
```

## Webhook Events

The provider handles the following webhook events:

- `payment_intent.succeeded` → Payment completed successfully
- `payment_intent.failed` → Payment failed
- `payment_intent.requires_capture` → Payment authorized, awaiting capture
- `refund.received` → Refund request received
- `refund.accepted` → Refund accepted by payment provider
- `refund.settled` → Refund completed
- `refund.failed` → Refund failed

## Testing

Run the test suite:

```bash
cd tests
python -m unittest test_provider.py
```

## Support

- **AirWallex Documentation**: https://www.airwallex.com/docs
- **API Reference**: https://www.airwallex.com/docs/api
- **Developer Tools**: https://www.airwallex.com/docs/developer-tools
- **Contact Support**: Through your AirWallex dashboard

## Partnership Benefits

This platform has a partnership agreement with AirWallex, providing:
- Competitive transaction rates
- Priority support
- Revenue sharing benefits
- Faster onboarding

## License

Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0.

This component is part of the Spwig eCommerce Platform and is provided for use with the platform only.
