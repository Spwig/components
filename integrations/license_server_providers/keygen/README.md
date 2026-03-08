# Keygen.sh License Provider

**Version:** 1.0.0
**Author:** Spwig
**Type:** License Server Provider Component

## Overview

Keygen.sh is a popular third-party license management platform that provides policy-based licensing with comprehensive device tracking and analytics.

## Features

- ✅ **Policy-Based Licensing** - Flexible license terms and limitations
- ✅ **Device Tracking** - Monitor and manage device activations
- ✅ **Usage Analytics** - Track license usage and activations
- ✅ **Webhooks** - Real-time notifications for license events
- ✅ **Floating Licenses** - Concurrent user licensing support
- ✅ **Multi-Platform** - SDKs for Windows, macOS, Linux, and more
- ✅ **Sandbox Environment** - Test before going live
- ✅ **Comprehensive API** - Full REST API access

## Setup

1. Sign up at [keygen.sh](https://keygen.sh)
2. Create a product and policy in your Keygen dashboard
3. Generate a Product API Token (Settings → Tokens)
4. Get your Account ID from the dashboard URL
5. Use the Spwig wizard to connect Keygen
6. Map your Spwig products to Keygen policies

## Product Mapping

After connecting Keygen, you'll need to map your Spwig products to Keygen policies:

1. Go to the provider configuration
2. Add product mapping in the `provider_config` field:
```json
{
  "product_mapping": {
    "123": "policy_abc123...",
    "456": "policy_def456..."
  }
}
```

Where the keys are Spwig product IDs and values are Keygen policy IDs.

## API Endpoints

- **Base URL:** `https://api.keygen.sh/v1`
- **Create License:** `POST /accounts/{account_id}/licenses`
- **Validate License:** `POST /accounts/{account_id}/licenses/actions/validate-key`
- **Activate Machine:** `POST /accounts/{account_id}/machines`

## Pricing

### Free Tier
- 10 licenses
- Basic policy support
- Standard API access
- Community support

### Indie - $29/month
- 1,000 licenses
- All policy features
- Webhooks
- Email support

### Business - $99/month
- 10,000 licenses
- Priority support
- Advanced analytics

### Enterprise - Custom
- Unlimited licenses
- Dedicated support
- On-premise option

## Support

- **Documentation:** [keygen.sh/docs](https://keygen.sh/docs)
- **API Docs:** [keygen.sh/docs/api](https://keygen.sh/docs/api)
- **Support:** [keygen.sh/docs/support](https://keygen.sh/docs/support)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
