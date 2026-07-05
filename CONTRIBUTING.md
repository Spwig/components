# Contributing to Spwig Components

Thanks for wanting to contribute. This repository is the open-source component library for the [Spwig](https://spwig.com) e-commerce platform — themes, admin utilities, and provider integrations. Every contribution, from a typo fix to a new payment provider, is welcome.

## TL;DR

1. Fork the repo and create a branch from `main`
2. Make your change
3. Commit with **`git commit -s`** (the `-s` adds the DCO sign-off line — required)
4. Push and open a pull request against `Spwig/components:main`

That's it. Details below.

---

## Ways to contribute

- **Report a bug** — open an [issue](https://github.com/Spwig/components/issues) with reproduction steps and expected vs. actual behaviour
- **Fix a bug** — pick an issue labelled `good first issue` or `help wanted` and submit a PR
- **Build a new theme** — see [Building a theme](#building-a-theme) below
- **Build a new provider integration** — see [Building a provider integration](#building-a-provider-integration) below
- **Improve an existing component** — bug fixes, performance, accessibility, RTL support, dark-mode polish, etc.
- **Translate a README or a component's setup instructions** — translations lower the barrier for merchants worldwide

---

## Developer Certificate of Origin (DCO)

We use the [Developer Certificate of Origin](https://developercertificate.org/) instead of a Contributor License Agreement. This is a lightweight statement that you have the right to submit your contribution under this project's licence (AGPL-3.0).

To sign off, add `-s` to every commit:

```bash
git commit -s -m "Add support for X"
```

This appends a line like:

```
Signed-off-by: Your Name <your.email@example.com>
```

The sign-off must match your git `user.name` and `user.email`. If you forget on a commit, you can amend the last commit with `git commit --amend --signoff`, or rebase and add sign-offs across a branch with `git rebase --signoff HEAD~N`.

CI blocks PRs without a sign-off on every commit.

---

## Repository layout

```
spwig-components/
├── integrations/       # Provider integrations (payments, shipping, SMS, ...)
│   ├── payments/
│   │   ├── stripe/
│   │   │   ├── manifest.json
│   │   │   ├── provider.py
│   │   │   ├── setup_instructions.html
│   │   │   └── ...
│   │   └── ...
│   ├── shipping/
│   └── ...
├── themes/             # Storefront themes
│   ├── botanica/
│   │   ├── manifest.json
│   │   ├── tokens.json
│   │   ├── css/
│   │   └── ...
│   └── ...
└── utilities/          # Admin UI helpers (color picker, gradient creator, ...)
    ├── color_picker/
    │   ├── manifest.json
    │   ├── color_picker.js
    │   ├── color_picker.css
    │   └── ...
    └── ...
```

Every component is a self-contained directory with a `manifest.json` describing it. The Spwig admin marketplace uses this manifest to discover, install, and manage components.

---

## Manifest format

Every component has a `manifest.json` at its root. Minimum fields:

```json
{
  "component_type": "payment_provider",
  "slug": "my-provider",
  "name": "My Provider",
  "version": "1.0.0",
  "description": "A one-line description of what this component does.",
  "author": "Your Name or Company",
  "license": "AGPL-3.0",
  "min_platform_version": "1.0.0"
}
```

`component_type` must be one of:

- `theme`
- `utility`
- `payment_provider`, `payout_provider`
- `shipping_provider`, `terminal_provider`
- `email_provider`, `sms_provider`
- `translation_provider`, `seo_generator_provider`
- `exchange_rate_provider`
- `social_connector`
- `product_feed_provider`
- `license_server_provider`

Look at any existing component in this repo as a working example. `integrations/payments/stripe/manifest.json` and `themes/default/manifest.json` are good starting points.

---

## Building a theme

The [`theme-sdk`](https://github.com/Spwig/theme-sdk) is the framework. Every theme in this repo follows the SDK's v2.0 format.

Quick pattern:

1. Copy `themes/starter/` as your starting point
2. Rename the directory and update `manifest.json` (slug, name, description)
3. Edit `tokens.json` to define your colour palette, spacing scale, typography, etc.
4. Regenerate CSS from tokens (Spwig ships a management command for this on the platform side)
5. Customise `css/theme.css` and the critical CSS files as needed
6. Add a `preview.png` (1200×800 recommended) so the marketplace can show your theme

See the [`theme-sdk` docs](https://github.com/Spwig/theme-sdk#readme) for full details.

---

## Building a provider integration

The [`provider-sdks`](https://github.com/Spwig/provider-sdks) repo hosts one SDK per provider type, each with a working example provider you can fork.

Quick pattern:

1. Pick the relevant SDK (e.g. `payment_provider_sdk` for a new payment provider)
2. Copy its `example_*_provider/` directory into this repo under the right category
3. Rename and update `manifest.json`
4. Implement the required interface in `provider.py`
5. Update `setup_instructions.html` to explain how a merchant configures the provider
6. Add tests under a `tests/` directory
7. Add a `logo.svg` (SVG preferred, PNG acceptable)

Provider tests should not hit real APIs — use mocks or sandbox mode.

---

## Submitting a pull request

1. **Fork** and clone: `git clone git@github.com:YOUR_USER/components.git`
2. **Branch** from `main`: `git checkout -b add-provider-example`
3. **Make your changes** — one logical change per PR when practical
4. **Test** — run any relevant tests. For themes, load them in a dev Spwig install and check every page type (home, collection, product, cart, checkout)
5. **Commit with sign-off**: `git commit -s -m "Add example provider integration"`
6. **Push** to your fork: `git push origin add-provider-example`
7. **Open a PR** against `Spwig/components:main`. Describe:
   - What the change does
   - Why (link to an issue if there is one)
   - How you tested it
   - Screenshots for visual changes

A maintainer will review, may suggest changes, and merge when ready.

---

## Code style

- **Python**: Follow PEP 8. Provider code should target Python 3.10+.
- **JavaScript**: ES2020+, no build step required for utility JS. Use vanilla DOM APIs; no framework dependency for utilities.
- **CSS**: Prefer CSS custom properties (design tokens) over hardcoded values. Support RTL where the component may render in Arabic/Hebrew stores.
- **Manifest JSON**: 2-space indentation. Keep the file human-readable.
- **File headers**: New source files should carry `/* Copyright (c) 2025-2026 Spwig contributors. Licensed under AGPL-3.0. */` (or the language-appropriate comment syntax).

---

## Translations

Translations of the README are in `README.<locale>.md` — 16 locales are supported today. To add or improve a translation:

- Copy `README.md` to `README.<locale>.md`
- Translate the prose; leave code blocks, URLs, and product names unchanged
- Update the language switcher at the top of the file so your locale appears as `<strong>` (rather than a link) in the file you translated
- Open a PR — native-speaker review is strongly appreciated

For component-level translations (setup instructions, error messages), each component has its own conventions — check the component's directory for existing translation files.

---

## Getting help

- **Community forum**: [community.spwig.com](https://community.spwig.com) — best place for open-ended discussion
- **Documentation**: [docs.spwig.com](https://docs.spwig.com)
- **Issues**: [github.com/Spwig/components/issues](https://github.com/Spwig/components/issues) — bug reports and feature requests
- **Email**: support@spwig.com

Please don't email maintainers directly for issues that could be discussed publicly — a public thread lets others find the answer later.

---

## Licence

By contributing to this repository, you agree that your contribution will be licensed under the [AGPL-3.0](LICENSE) licence, the same licence as this project.
