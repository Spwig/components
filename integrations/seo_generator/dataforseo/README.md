# DataForSEO Provider

Professional SEO content generation powered by [DataForSEO](https://dataforseo.com)'s Content Generation API.

## Features

- Meta title generation via Content Generation API (~60 characters)
- Meta description generation via Content Generation API (~155 characters)
- Keyword extraction via text summary analysis
- Multi-language support (20+ languages)
- Pay-as-you-go pricing
- 2,000 requests/minute rate limit

## Requirements

- Python >= 3.10
- Django >= 4.2
- Spwig >= 2.0.0
- DataForSEO account with API access

## Setup

1. Install from the Spwig Marketplace
2. Create a DataForSEO account at https://app.dataforseo.com/register
3. Navigate to API Access in your dashboard
4. Copy your login email and API password
5. Enter credentials in the Spwig setup wizard

## Pricing

DataForSEO uses pay-as-you-go pricing:
- Content Generation: ~$0.002/request
- Text Summary: ~$0.0006/request
- No monthly minimums

## API Documentation

- [DataForSEO API v3](https://docs.dataforseo.com/v3)
- [Content Generation API](https://docs.dataforseo.com/v3/content_generation)

## Security

- API credentials encrypted at rest (Fernet AES-256)
- HTTP Basic Auth over HTTPS
- All API calls have explicit 30-second timeout

## Version

1.0.0 - Initial release
