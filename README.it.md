<p align="center">
  <a href="README.md">English</a> |
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
  <strong>Italiano</strong> |
  <a href="README.ko.md">한국어</a> |
  <a href="README.tr.md">Türkçe</a> |
  <a href="README.vi.md">Tiếng Việt</a> |
  <a href="README.th.md">ไทย</a>
</p>

<p align="center">
  <img src="https://spwig.com/images/logo.svg" alt="Spwig" width="200">
</p>

<h1 align="center">Componenti Spwig</h1>

<p align="center">
  <strong>Temi, utilità di amministrazione e integrazioni di provider per la piattaforma e-commerce Spwig.</strong>
</p>

<p align="center">
  <a href="https://spwig.com">Sito web</a> &nbsp;&bull;&nbsp;
  <a href="https://docs.spwig.com">Documentazione</a> &nbsp;&bull;&nbsp;
  <a href="https://community.spwig.com">Community</a> &nbsp;&bull;&nbsp;
  <a href="https://spwig.com/en/demos">Demo dal vivo</a>
</p>

---

## Panoramica

Questo repository è la libreria di componenti open source di [Spwig](https://spwig.com), una piattaforma e-commerce self-hosted. Contiene tre tipi di componenti che un'installazione Spwig può utilizzare:

| | |
|--|--|
| **Temi** | Design pronti all'uso per il negozio |
| **Utilità** | Aiuti per l'interfaccia di amministrazione (selettore di colori, editor di gradienti, selettore del punto focale, ecc.) |
| **Integrazioni** | Provider di pagamento, spedizione, SMS, email, traduzione, SEO e social |

Ogni componente è progettato per essere installato e aggiornato tramite l'amministrazione Spwig — senza codice — ma il codice sorgente vive qui in modo che tu possa ispezionarlo, contribuire o fare un fork.

---

## Cosa è incluso

### Temi (13)

| Tema | Stile |
|------|-------|
| **Default** | Pulito, professionale, versatile |
| **Apparel** | Negozi di moda e abbigliamento |
| **Artisan** | Prodotti artigianali |
| **Bold** | Alto contrasto, d'impatto |
| **Botanica** | Piante, giardino, prodotti naturali |
| **Elegant Shop** | Premium, lusso |
| **Modern Dark** | Design pensato per la modalità scura |
| **Modern Shop** | Negozio generale contemporaneo |
| **Nature** | Marchi outdoor e sostenibili |
| **Space** | Tech, gadget, futuristico |
| **Starter** | Punto di partenza minimale per temi personalizzati |
| **Tech** | Elettronica e hardware |
| **Vivid** | Vivace, colorato |

### Utilità di amministrazione (14)

Elementi di interfaccia riutilizzabili in tutta l'amministrazione Spwig — inclusi selettore di colori, creatore di gradienti, selettore del punto focale, editor di ombre, editor di tipografia, editor di sfondo, editor di bordi, editor di spaziatura, selettore di icone, selettore di unità, editor di regole di visibilità, selettore di moduli, editor di traduzioni e una base condivisa di utilità.

### Integrazioni (49+)

| Categoria | Provider |
|-----------|----------|
| **Pagamenti** | Stripe, Adyen, PayPal Checkout, Airwallex, Revolut, Square |
| **Pagamenti in uscita** | PayPal, Airwallex Payouts, Wise |
| **Spedizioni** | FedEx, UPS, USPS, Canada Post, Australia Post, NinjaVan |
| **Terminali** | Stripe Terminal, Square Terminal, Adyen Terminal, Revolut Terminal, SumUp, Zettle |
| **Email** | Gmail API, SMTP (Gmail / Outlook / SendGrid / SES / qualsiasi) |
| **SMS** | Twilio, Twilio WhatsApp |
| **Tassi di cambio** | Fixer, currencylayer, XE, Open Exchange Rates, exchangerate-api, exchangeratesapi |
| **Traduzione** | DeepL, AWS Translate, Azure Translator, Google Translate, API generica |
| **SEO** | Semrush, DataForSEO, AI SEO |
| **Social** | Facebook Pages, Instagram Business, LinkedIn Company, Twitter |
| **Feed prodotti** | Google Merchant Center |
| **Server di licenza** | Cryptlex, LicenseSpring, Keygen, API personalizzata, Spwig integrato |

---

## Installazione

### Tramite l'amministrazione Spwig (consigliato)

I componenti si installano con un clic dall'amministrazione del tuo negozio Spwig:

**Admin → Marketplace → Componenti**

Il marketplace mostra tutti i componenti di questo repository, oltre a quelli premium e di terze parti. Fai clic su **Installa** e Spwig scaricherà il componente, lo integrerà nel tuo sito e applicherà le migrazioni necessarie.

### Installazione manuale

Se stai eseguendo una configurazione Spwig personalizzata o sviluppi offline, puoi installare i componenti manualmente:

```bash
git clone https://github.com/Spwig/components.git
cp -r components/themes/botanica /path/to/spwig/media/components/themes/
```

Poi, nell'amministrazione Spwig, esegui **Marketplace → Riscansione componenti locali**.

---

## Sviluppare il proprio componente

Vuoi creare un nuovo tema, utilità o integrazione? Inizia con uno dei nostri SDK — ognuno è un piccolo framework ben documentato con un provider di esempio da forkare:

| SDK | Per creare |
|-----|-----------|
| [`theme-sdk`](https://github.com/Spwig/theme-sdk) | Temi con token, CSS critico e supporto page builder |
| [`provider-sdks`](https://github.com/Spwig/provider-sdks) | Integrazioni di pagamento, spedizione, SMS, email e altri provider |
| [`headless-sdk`](https://github.com/Spwig/headless-sdk) | Storefront headless che chiamano l'API Spwig |
| [`react`](https://github.com/Spwig/react) | Hook e componenti React per storefront headless |

Ogni componente in questo repository segue lo stesso formato di manifest (`manifest.json`) per essere scoperto dal marketplace Spwig.

---

## Contribuire

I contributi sono benvenuti. Per mantenere le cose semplici usiamo il **Developer Certificate of Origin (DCO)** invece di un CLA — aggiungi semplicemente una riga di firma ai tuoi commit:

```bash
git commit -s -m "Add support for X"
```

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) per i dettagli su come inviare una PR, il formato del manifest e le convenzioni di codice.

**Idee per contribuire:**

- Nuovi temi per settori poco coperti (cibo e bevande, salute, istruzione, immobili)
- Provider aggiuntivi di pagamento o spedizione per regione
- Correzioni e miglioramenti ai componenti esistenti
- Traduzioni del README e delle istruzioni di configurazione dei componenti

---

## Licenza

**AGPL-3.0** — vedi [LICENSE](LICENSE). Puoi usare, modificare e distribuire questo codice liberamente per negozi self-hosted. Se esegui una versione modificata come servizio di rete, devi rendere le tue modifiche disponibili ai tuoi utenti con la stessa licenza.

Per condizioni adatte a un uso proprietario o SaaS, contatta [licensing@spwig.com](mailto:licensing@spwig.com).

---

## Supporto

- **Documentazione**: [docs.spwig.com](https://docs.spwig.com)
- **Forum della community**: [community.spwig.com](https://community.spwig.com)
- **Email**: support@spwig.com
- **Issue**: [github.com/Spwig/components/issues](https://github.com/Spwig/components/issues)

---

<p align="center">
  <sub>Creato da <a href="https://spwig.com">Spwig</a> e collaboratori</sub>
</p>
