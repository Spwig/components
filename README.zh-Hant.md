<p align="center">
  <a href="README.md">English</a> |
  <a href="README.fr.md">Français</a> |
  <a href="README.es.md">Español</a> |
  <a href="README.de.md">Deutsch</a> |
  <a href="README.ja.md">日本語</a> |
  <a href="README.zh-Hans.md">简体中文</a> |
  <strong>繁體中文</strong> |
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

<h1 align="center">Spwig 元件</h1>

<p align="center">
  <strong>為 Spwig 電商平台提供的佈景主題、管理工具與服務商整合。</strong>
</p>

<p align="center">
  <a href="https://spwig.com">官網</a> &nbsp;&bull;&nbsp;
  <a href="https://docs.spwig.com">文件</a> &nbsp;&bull;&nbsp;
  <a href="https://community.spwig.com">社群</a> &nbsp;&bull;&nbsp;
  <a href="https://spwig.com/en/demos">線上示範</a>
</p>

---

## 概覽

本儲存庫是 [Spwig](https://spwig.com) 的開源元件庫,Spwig 是一款自架設電商平台。儲存庫包含 Spwig 安裝可用的三類元件:

| | |
|--|--|
| **佈景主題** | 即用型店面設計 |
| **工具** | 管理介面輔助工具(顏色選擇器、漸層編輯器、焦點選擇器等) |
| **整合** | 支付、物流、簡訊、電子郵件、翻譯、SEO 及社群服務商 |

每個元件都可透過 Spwig 管理面板一鍵安裝並更新——無需撰寫程式碼——但原始碼在此,方便你查看、貢獻或 fork。

---

## 包含內容

### 佈景主題 (13)

| 主題 | 風格 |
|------|------|
| **Default** | 簡潔、專業、通用 |
| **Apparel** | 時尚與服飾店 |
| **Artisan** | 手工藝品 |
| **Bold** | 高對比、有個性 |
| **Botanica** | 植物、園藝、自然產品 |
| **Elegant Shop** | 高端、奢華 |
| **Modern Dark** | 深色模式優先設計 |
| **Modern Shop** | 現代綜合店面 |
| **Nature** | 戶外與永續品牌 |
| **Space** | 科技、數位配件、未來感 |
| **Starter** | 自訂主題的極簡起點 |
| **Tech** | 電子產品與硬體 |
| **Vivid** | 鮮豔多彩 |

### 管理工具 (14)

在 Spwig 管理介面中可重複使用的 UI 元件——包括顏色選擇器、漸層產生器、焦點選擇器、陰影編輯器、字體編輯器、背景編輯器、邊框編輯器、間距編輯器、圖示選擇器、單位選擇器、可見性規則編輯器、表單選擇器、翻譯編輯器,以及共用工具基礎。

### 整合 (49+)

| 類別 | 服務商 |
|------|--------|
| **支付** | Stripe, Adyen, PayPal Checkout, Airwallex, Revolut, Square |
| **撥款** | PayPal, Airwallex Payouts, Wise |
| **物流** | FedEx, UPS, USPS, Canada Post, Australia Post, NinjaVan |
| **終端** | Stripe Terminal, Square Terminal, Adyen Terminal, Revolut Terminal, SumUp, Zettle |
| **電子郵件** | Gmail API, SMTP (Gmail / Outlook / SendGrid / SES / 任意) |
| **簡訊** | Twilio, Twilio WhatsApp |
| **匯率** | Fixer, currencylayer, XE, Open Exchange Rates, exchangerate-api, exchangeratesapi |
| **翻譯** | DeepL, AWS Translate, Azure Translator, Google Translate, 通用 API |
| **SEO** | Semrush, DataForSEO, AI SEO |
| **社群** | Facebook Pages, Instagram Business, LinkedIn Company, Twitter |
| **商品資料** | Google Merchant Center |
| **授權伺服器** | Cryptlex, LicenseSpring, Keygen, 自訂 API, Spwig 內建 |

---

## 安裝

### 透過 Spwig 管理面板(推薦)

在 Spwig 店面管理面板中一鍵安裝元件:

**管理 → 市集 → 元件**

市集會顯示本儲存庫的所有元件,以及付費及第三方元件。點擊 **安裝**,Spwig 便會取得元件、整合到你的網站,並套用必要的遷移。

### 手動安裝

如果你執行的是自訂的 Spwig 環境,或在離線開發,可以手動安裝元件:

```bash
git clone https://github.com/Spwig/components.git
cp -r components/themes/botanica /path/to/spwig/media/components/themes/
```

然後在 Spwig 管理面板執行 **市集 → 重新掃描本地元件**。

---

## 開發自己的元件

想建立新的佈景主題、工具或整合?可以從我們的 SDK 開始——每個 SDK 都是精簡且文件齊全的框架,並附帶可 fork 的範例服務商:

| SDK | 用途 |
|-----|------|
| [`theme-sdk`](https://github.com/Spwig/theme-sdk) | 具備 token、關鍵 CSS 和頁面建構器支援的佈景主題 |
| [`provider-sdks`](https://github.com/Spwig/provider-sdks) | 支付、物流、簡訊、電子郵件及其他服務商整合 |
| [`headless-sdk`](https://github.com/Spwig/headless-sdk) | 呼叫 Spwig API 的 headless 店面 |
| [`react`](https://github.com/Spwig/react) | 用於 headless 店面的 React hook 與元件 |

本儲存庫中每個元件都遵循相同的 manifest 格式 (`manifest.json`),便於 Spwig 市集自動發現。

---

## 貢獻

歡迎貢獻。為了簡化流程,我們採用 **Developer Certificate of Origin (DCO)** 而非 CLA——只需在提交中加上簽署行:

```bash
git commit -s -m "Add support for X"
```

關於如何提交 PR、manifest 格式及編碼慣例,請參閱 [CONTRIBUTING.md](CONTRIBUTING.md)。

**貢獻構想:**

- 為較少涵蓋的行業提供新佈景主題(餐飲、健康、教育、房產)
- 按地區提供額外的支付或物流服務商
- 修復現有元件的錯誤、進行改進
- 翻譯 README 和元件設定說明

---

## 授權

**AGPL-3.0** — 詳見 [LICENSE](LICENSE)。你可以自由使用、修改並散布本程式碼用於自架店面。如果你以網路服務形式執行修改版本,必須以相同授權向你的使用者公開你的修改。

如需符合專有或 SaaS 用途的條款,請聯絡 [licensing@spwig.com](mailto:licensing@spwig.com)。

---

## 支援

- **文件**:[docs.spwig.com](https://docs.spwig.com)
- **社群論壇**:[community.spwig.com](https://community.spwig.com)
- **電子郵件**:support@spwig.com
- **Issues**:[github.com/Spwig/components/issues](https://github.com/Spwig/components/issues)

---

<p align="center">
  <sub>由 <a href="https://spwig.com">Spwig</a> 與貢獻者共同打造</sub>
</p>
