# AI SEO Generator

AI-powered SEO content generation for your Spwig store, supporting both **Claude (Anthropic)** and **OpenAI (GPT)** models.

## Features

- Meta title generation with SEO best practices (~60 characters)
- Meta description generation with call-to-action (~155 characters)
- Intelligent keyword extraction with relevance ordering
- Multi-language support (generates native-language content, not translations)
- Single-call optimization (one AI call returns title + description + keywords)
- Content-type aware (product, category, brand, page, blog post)

## Supported AI Services

| Service | Models | Approximate Cost/Request |
|---------|--------|--------------------------|
| Claude (Anthropic) | Sonnet 4, Haiku 4 | $0.001 - $0.005 |
| OpenAI (GPT) | GPT-4o Mini, GPT-4o | $0.001 - $0.005 |

## Requirements

- Python >= 3.10
- Django >= 4.2
- Spwig >= 2.0.0
- An API key from Anthropic or OpenAI

## Setup

1. Install from the Spwig Marketplace
2. Navigate to SEO Generator > Provider Setup Wizard
3. Select your AI service (Claude or OpenAI)
4. Enter your API key and select a model
5. Test the connection and activate

## How It Works

The provider sends structured prompts to the selected AI service with your content details (name, description, category, brand, content type). The AI generates SEO-optimized titles, descriptions, and keywords following search engine best practices.

For efficiency, the `generate_seo()` method makes a single AI call that returns all three fields in one response, reducing API costs by ~66% compared to three separate calls.

## Security

- API keys are encrypted at rest using Fernet (AES-256)
- Keys are redacted in all log output
- All API calls use HTTPS with explicit timeouts
- No credentials are stored in the provider code

## Version

1.0.0 - Initial release
