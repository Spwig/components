<p align="center">
  <a href="README.md">English</a> |
  <a href="README.fr.md">Français</a> |
  <strong>Español</strong> |
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

<h1 align="center">Componentes de Spwig</h1>

<p align="center">
  <strong>Temas, utilidades de administración e integraciones de proveedores para la plataforma de comercio electrónico Spwig.</strong>
</p>

<p align="center">
  <a href="https://spwig.com">Sitio web</a> &nbsp;&bull;&nbsp;
  <a href="https://docs.spwig.com">Documentación</a> &nbsp;&bull;&nbsp;
  <a href="https://community.spwig.com">Comunidad</a> &nbsp;&bull;&nbsp;
  <a href="https://spwig.com/en/demos">Demos en vivo</a>
</p>

---

## Descripción general

Este repositorio es la biblioteca de componentes de código abierto de [Spwig](https://spwig.com), una plataforma de comercio electrónico autoalojada. Contiene tres tipos de componentes que una instalación de Spwig puede utilizar:

| | |
|--|--|
| **Temas** | Diseños de tienda listos para usar |
| **Utilidades** | Ayudantes para la interfaz de administración (selector de color, editor de degradados, selector de punto focal, etc.) |
| **Integraciones** | Proveedores de pagos, envíos, SMS, correo electrónico, traducción, SEO y redes sociales |

Cada componente está diseñado para instalarse y actualizarse desde el panel de administración de Spwig, sin necesidad de escribir código, pero el código fuente vive aquí para que puedas inspeccionarlo, contribuir o hacer un fork.

---

## Lo que se incluye

### Temas (13)

| Tema | Estilo |
|------|--------|
| **Default** | Limpio, profesional, versátil |
| **Apparel** | Tiendas de moda y ropa |
| **Artisan** | Productos artesanales |
| **Bold** | Alto contraste, con carácter |
| **Botanica** | Plantas, jardín, productos naturales |
| **Elegant Shop** | Premium, lujo |
| **Modern Dark** | Diseño pensado para modo oscuro |
| **Modern Shop** | Tienda general contemporánea |
| **Nature** | Marcas al aire libre y sostenibles |
| **Space** | Tecnología, gadgets, futurista |
| **Starter** | Punto de partida minimalista para temas personalizados |
| **Tech** | Electrónica y hardware |
| **Vivid** | Vibrante, colorido |

### Utilidades de administración (14)

Piezas de interfaz reutilizables en toda la administración de Spwig, incluyendo selector de color, creador de degradados, selector de punto focal, editor de sombras, editor de tipografía, editor de fondo, editor de bordes, editor de espaciado, selector de iconos, selector de unidades, editor de reglas de visibilidad, selector de formularios, editor de traducciones y una base compartida de utilidades.

### Integraciones (49+)

| Categoría | Proveedores |
|-----------|-------------|
| **Pagos** | Stripe, Adyen, PayPal Checkout, Airwallex, Revolut, Square |
| **Pagos salientes** | PayPal, Airwallex Payouts, Wise |
| **Envíos** | FedEx, UPS, USPS, Canada Post, Australia Post, NinjaVan |
| **Terminales** | Stripe Terminal, Square Terminal, Adyen Terminal, Revolut Terminal, SumUp, Zettle |
| **Correo** | Gmail API, SMTP (Gmail / Outlook / SendGrid / SES / cualquiera) |
| **SMS** | Twilio, Twilio WhatsApp |
| **Tipos de cambio** | Fixer, currencylayer, XE, Open Exchange Rates, exchangerate-api, exchangeratesapi |
| **Traducción** | DeepL, AWS Translate, Azure Translator, Google Translate, API genérica |
| **SEO** | Semrush, DataForSEO, AI SEO |
| **Redes sociales** | Facebook Pages, Instagram Business, LinkedIn Company, Twitter |
| **Feeds de productos** | Google Merchant Center |
| **Servidores de licencias** | Cryptlex, LicenseSpring, Keygen, API personalizada, Spwig integrado |

---

## Instalación

### Desde el panel de Spwig (recomendado)

Los componentes se instalan con un clic desde la administración de tu tienda Spwig:

**Admin → Marketplace → Componentes**

El marketplace muestra todos los componentes de este repositorio, además de los premium y los de terceros. Haz clic en **Instalar** y Spwig descargará el componente, lo integrará en tu sitio y aplicará las migraciones necesarias.

### Instalación manual

Si ejecutas una instalación personalizada de Spwig o desarrollas sin conexión, puedes instalar componentes manualmente:

```bash
git clone https://github.com/Spwig/components.git
cp -r components/themes/botanica /path/to/spwig/media/components/themes/
```

Luego, en la administración de Spwig, ejecuta **Marketplace → Volver a escanear componentes locales**.

---

## Cómo desarrollar tu propio componente

¿Quieres crear un nuevo tema, utilidad o integración? Empieza con uno de nuestros SDK — cada uno es un pequeño marco bien documentado con un proveedor de ejemplo que puedes usar como base:

| SDK | Para crear |
|-----|------------|
| [`theme-sdk`](https://github.com/Spwig/theme-sdk) | Temas con tokens, CSS crítico y soporte para el generador de páginas |
| [`provider-sdks`](https://github.com/Spwig/provider-sdks) | Integraciones de pagos, envíos, SMS, correo y otros proveedores |
| [`headless-sdk`](https://github.com/Spwig/headless-sdk) | Storefronts headless que consumen la API de Spwig |
| [`react`](https://github.com/Spwig/react) | Hooks y componentes React para storefronts headless |

Todos los componentes de este repositorio siguen el mismo formato de manifiesto (`manifest.json`) para que el marketplace de Spwig los pueda descubrir.

---

## Cómo contribuir

Las contribuciones son bienvenidas. Para mantener las cosas simples usamos el **Developer Certificate of Origin (DCO)** en lugar de un CLA — solo añade una línea de firma a tus commits:

```bash
git commit -s -m "Añadir soporte para X"
```

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para más detalles sobre cómo enviar un PR, el formato de manifiesto y las convenciones de código.

**Ideas para contribuir:**

- Nuevos temas para verticales poco cubiertas (alimentación y bebidas, salud, educación, inmobiliario)
- Proveedores adicionales de pagos o envíos por región
- Correcciones y mejoras a los componentes existentes
- Traducciones del README y de las instrucciones de configuración de los componentes

---

## Licencia

**AGPL-3.0** — consulta [LICENSE](LICENSE). Puedes usar, modificar y distribuir este código libremente para tiendas autoalojadas. Si ejecutas una versión modificada como servicio de red, debes poner tus cambios a disposición de tus usuarios bajo la misma licencia.

Para términos que se adapten a un uso propietario o SaaS, contacta [licensing@spwig.com](mailto:licensing@spwig.com).

---

## Soporte

- **Documentación**: [docs.spwig.com](https://docs.spwig.com)
- **Foro de la comunidad**: [community.spwig.com](https://community.spwig.com)
- **Correo electrónico**: support@spwig.com
- **Issues**: [github.com/Spwig/components/issues](https://github.com/Spwig/components/issues)

---

<p align="center">
  <sub>Creado por <a href="https://spwig.com">Spwig</a> y sus colaboradores</sub>
</p>
