# Twilio SMS Provider

Send SMS messages worldwide using Twilio's reliable global network.

## Features

- **Global SMS Delivery**: Send messages to 180+ countries
- **High Reliability**: 99.95% API uptime SLA
- **Delivery Reports**: Real-time delivery status updates
- **Unicode Support**: Send messages in any language
- **MMS Support**: Send images and media (US/Canada)

## Quick Start

1. Create a Twilio account at [twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. Get your Account SID and Auth Token from the Console
3. Purchase a phone number with SMS capability
4. Configure the provider with your credentials

## Credentials Required

| Field | Description |
|-------|-------------|
| Account SID | Your Twilio Account SID (starts with AC) |
| Auth Token | Your Twilio Auth Token |
| Phone Number | Your Twilio phone number in E.164 format |

## Pricing

Twilio uses pay-as-you-go pricing. Example rates:

- USA: $0.0079/message
- UK: $0.0420/message
- Canada: $0.0075/message

See [Twilio SMS Pricing](https://www.twilio.com/sms/pricing) for current rates.

## Free Trial

New accounts receive $15 in trial credit. Trial limitations:
- Can only send to verified phone numbers
- Messages include "Sent from Twilio trial account" prefix

Upgrade to a paid account to remove these limitations.

## Support

- [Twilio Documentation](https://www.twilio.com/docs/sms)
- [Twilio Support](https://support.twilio.com)
- [API Status](https://status.twilio.com)

## Changelog

### v1.0.0 (2025-01-15)
- Initial release
- SMS sending support
- MMS support
- Delivery status webhooks
- Connection testing
