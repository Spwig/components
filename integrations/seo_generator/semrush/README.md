# SEMrush SEO Provider

SEO content generation powered by [SEMrush](https://www.semrush.com)'s keyword intelligence API.

## Features

- Keyword research via SEMrush's Related Keywords API
- Keyword-optimized meta title generation with smart templates (~60 characters)
- Keyword-rich meta description generation with CTAs (~155 characters)
- 30+ regional database support
- Instance-level keyword caching for efficiency
- Content-type aware templates (product, category, brand, page, blog)

## How It Works

Unlike direct content generators, SEMrush provides **keyword intelligence**:

1. Fetches high-value keywords related to your content from SEMrush
2. Uses keyword-driven templates to build titles and descriptions
3. Places top keywords strategically for maximum SEO impact
4. Caches keyword data within sessions for efficiency

## Requirements

- Python >= 3.10
- Django >= 4.2
- Spwig >= 2.0.0
- SEMrush paid plan with API units

## Setup

1. Install from the Spwig Marketplace
2. Create a SEMrush account at https://www.semrush.com/signup
3. Find your API key in Subscription Info > API units
4. Select your target regional database
5. Enter credentials in the Spwig setup wizard

## Regional Databases

Select the database matching your target market: US, UK, Canada, Australia, Germany, France, Spain, Italy, Brazil, and 20+ more regions.

## Pricing

SEMrush uses unit-based pricing:
- 10,000 API units included by default
- Each keyword request consumes units
- Additional units can be purchased

## Security

- API key encrypted at rest (Fernet AES-256)
- All API calls over HTTPS with 30-second timeout
- Credentials redacted in all log output

## Version

1.0.0 - Initial release
