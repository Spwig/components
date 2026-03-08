# Twilio WhatsApp Provider

Send WhatsApp messages using Twilio's WhatsApp Business API.

## Features

- **WhatsApp Business API**: Official WhatsApp integration via Twilio
- **Template Messages**: Pre-approved templates for business-initiated conversations
- **Rich Media**: Send images, documents, and other media
- **Delivery Reports**: Real-time message status updates
- **Two-Way Messaging**: Receive and respond to customer messages

## Quick Start

1. Create or use existing Twilio account
2. Complete WhatsApp sender registration
3. Get Meta Business approval (for production)
4. Configure the provider with your credentials

## Credentials Required

| Field | Description |
|-------|-------------|
| Account SID | Your Twilio Account SID (starts with AC) |
| Auth Token | Your Twilio Auth Token |
| WhatsApp Number | Your WhatsApp-enabled phone number in E.164 format |

## WhatsApp Messaging Rules

### 24-Hour Window
- Free-form messages can only be sent within 24 hours of customer's last message
- Outside this window, you must use pre-approved templates

### Template Messages
- Required for business-initiated conversations
- Must be approved by Meta before use
- Typically approved within 24-48 hours

### Opt-in Required
- Customers must explicitly opt-in to receive WhatsApp messages
- Provide clear opt-out options

## Pricing

WhatsApp uses conversation-based pricing:
- **User-initiated (Service)**: Customer messages you first
- **Business-initiated (Marketing/Utility)**: You message first with templates

Example rates per conversation:
- North America: ~$0.0088 (user) / ~$0.0147 (business)
- UK/Western Europe: ~$0.0516 (user) / ~$0.0858 (business)

See [Twilio WhatsApp Pricing](https://www.twilio.com/whatsapp/pricing) for current rates.

## Setup Options

### Sandbox (Testing)
Quick setup for testing, but limited to phones that "join" the sandbox.

### Production
Full WhatsApp Business API access. Requires:
1. Meta Business Account verification
2. WhatsApp sender registration
3. Template approval

## Support

- [Twilio WhatsApp Documentation](https://www.twilio.com/docs/whatsapp)
- [Meta WhatsApp Business Platform](https://developers.facebook.com/docs/whatsapp/overview)
- [Twilio Support](https://support.twilio.com)

## Changelog

### v1.0.0 (2025-01-15)
- Initial release
- WhatsApp template message support
- Free-form message support (within 24hr window)
- Rich media support
- Delivery status webhooks
