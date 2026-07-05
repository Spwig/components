<p align="center">
  <a href="README.md">English</a> |
  <a href="README.fr.md">Français</a> |
  <a href="README.es.md">Español</a> |
  <a href="README.de.md">Deutsch</a> |
  <a href="README.ja.md">日本語</a> |
  <a href="README.zh-Hans.md">简体中文</a> |
  <a href="README.zh-Hant.md">繁體中文</a> |
  <strong>Português</strong> |
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

<h1 align="center">Componentes Spwig</h1>

<p align="center">
  <strong>Temas, utilidades de administração e integrações de provedores para a plataforma de e-commerce Spwig.</strong>
</p>

<p align="center">
  <a href="https://spwig.com">Site</a> &nbsp;&bull;&nbsp;
  <a href="https://docs.spwig.com">Documentação</a> &nbsp;&bull;&nbsp;
  <a href="https://community.spwig.com">Comunidade</a> &nbsp;&bull;&nbsp;
  <a href="https://spwig.com/en/demos">Demos ao vivo</a>
</p>

---

## Visão geral

Este repositório é a biblioteca de componentes open source do [Spwig](https://spwig.com), uma plataforma de e-commerce auto-hospedada. Contém três tipos de componentes que uma instalação Spwig pode usar:

| | |
|--|--|
| **Temas** | Designs de loja prontos para usar |
| **Utilidades** | Auxiliares para a interface de administração (seletor de cor, editor de gradiente, seletor de ponto focal, etc.) |
| **Integrações** | Provedores de pagamento, envio, SMS, e-mail, tradução, SEO e redes sociais |

Cada componente é feito para ser instalado e atualizado através do painel de administração do Spwig — sem código — mas o código-fonte vive aqui para que você possa inspecionar, contribuir ou fazer fork.

---

## O que está incluído

### Temas (13)

| Tema | Estilo |
|------|--------|
| **Default** | Limpo, profissional, versátil |
| **Apparel** | Lojas de moda e vestuário |
| **Artisan** | Produtos artesanais |
| **Bold** | Alto contraste, marcante |
| **Botanica** | Plantas, jardim, produtos naturais |
| **Elegant Shop** | Premium, luxo |
| **Modern Dark** | Design pensado para modo escuro |
| **Modern Shop** | Loja geral contemporânea |
| **Nature** | Marcas outdoor e sustentáveis |
| **Space** | Tech, gadgets, futurista |
| **Starter** | Ponto de partida minimalista para temas personalizados |
| **Tech** | Eletrônica e hardware |
| **Vivid** | Vibrante, colorido |

### Utilidades de administração (14)

Peças de interface reutilizáveis em toda a administração do Spwig — incluindo seletor de cor, criador de gradiente, seletor de ponto focal, editor de sombra, editor de tipografia, editor de fundo, editor de borda, editor de espaçamento, seletor de ícones, seletor de unidade, editor de regras de visibilidade, seletor de formulário, editor de tradução e uma base compartilhada de utilidades.

### Integrações (49+)

| Categoria | Provedores |
|-----------|------------|
| **Pagamentos** | Stripe, Adyen, PayPal Checkout, Airwallex, Revolut, Square |
| **Pagamentos de saída** | PayPal, Airwallex Payouts, Wise |
| **Envio** | FedEx, UPS, USPS, Canada Post, Australia Post, NinjaVan |
| **Terminais** | Stripe Terminal, Square Terminal, Adyen Terminal, Revolut Terminal, SumUp, Zettle |
| **E-mail** | Gmail API, SMTP (Gmail / Outlook / SendGrid / SES / qualquer) |
| **SMS** | Twilio, Twilio WhatsApp |
| **Câmbio** | Fixer, currencylayer, XE, Open Exchange Rates, exchangerate-api, exchangeratesapi |
| **Tradução** | DeepL, AWS Translate, Azure Translator, Google Translate, API genérica |
| **SEO** | Semrush, DataForSEO, AI SEO |
| **Redes sociais** | Facebook Pages, Instagram Business, LinkedIn Company, Twitter |
| **Feeds de produtos** | Google Merchant Center |
| **Servidores de licenças** | Cryptlex, LicenseSpring, Keygen, API personalizada, Spwig integrado |

---

## Instalação

### Pelo painel do Spwig (recomendado)

Os componentes são instalados com um clique a partir da administração da sua loja Spwig:

**Admin → Marketplace → Componentes**

O marketplace mostra todos os componentes deste repositório, além dos premium e de terceiros. Clique em **Instalar** e o Spwig baixa o componente, integra ao seu site e aplica quaisquer migrações necessárias.

### Instalação manual

Se você estiver rodando uma configuração personalizada do Spwig ou desenvolvendo offline, pode instalar componentes manualmente:

```bash
git clone https://github.com/Spwig/components.git
cp -r components/themes/botanica /path/to/spwig/media/components/themes/
```

Depois, no painel do Spwig, execute **Marketplace → Rescan de componentes locais**.

---

## Desenvolvendo seu próprio componente

Está criando um novo tema, utilidade ou integração? Comece com um dos nossos SDKs — cada um é um pequeno framework bem documentado com um provedor de exemplo para você fazer fork:

| SDK | Para criar |
|-----|-----------|
| [`theme-sdk`](https://github.com/Spwig/theme-sdk) | Temas com tokens, CSS crítico e suporte a page builder |
| [`provider-sdks`](https://github.com/Spwig/provider-sdks) | Integrações de pagamento, envio, SMS, e-mail e outros provedores |
| [`headless-sdk`](https://github.com/Spwig/headless-sdk) | Storefronts headless que chamam a API do Spwig |
| [`react`](https://github.com/Spwig/react) | Hooks e componentes React para storefronts headless |

Cada componente neste repositório segue o mesmo formato de manifest (`manifest.json`) para ser descoberto pelo marketplace do Spwig.

---

## Como contribuir

Contribuições são bem-vindas. Para manter as coisas simples, usamos o **Developer Certificate of Origin (DCO)** em vez de um CLA — apenas adicione uma linha de assinatura aos seus commits:

```bash
git commit -s -m "Add support for X"
```

Consulte [CONTRIBUTING.md](CONTRIBUTING.md) para detalhes sobre como enviar um PR, o formato do manifest e as convenções de código.

**Ideias para contribuir:**

- Novos temas para verticais pouco atendidas (comida e bebida, saúde, educação, imóveis)
- Provedores adicionais de pagamento ou envio por região
- Correções e melhorias para os componentes existentes
- Traduções do README e das instruções de configuração dos componentes

---

## Licença

**AGPL-3.0** — veja [LICENSE](LICENSE). Você pode usar, modificar e distribuir este código livremente para lojas auto-hospedadas. Se você executar uma versão modificada como serviço de rede, deve disponibilizar suas mudanças aos seus usuários sob a mesma licença.

Para termos adequados a um uso proprietário ou SaaS, entre em contato: [licensing@spwig.com](mailto:licensing@spwig.com).

---

## Suporte

- **Documentação**: [docs.spwig.com](https://docs.spwig.com)
- **Fórum da comunidade**: [community.spwig.com](https://community.spwig.com)
- **E-mail**: support@spwig.com
- **Issues**: [github.com/Spwig/components/issues](https://github.com/Spwig/components/issues)

---

<p align="center">
  <sub>Criado por <a href="https://spwig.com">Spwig</a> e colaboradores</sub>
</p>
