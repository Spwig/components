<p align="center">
  <a href="README.md">English</a> |
  <strong>Français</strong> |
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

<h1 align="center">Composants Spwig</h1>

<p align="center">
  <strong>Thèmes, utilitaires d'administration et intégrations de fournisseurs pour la plateforme e-commerce Spwig.</strong>
</p>

<p align="center">
  <a href="https://spwig.com">Site web</a> &nbsp;&bull;&nbsp;
  <a href="https://docs.spwig.com">Documentation</a> &nbsp;&bull;&nbsp;
  <a href="https://community.spwig.com">Communauté</a> &nbsp;&bull;&nbsp;
  <a href="https://spwig.com/en/demos">Démos en direct</a>
</p>

---

## Aperçu

Ce dépôt est la bibliothèque de composants open source de [Spwig](https://spwig.com), une plateforme e-commerce auto-hébergée. Il contient trois types de composants qu'une installation Spwig peut utiliser :

| | |
|--|--|
| **Thèmes** | Designs de boutique prêts à l'emploi |
| **Utilitaires** | Aides pour l'interface d'administration (sélecteur de couleur, éditeur de dégradé, sélecteur de point focal, etc.) |
| **Intégrations** | Fournisseurs de paiement, livraison, SMS, e-mail, traduction, SEO et réseaux sociaux |

Chaque composant est conçu pour être installé et mis à jour via l'admin Spwig — sans écrire de code — mais le code source vit ici pour que vous puissiez l'inspecter, contribuer, ou faire un fork.

---

## Ce qui est inclus

### Thèmes (13)

| Thème | Style |
|-------|-------|
| **Default** | Propre, professionnel, polyvalent |
| **Apparel** | Boutiques de mode et vêtements |
| **Artisan** | Produits artisanaux |
| **Bold** | Contraste élevé, affirmé |
| **Botanica** | Plantes, jardin, produits naturels |
| **Elegant Shop** | Premium, luxe |
| **Modern Dark** | Design pensé pour le mode sombre |
| **Modern Shop** | Boutique généraliste contemporaine |
| **Nature** | Marques outdoor et durables |
| **Space** | Tech, gadgets, futuriste |
| **Starter** | Point de départ minimal pour thèmes personnalisés |
| **Tech** | Électronique et matériel |
| **Vivid** | Vivant, coloré |

### Utilitaires d'administration (14)

Éléments d'interface réutilisables dans toute l'administration Spwig — incluant sélecteur de couleur, créateur de dégradé, sélecteur de point focal, éditeur d'ombre, éditeur typographique, éditeur d'arrière-plan, éditeur de bordure, éditeur d'espacement, sélecteur d'icônes, sélecteur d'unité, éditeur de règles de visibilité, sélecteur de formulaire, éditeur de traduction, et une base utilitaire partagée.

### Intégrations (49+)

| Catégorie | Fournisseurs |
|-----------|--------------|
| **Paiements** | Stripe, Adyen, PayPal Checkout, Airwallex, Revolut, Square |
| **Versements** | PayPal, Airwallex Payouts, Wise |
| **Livraison** | FedEx, UPS, USPS, Canada Post, Australia Post, NinjaVan |
| **Terminaux** | Stripe Terminal, Square Terminal, Adyen Terminal, Revolut Terminal, SumUp, Zettle |
| **E-mail** | Gmail API, SMTP (Gmail / Outlook / SendGrid / SES / autre) |
| **SMS** | Twilio, Twilio WhatsApp |
| **Taux de change** | Fixer, currencylayer, XE, Open Exchange Rates, exchangerate-api, exchangeratesapi |
| **Traduction** | DeepL, AWS Translate, Azure Translator, Google Translate, API générique |
| **SEO** | Semrush, DataForSEO, AI SEO |
| **Réseaux sociaux** | Facebook Pages, Instagram Business, LinkedIn Company, Twitter |
| **Flux produits** | Google Merchant Center |
| **Serveurs de licence** | Cryptlex, LicenseSpring, Keygen, API personnalisée, Spwig intégré |

---

## Installation

### Via l'admin Spwig (recommandé)

Les composants s'installent en un clic depuis l'administration de votre boutique Spwig :

**Admin → Marketplace → Composants**

Le marketplace affiche tous les composants de ce dépôt, ainsi que ceux premium et tiers. Cliquez sur **Installer**, et Spwig récupère le composant, l'intègre à votre site et applique les migrations nécessaires.

### Installation manuelle

Si vous exécutez une configuration Spwig personnalisée ou développez hors ligne, vous pouvez installer les composants manuellement :

```bash
git clone https://github.com/Spwig/components.git
cp -r components/themes/botanica /path/to/spwig/media/components/themes/
```

Ensuite, dans l'admin Spwig, exécutez **Marketplace → Rescanner les composants locaux**.

---

## Développer votre propre composant

Vous créez un nouveau thème, utilitaire ou intégration ? Commencez avec l'un de nos SDK — chacun est un petit framework bien documenté avec un fournisseur d'exemple que vous pouvez forker :

| SDK | Pour créer |
|-----|-----------|
| [`theme-sdk`](https://github.com/Spwig/theme-sdk) | Thèmes avec tokens, CSS critique et support du page builder |
| [`provider-sdks`](https://github.com/Spwig/provider-sdks) | Intégrations paiement, livraison, SMS, e-mail et autres fournisseurs |
| [`headless-sdk`](https://github.com/Spwig/headless-sdk) | Boutiques headless appelant l'API Spwig |
| [`react`](https://github.com/Spwig/react) | Hooks et composants React pour boutiques headless |

Chaque composant de ce dépôt suit le même format de manifeste (`manifest.json`) pour être découvert par le marketplace Spwig.

---

## Contribuer

Les contributions sont bienvenues. Pour simplifier les choses, nous utilisons le **Developer Certificate of Origin (DCO)** au lieu d'un CLA — ajoutez simplement une ligne de signature à vos commits :

```bash
git commit -s -m "Ajouter le support de X"
```

Consultez [CONTRIBUTING.md](CONTRIBUTING.md) pour les détails sur la soumission d'une PR, le format du manifeste et les conventions de code.

**Idées de contribution :**

- Nouveaux thèmes pour des secteurs peu couverts (restauration, santé, éducation, immobilier)
- Fournisseurs de paiement ou de livraison supplémentaires par région
- Corrections et améliorations des composants existants
- Traductions du README et des instructions de configuration des composants

---

## Licence

**AGPL-3.0** — voir [LICENSE](LICENSE). Vous pouvez utiliser, modifier et distribuer ce code librement pour des boutiques auto-hébergées. Si vous exécutez une version modifiée en tant que service réseau, vous devez mettre vos changements à disposition de vos utilisateurs sous la même licence.

Pour des conditions adaptées à un usage propriétaire ou SaaS, contactez [licensing@spwig.com](mailto:licensing@spwig.com).

---

## Support

- **Documentation** : [docs.spwig.com](https://docs.spwig.com)
- **Forum communautaire** : [community.spwig.com](https://community.spwig.com)
- **E-mail** : support@spwig.com
- **Issues** : [github.com/Spwig/components/issues](https://github.com/Spwig/components/issues)

---

<p align="center">
  <sub>Créé par <a href="https://spwig.com">Spwig</a> et ses contributeurs</sub>
</p>
