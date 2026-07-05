<p align="center">
  <a href="README.md">English</a> |
  <a href="README.fr.md">Français</a> |
  <a href="README.es.md">Español</a> |
  <a href="README.de.md">Deutsch</a> |
  <a href="README.ja.md">日本語</a> |
  <strong>简体中文</strong> |
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

<h1 align="center">Spwig 组件</h1>

<p align="center">
  <strong>为 Spwig 电商平台提供的主题、管理工具和服务商集成。</strong>
</p>

<p align="center">
  <a href="https://spwig.com">官网</a> &nbsp;&bull;&nbsp;
  <a href="https://docs.spwig.com">文档</a> &nbsp;&bull;&nbsp;
  <a href="https://community.spwig.com">社区</a> &nbsp;&bull;&nbsp;
  <a href="https://spwig.com/en/demos">在线演示</a>
</p>

---

## 概览

本仓库是 [Spwig](https://spwig.com) 的开源组件库,Spwig 是一款自托管电商平台。仓库包含 Spwig 安装可用的三类组件:

| | |
|--|--|
| **主题** | 即用型店铺设计 |
| **工具** | 管理界面辅助工具(取色器、渐变编辑器、焦点选择器等) |
| **集成** | 支付、物流、短信、邮件、翻译、SEO 及社交服务商 |

每个组件都可以通过 Spwig 管理面板一键安装并更新——无需编写代码——但源代码在此,便于你查看、贡献或 fork。

---

## 包含内容

### 主题 (13)

| 主题 | 风格 |
|------|------|
| **Default** | 简洁、专业、通用 |
| **Apparel** | 时尚与服装店铺 |
| **Artisan** | 手工艺品 |
| **Bold** | 高对比、有个性 |
| **Botanica** | 植物、园艺、自然产品 |
| **Elegant Shop** | 高端、奢华 |
| **Modern Dark** | 深色模式优先设计 |
| **Modern Shop** | 现代综合店铺 |
| **Nature** | 户外与可持续品牌 |
| **Space** | 科技、数码、未来感 |
| **Starter** | 定制主题的极简起点 |
| **Tech** | 电子产品与硬件 |
| **Vivid** | 鲜艳多彩 |

### 管理工具 (14)

在 Spwig 管理界面中可复用的 UI 组件——包括取色器、渐变创建器、焦点选择器、阴影编辑器、排版编辑器、背景编辑器、边框编辑器、间距编辑器、图标选择器、单位选择器、可见性规则编辑器、表单选择器、翻译编辑器,以及共享的工具基础库。

### 集成 (49+)

| 类别 | 服务商 |
|------|--------|
| **支付** | Stripe, Adyen, PayPal Checkout, Airwallex, Revolut, Square |
| **付款** | PayPal, Airwallex Payouts, Wise |
| **物流** | FedEx, UPS, USPS, Canada Post, Australia Post, NinjaVan |
| **终端** | Stripe Terminal, Square Terminal, Adyen Terminal, Revolut Terminal, SumUp, Zettle |
| **邮件** | Gmail API, SMTP (Gmail / Outlook / SendGrid / SES / 任意) |
| **短信** | Twilio, Twilio WhatsApp |
| **汇率** | Fixer, currencylayer, XE, Open Exchange Rates, exchangerate-api, exchangeratesapi |
| **翻译** | DeepL, AWS Translate, Azure Translator, Google Translate, 通用 API |
| **SEO** | Semrush, DataForSEO, AI SEO |
| **社交** | Facebook Pages, Instagram Business, LinkedIn Company, Twitter |
| **商品源** | Google Merchant Center |
| **许可服务器** | Cryptlex, LicenseSpring, Keygen, 自定义 API, Spwig 内置 |

---

## 安装

### 通过 Spwig 管理面板(推荐)

在 Spwig 店铺管理面板中一键安装组件:

**管理 → 市场 → 组件**

市场展示本仓库中所有组件,以及付费及第三方组件。点击 **安装**,Spwig 会获取组件、集成到你的站点,并执行必要的迁移。

### 手动安装

如果你运行的是自定义 Spwig 环境,或在离线开发,可以手动安装组件:

```bash
git clone https://github.com/Spwig/components.git
cp -r components/themes/botanica /path/to/spwig/media/components/themes/
```

然后在 Spwig 管理面板执行 **市场 → 重新扫描本地组件**。

---

## 开发自己的组件

想创建新主题、工具或集成?可以从我们的 SDK 开始——每个 SDK 都是精简且文档齐全的框架,并附带示例服务商可供 fork:

| SDK | 用于创建 |
|-----|---------|
| [`theme-sdk`](https://github.com/Spwig/theme-sdk) | 带 token、关键 CSS 和页面构建器支持的主题 |
| [`provider-sdks`](https://github.com/Spwig/provider-sdks) | 支付、物流、短信、邮件及其他服务商集成 |
| [`headless-sdk`](https://github.com/Spwig/headless-sdk) | 调用 Spwig API 的 headless 店铺 |
| [`react`](https://github.com/Spwig/react) | 用于 headless 店铺的 React hook 与组件 |

本仓库中每个组件都遵循相同的 manifest 格式 (`manifest.json`),便于 Spwig 市场自动发现。

---

## 贡献

欢迎贡献。为了简化流程,我们使用 **Developer Certificate of Origin (DCO)** 而非 CLA——只需在提交中添加签署行:

```bash
git commit -s -m "Add support for X"
```

关于如何提交 PR、manifest 格式及编码规范,请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

**贡献想法:**

- 为少人覆盖的行业提供新主题(餐饮、健康、教育、房产)
- 按地区提供额外的支付或物流服务商
- 修复现有组件的 bug、进行改进
- 翻译 README 和组件设置说明

---

## 许可协议

**AGPL-3.0** — 见 [LICENSE](LICENSE)。你可以自由使用、修改并分发本代码用于自托管店铺。如果你以网络服务形式运行修改版本,必须以相同许可向你的用户提供你的修改。

如需符合专有或 SaaS 用途的条款,请联系 [licensing@spwig.com](mailto:licensing@spwig.com)。

---

## 支持

- **文档**:[docs.spwig.com](https://docs.spwig.com)
- **社区论坛**:[community.spwig.com](https://community.spwig.com)
- **邮箱**:support@spwig.com
- **Issues**:[github.com/Spwig/components/issues](https://github.com/Spwig/components/issues)

---

<p align="center">
  <sub>由 <a href="https://spwig.com">Spwig</a> 与贡献者共同构建</sub>
</p>
