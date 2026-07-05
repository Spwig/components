<p align="center">
  <strong>English</strong> |
  <a href="README.fr.md">Français</a> |
  <a href="README.es.md">Español</a> |
  <a href="README.de.md">Deutsch</a> |
  <a href="README.ja.md">日本語</a> |
  <a href="README.zh-Hans.md">简体中文</a> |
  <a href="README.zh-Hant.md">繁體中文</a> |
  <a href="README.pt.md">Português</a> |
  <a href="README.ru.md">Русский</a> |
  <a href="README.ar.md">العربية</a> |
  <a href="README.hi.md">हिन्दी</a> |
  <a href="README.id.md">Bahasa Indonesia</a> |
  <a href="README.it.md">Italiano</a> |
  <a href="README.ko.md">한국어</a> |
  <a href="README.tr.md">Türkçe</a> |
  <a href="README.vi.md">Tiếng Việt</a> |
  <a href="README.th.md">ไทย</a>
</p>

<p align="center">
  <img src="https://spwig.com/images/logo.svg" alt="Spwig" width="200">
</p>

<h1 align="center">Spwig Components</h1>

<p align="center">
  <strong>Themes, admin utilities, and provider integrations for the Spwig e-commerce platform.</strong>
</p>

<p align="center">
  <a href="https://spwig.com">Website</a> &nbsp;&bull;&nbsp;
  <a href="https://docs.spwig.com">Documentation</a> &nbsp;&bull;&nbsp;
  <a href="https://community.spwig.com">Community</a> &nbsp;&bull;&nbsp;
  <a href="https://spwig.com/en/demos">Live Demos</a>
</p>

---

## Overview

This repository is the open-source component library for [Spwig](https://spwig.com), a self-hosted e-commerce platform. It contains three kinds of components that a Spwig installation can use:

| | |
|--|--|
| **Themes** | Ready-to-use storefront designs |
| **Utilities** | Admin UI helpers (color picker, gradient editor, focal point picker, etc.) |
| **Integrations** | Payment, shipping, SMS, email, translation, SEO, and social providers |

Every component is designed to be installed and updated through the Spwig admin — no code required — but the source lives here so you can inspect it, contribute, or fork.

---

## What's Included

### Themes (13)

| Theme | Style |
|-------|-------|
| **Default** | Clean, professional, versatile |
| **Apparel** | Fashion and clothing stores |
| **Artisan** | Handcrafted goods |
| **Bold** | High-contrast, statement-making |
| **Botanica** | Plants, garden, natural products |
| **Elegant Shop** | Premium, luxury |
| **Modern Dark** | Dark-mode-first design |
| **Modern Shop** | Contemporary general store |
| **Nature** | Outdoor, sustainable brands |
| **Space** | Tech, gadgets, futuristic |
| **Starter** | Minimal starting point for custom themes |
| **Tech** | Electronics and hardware |
| **Vivid** | Vibrant, colorful |

### Admin Utilities (14)

Reusable UI pieces used across the Spwig admin interface — including a color picker, gradient creator, focal-point selector, shadow editor, typography editor, background editor, border editor, spacing editor, icon picker, unit selector, visibility rules editor, form selector, translation editor, and a shared utility base.

### Integrations (49+)

| Category | Providers |
|----------|-----------|
| **Payments** | Stripe, Adyen, PayPal Checkout, Airwallex, Revolut, Square |
| **Payouts** | PayPal, Airwallex Payouts, Wise |
| **Shipping** | FedEx, UPS, USPS, Canada Post, Australia Post, NinjaVan |
| **Terminals** | Stripe Terminal, Square Terminal, Adyen Terminal, Revolut Terminal, SumUp, Zettle |
| **Email** | Gmail API, SMTP (Gmail / Outlook / SendGrid / SES / any) |
| **SMS** | Twilio, Twilio WhatsApp |
| **Exchange Rates** | Fixer, currencylayer, XE, Open Exchange Rates, exchangerate-api, exchangeratesapi |
| **Translation** | DeepL, AWS Translate, Azure Translator, Google Translate, Generic API |
| **SEO** | Semrush, DataForSEO, AI SEO |
| **Social** | Facebook Pages, Instagram Business, LinkedIn Company, Twitter |
| **Product Feeds** | Google Merchant Center |
| **License Servers** | Cryptlex, LicenseSpring, Keygen, Custom API, Spwig Built-in |

---

## Installation

### Through the Spwig admin (recommended)

Components install with a click from your Spwig store's admin:

**Admin → Marketplace → Components**

The marketplace shows every component in this repository, plus premium and third-party ones. Click **Install**, and Spwig fetches the component, wires it into your site, and applies any required migrations.

### Manual installation

If you're running a customised Spwig setup or developing offline, you can install components manually:

```bash
git clone https://github.com/Spwig/components.git
cp -r components/themes/botanica /path/to/spwig/media/components/themes/
```

Then, in the Spwig admin, run **Marketplace → Rescan Local Components**.

---

## Developing Your Own Component

Building a new theme, utility, or integration? Start with one of our SDKs — each is a small, well-documented framework with an example provider you can fork:

| SDK | For building |
|-----|--------------|
| [`theme-sdk`](https://github.com/Spwig/theme-sdk) | Themes with tokens, critical CSS, and page-builder support |
| [`provider-sdks`](https://github.com/Spwig/provider-sdks) | Payment, shipping, SMS, email, and other provider integrations |
| [`headless-sdk`](https://github.com/Spwig/headless-sdk) | Headless storefronts calling the Spwig API |
| [`react`](https://github.com/Spwig/react) | React hooks and components for headless storefronts |

Every component in this repository follows the same manifest format (`manifest.json`) so it can be discovered by the Spwig marketplace.

---

## Contributing

Contributions are welcome. To keep things simple we use the **Developer Certificate of Origin (DCO)** instead of a CLA — just add a sign-off line to your commits:

```bash
git commit -s -m "Add support for X"
```

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to submit a PR, the manifest format, and coding conventions.

**Ideas for contribution:**

- New themes for underserved verticals (food & drink, health, education, real estate)
- Additional payment or shipping providers by region
- Bug fixes and improvements to existing components
- Translations of the README and component setup instructions

---

## License

**AGPL-3.0** — see [LICENSE](LICENSE). You can use, modify, and distribute this code freely for self-hosted stores. If you run a modified version as a network service, you must make your changes available to your users under the same license.

For terms that suit a proprietary or SaaS use case, contact [licensing@spwig.com](mailto:licensing@spwig.com).

---

## Support

- **Documentation**: [docs.spwig.com](https://docs.spwig.com)
- **Community Forum**: [community.spwig.com](https://community.spwig.com)
- **Email**: support@spwig.com
- **Issues**: [github.com/Spwig/components/issues](https://github.com/Spwig/components/issues)

---

<p align="center">
  <sub>Built by <a href="https://spwig.com">Spwig</a> and contributors</sub>
</p>
