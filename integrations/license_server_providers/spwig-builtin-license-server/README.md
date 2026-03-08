# Spwig Built-in License Server

**Version:** 1.0.0
**Author:** Spwig
**Type:** License Server Provider Component

## Overview

The Spwig Built-in License Server is a fully managed license management solution provided by Spwig. It offers the easiest integration with your Spwig shop, requiring no external setup or maintenance.

## Features

- ✅ **Fully Managed** - No server setup, maintenance, or scaling required
- ✅ **Automatic Sync** - Licenses sync automatically when orders are placed
- ✅ **Device Management** - Track and manage device activations
- ✅ **Offline Validation** - Generate validation tokens for offline use
- ✅ **Analytics** - Built-in reporting and usage tracking
- ✅ **Webhooks** - Real-time notifications for license events
- ✅ **Floating Licenses** - Support for concurrent user licensing
- ✅ **Trial Licenses** - Time-limited trial support
- ✅ **99.9% Uptime SLA** - Enterprise-grade reliability

## Setup

1. Sign up for a Spwig License Server account at [licenses.spwig.com](https://licenses.spwig.com)
2. Obtain your Account ID and API Key from the dashboard
3. Use the Spwig admin wizard to connect your license server
4. Start syncing licenses automatically!

## API Endpoints

- **Base URL:** `https://licenses.spwig.com/api/v1`
- **Create License:** `POST /licenses/`
- **Validate License:** `GET /licenses/{key}/validate/`
- **Activate Device:** `POST /licenses/{key}/activate/`
- **Deactivate Device:** `POST /licenses/{key}/deactivate/`
- **Suspend License:** `PUT /licenses/{key}/suspend/`
- **Revoke License:** `PUT /licenses/{key}/revoke/`

## Pricing

### Free Tier
- 100 active licenses
- Basic analytics
- Standard support
- 99.5% uptime SLA

### Professional - $29/month
- 1,000 active licenses
- Advanced analytics
- Priority support
- 99.9% uptime SLA
- Custom branding

### Enterprise - $99/month
- 10,000 active licenses
- Premium analytics
- Dedicated support
- 99.95% uptime SLA
- Custom branding
- Custom integrations
- White-label option

### Custom
- Unlimited licenses
- Contact sales for pricing
- On-premise options available

## Support

- **Documentation:** [licenses.spwig.com/docs](https://licenses.spwig.com/docs)
- **Support:** [spwig.com/support](https://spwig.com/support)
- **Email:** support@spwig.com

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
