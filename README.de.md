<p align="center">
  <a href="README.md">English</a> |
  <a href="README.fr.md">Français</a> |
  <a href="README.es.md">Español</a> |
  <strong>Deutsch</strong> |
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

<h1 align="center">Spwig-Komponenten</h1>

<p align="center">
  <strong>Themes, Admin-Werkzeuge und Anbieter-Integrationen für die Spwig-E-Commerce-Plattform.</strong>
</p>

<p align="center">
  <a href="https://spwig.com">Website</a> &nbsp;&bull;&nbsp;
  <a href="https://docs.spwig.com">Dokumentation</a> &nbsp;&bull;&nbsp;
  <a href="https://community.spwig.com">Community</a> &nbsp;&bull;&nbsp;
  <a href="https://spwig.com/en/demos">Live-Demos</a>
</p>

---

## Überblick

Dieses Repository ist die Open-Source-Komponentenbibliothek für [Spwig](https://spwig.com), eine selbstgehostete E-Commerce-Plattform. Es enthält drei Arten von Komponenten, die eine Spwig-Installation nutzen kann:

| | |
|--|--|
| **Themes** | Fertige Storefront-Designs |
| **Utilities** | Admin-UI-Helfer (Farbwähler, Verlaufseditor, Fokuspunkt-Wähler usw.) |
| **Integrationen** | Anbieter für Zahlungen, Versand, SMS, E-Mail, Übersetzung, SEO und soziale Netzwerke |

Jede Komponente wird über die Spwig-Administration installiert und aktualisiert – ohne Code – aber der Quellcode liegt hier, damit Sie ihn prüfen, dazu beitragen oder forken können.

---

## Was enthalten ist

### Themes (13)

| Theme | Stil |
|-------|------|
| **Default** | Sauber, professionell, vielseitig |
| **Apparel** | Mode- und Bekleidungsshops |
| **Artisan** | Handgefertigte Waren |
| **Bold** | Kontrastreich, ausdrucksstark |
| **Botanica** | Pflanzen, Garten, Naturprodukte |
| **Elegant Shop** | Premium, Luxus |
| **Modern Dark** | Dark-Mode-first-Design |
| **Modern Shop** | Zeitgemäßer allgemeiner Shop |
| **Nature** | Outdoor- und Nachhaltigkeitsmarken |
| **Space** | Tech, Gadgets, futuristisch |
| **Starter** | Minimaler Ausgangspunkt für eigene Themes |
| **Tech** | Elektronik und Hardware |
| **Vivid** | Lebendig, farbenfroh |

### Admin-Utilities (14)

Wiederverwendbare UI-Bausteine für die gesamte Spwig-Administration – darunter Farbwähler, Verlaufsgenerator, Fokuspunkt-Wähler, Schatten-Editor, Typografie-Editor, Hintergrund-Editor, Rahmen-Editor, Abstands-Editor, Icon-Wähler, Einheiten-Wähler, Sichtbarkeitsregel-Editor, Formular-Wähler, Übersetzungs-Editor und eine gemeinsame Utility-Basis.

### Integrationen (49+)

| Kategorie | Anbieter |
|-----------|----------|
| **Zahlungen** | Stripe, Adyen, PayPal Checkout, Airwallex, Revolut, Square |
| **Auszahlungen** | PayPal, Airwallex Payouts, Wise |
| **Versand** | FedEx, UPS, USPS, Canada Post, Australia Post, NinjaVan |
| **Terminals** | Stripe Terminal, Square Terminal, Adyen Terminal, Revolut Terminal, SumUp, Zettle |
| **E-Mail** | Gmail API, SMTP (Gmail / Outlook / SendGrid / SES / beliebig) |
| **SMS** | Twilio, Twilio WhatsApp |
| **Wechselkurse** | Fixer, currencylayer, XE, Open Exchange Rates, exchangerate-api, exchangeratesapi |
| **Übersetzung** | DeepL, AWS Translate, Azure Translator, Google Translate, Generische API |
| **SEO** | Semrush, DataForSEO, AI SEO |
| **Soziale Netzwerke** | Facebook Pages, Instagram Business, LinkedIn Company, Twitter |
| **Produkt-Feeds** | Google Merchant Center |
| **Lizenzserver** | Cryptlex, LicenseSpring, Keygen, Custom API, Spwig integriert |

---

## Installation

### Über die Spwig-Administration (empfohlen)

Komponenten werden mit einem Klick über die Administration Ihres Spwig-Shops installiert:

**Admin → Marketplace → Komponenten**

Der Marketplace zeigt alle Komponenten aus diesem Repository sowie Premium- und Drittanbieter-Komponenten. Klicken Sie auf **Installieren**, und Spwig lädt die Komponente herunter, integriert sie in Ihre Website und wendet alle erforderlichen Migrationen an.

### Manuelle Installation

Wenn Sie eine angepasste Spwig-Konfiguration ausführen oder offline entwickeln, können Sie Komponenten manuell installieren:

```bash
git clone https://github.com/Spwig/components.git
cp -r components/themes/botanica /path/to/spwig/media/components/themes/
```

Führen Sie dann in der Spwig-Administration **Marketplace → Lokale Komponenten neu scannen** aus.

---

## Eigene Komponenten entwickeln

Möchten Sie ein neues Theme, Utility oder eine Integration entwickeln? Beginnen Sie mit einem unserer SDKs – jedes ist ein kleines, gut dokumentiertes Framework mit einem Beispielanbieter zum Forken:

| SDK | Zum Erstellen |
|-----|---------------|
| [`theme-sdk`](https://github.com/Spwig/theme-sdk) | Themes mit Tokens, kritischem CSS und Page-Builder-Unterstützung |
| [`provider-sdks`](https://github.com/Spwig/provider-sdks) | Integrationen für Zahlungen, Versand, SMS, E-Mail und andere Anbieter |
| [`headless-sdk`](https://github.com/Spwig/headless-sdk) | Headless-Storefronts, die die Spwig-API nutzen |
| [`react`](https://github.com/Spwig/react) | React-Hooks und -Komponenten für Headless-Storefronts |

Jede Komponente in diesem Repository folgt demselben Manifestformat (`manifest.json`), damit sie vom Spwig-Marketplace erkannt wird.

---

## Beitragen

Beiträge sind willkommen. Um es einfach zu halten, verwenden wir das **Developer Certificate of Origin (DCO)** anstelle eines CLA – fügen Sie einfach eine Sign-off-Zeile zu Ihren Commits hinzu:

```bash
git commit -s -m "Add support for X"
```

Details zum Einreichen eines PR, zum Manifestformat und zu Coding-Konventionen finden Sie in [CONTRIBUTING.md](CONTRIBUTING.md).

**Ideen für Beiträge:**

- Neue Themes für unterversorgte Branchen (Essen & Trinken, Gesundheit, Bildung, Immobilien)
- Zusätzliche Zahlungs- oder Versandanbieter nach Region
- Bugfixes und Verbesserungen an bestehenden Komponenten
- Übersetzungen des README und der Setup-Anleitungen der Komponenten

---

## Lizenz

**AGPL-3.0** – siehe [LICENSE](LICENSE). Sie können diesen Code für selbstgehostete Shops frei nutzen, modifizieren und weitergeben. Wenn Sie eine modifizierte Version als Netzwerkdienst ausführen, müssen Sie Ihre Änderungen unter derselben Lizenz für Ihre Nutzer zugänglich machen.

Für Bedingungen, die für proprietäre oder SaaS-Nutzung geeignet sind, kontaktieren Sie [licensing@spwig.com](mailto:licensing@spwig.com).

---

## Support

- **Dokumentation**: [docs.spwig.com](https://docs.spwig.com)
- **Community-Forum**: [community.spwig.com](https://community.spwig.com)
- **E-Mail**: support@spwig.com
- **Issues**: [github.com/Spwig/components/issues](https://github.com/Spwig/components/issues)

---

<p align="center">
  <sub>Erstellt von <a href="https://spwig.com">Spwig</a> und Mitwirkenden</sub>
</p>
