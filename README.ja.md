<p align="center">
  <a href="README.md">English</a> |
  <a href="README.fr.md">Français</a> |
  <a href="README.es.md">Español</a> |
  <a href="README.de.md">Deutsch</a> |
  <strong>日本語</strong> |
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

<h1 align="center">Spwig コンポーネント</h1>

<p align="center">
  <strong>Spwig e コマースプラットフォーム向けのテーマ、管理ユーティリティ、プロバイダー統合。</strong>
</p>

<p align="center">
  <a href="https://spwig.com">ウェブサイト</a> &nbsp;&bull;&nbsp;
  <a href="https://docs.spwig.com">ドキュメント</a> &nbsp;&bull;&nbsp;
  <a href="https://community.spwig.com">コミュニティ</a> &nbsp;&bull;&nbsp;
  <a href="https://spwig.com/en/demos">ライブデモ</a>
</p>

---

## 概要

このリポジトリは、セルフホスト型 e コマースプラットフォーム [Spwig](https://spwig.com) 用のオープンソースコンポーネントライブラリです。Spwig インストールで使用できる 3 種類のコンポーネントを含みます:

| | |
|--|--|
| **テーマ** | すぐに使えるストアフロントデザイン |
| **ユーティリティ** | 管理 UI のヘルパー (カラーピッカー、グラデーションエディタ、フォーカルポイントピッカーなど) |
| **統合** | 決済、配送、SMS、メール、翻訳、SEO、ソーシャルプロバイダー |

各コンポーネントは Spwig 管理画面からコードなしでインストールおよび更新できるように設計されていますが、ソースはここにあり、検査、貢献、フォークが可能です。

---

## 含まれるもの

### テーマ (13)

| テーマ | スタイル |
|--------|----------|
| **Default** | 清潔でプロフェッショナル、汎用的 |
| **Apparel** | ファッション・アパレルストア |
| **Artisan** | 手工芸品 |
| **Bold** | 高コントラスト、印象的 |
| **Botanica** | 植物、ガーデン、自然素材 |
| **Elegant Shop** | プレミアム、ラグジュアリー |
| **Modern Dark** | ダークモード優先のデザイン |
| **Modern Shop** | 現代的な総合ストア |
| **Nature** | アウトドア・サステナブルブランド |
| **Space** | テック、ガジェット、未来的 |
| **Starter** | カスタムテーマ向けの最小の出発点 |
| **Tech** | エレクトロニクス・ハードウェア |
| **Vivid** | 鮮やかでカラフル |

### 管理ユーティリティ (14)

Spwig 管理画面全体で再利用される UI パーツ — カラーピッカー、グラデーション作成、フォーカルポイント選択、シャドウエディタ、タイポグラフィエディタ、背景エディタ、ボーダーエディタ、スペーシングエディタ、アイコンピッカー、単位セレクタ、可視性ルールエディタ、フォームセレクタ、翻訳エディタ、共有ユーティリティベースなど。

### 統合 (49+)

| カテゴリー | プロバイダー |
|-----------|-------------|
| **決済** | Stripe, Adyen, PayPal Checkout, Airwallex, Revolut, Square |
| **送金** | PayPal, Airwallex Payouts, Wise |
| **配送** | FedEx, UPS, USPS, Canada Post, Australia Post, NinjaVan |
| **端末** | Stripe Terminal, Square Terminal, Adyen Terminal, Revolut Terminal, SumUp, Zettle |
| **メール** | Gmail API, SMTP (Gmail / Outlook / SendGrid / SES / 任意) |
| **SMS** | Twilio, Twilio WhatsApp |
| **為替レート** | Fixer, currencylayer, XE, Open Exchange Rates, exchangerate-api, exchangeratesapi |
| **翻訳** | DeepL, AWS Translate, Azure Translator, Google Translate, 汎用 API |
| **SEO** | Semrush, DataForSEO, AI SEO |
| **ソーシャル** | Facebook Pages, Instagram Business, LinkedIn Company, Twitter |
| **商品フィード** | Google Merchant Center |
| **ライセンスサーバー** | Cryptlex, LicenseSpring, Keygen, カスタム API, Spwig 組み込み |

---

## インストール

### Spwig 管理画面から (推奨)

コンポーネントは、Spwig ストア管理画面からワンクリックでインストールできます:

**管理 → マーケットプレイス → コンポーネント**

マーケットプレイスには、このリポジトリのすべてのコンポーネントに加え、プレミアムやサードパーティのコンポーネントも表示されます。**インストール** をクリックすると、Spwig がコンポーネントを取得し、サイトに統合し、必要な移行を適用します。

### 手動インストール

カスタマイズした Spwig 環境で実行している場合やオフラインで開発している場合は、手動でコンポーネントをインストールできます:

```bash
git clone https://github.com/Spwig/components.git
cp -r components/themes/botanica /path/to/spwig/media/components/themes/
```

その後、Spwig 管理画面で **マーケットプレイス → ローカルコンポーネントを再スキャン** を実行します。

---

## 独自のコンポーネントを開発する

新しいテーマ、ユーティリティ、統合を作成しますか？ 私たちの SDK のいずれかから始めてください — それぞれ小さくてドキュメントが充実したフレームワークで、フォーク可能なサンプルプロバイダーが含まれています:

| SDK | 作成するもの |
|-----|-------------|
| [`theme-sdk`](https://github.com/Spwig/theme-sdk) | トークン、クリティカル CSS、ページビルダー対応のテーマ |
| [`provider-sdks`](https://github.com/Spwig/provider-sdks) | 決済、配送、SMS、メール、その他プロバイダーの統合 |
| [`headless-sdk`](https://github.com/Spwig/headless-sdk) | Spwig API を呼び出すヘッドレスストアフロント |
| [`react`](https://github.com/Spwig/react) | ヘッドレスストアフロント用の React フックとコンポーネント |

このリポジトリのすべてのコンポーネントは、Spwig マーケットプレイスから検出可能にするために同じマニフェスト形式 (`manifest.json`) に従っています。

---

## 貢献する

貢献を歓迎します。シンプルさを保つため、CLA の代わりに **Developer Certificate of Origin (DCO)** を使用しています — コミットに署名行を追加するだけです:

```bash
git commit -s -m "Add support for X"
```

PR の提出方法、マニフェスト形式、コーディング規約の詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

**貢献のアイデア:**

- 未対応の分野向けの新しいテーマ (飲食、健康、教育、不動産)
- 地域別の追加決済または配送プロバイダー
- 既存コンポーネントのバグ修正と改善
- README とコンポーネント設定手順の翻訳

---

## ライセンス

**AGPL-3.0** — [LICENSE](LICENSE) を参照。セルフホスト型ストア向けにこのコードを自由に使用、変更、配布できます。変更したバージョンをネットワークサービスとして実行する場合、同じライセンスの下でユーザーに変更内容を公開する必要があります。

プロプライエタリまたは SaaS 用途に適した条件については、[licensing@spwig.com](mailto:licensing@spwig.com) にお問い合わせください。

---

## サポート

- **ドキュメント**: [docs.spwig.com](https://docs.spwig.com)
- **コミュニティフォーラム**: [community.spwig.com](https://community.spwig.com)
- **メール**: support@spwig.com
- **Issue**: [github.com/Spwig/components/issues](https://github.com/Spwig/components/issues)

---

<p align="center">
  <sub><a href="https://spwig.com">Spwig</a> と貢献者によって作成</sub>
</p>
