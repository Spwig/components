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
  <a href="README.it.md">Italiano</a> |
  <a href="README.ko.md">한국어</a> |
  <strong>Türkçe</strong> |
  <a href="README.vi.md">Tiếng Việt</a> |
  <a href="README.th.md">ไทย</a>
</p>

<p align="center">
  <img src="https://spwig.com/images/logo.svg" alt="Spwig" width="200">
</p>

<h1 align="center">Spwig Bileşenleri</h1>

<p align="center">
  <strong>Spwig e-ticaret platformu için temalar, yönetim araçları ve sağlayıcı entegrasyonları.</strong>
</p>

<p align="center">
  <a href="https://spwig.com">Web sitesi</a> &nbsp;&bull;&nbsp;
  <a href="https://docs.spwig.com">Belgeler</a> &nbsp;&bull;&nbsp;
  <a href="https://community.spwig.com">Topluluk</a> &nbsp;&bull;&nbsp;
  <a href="https://spwig.com/en/demos">Canlı Demolar</a>
</p>

---

## Genel Bakış

Bu depo, kendi kendine barındırılan bir e-ticaret platformu olan [Spwig](https://spwig.com) için açık kaynak bileşen kütüphanesidir. Bir Spwig kurulumunun kullanabileceği üç tür bileşen içerir:

| | |
|--|--|
| **Temalar** | Kullanıma hazır mağaza tasarımları |
| **Araçlar** | Yönetim arayüzü yardımcıları (renk seçici, gradyan düzenleyici, odak noktası seçici, vb.) |
| **Entegrasyonlar** | Ödeme, kargo, SMS, e-posta, çeviri, SEO ve sosyal medya sağlayıcıları |

Her bileşen, Spwig yönetim panelinden — kod yazmadan — kurulmak ve güncellenmek üzere tasarlanmıştır, ancak kaynak kod burada yaşar, böylece inceleyebilir, katkıda bulunabilir veya fork edebilirsiniz.

---

## İçindekiler

### Temalar (13)

| Tema | Stil |
|------|------|
| **Default** | Temiz, profesyonel, çok yönlü |
| **Apparel** | Moda ve giyim mağazaları |
| **Artisan** | El yapımı ürünler |
| **Bold** | Yüksek kontrast, iddialı |
| **Botanica** | Bitkiler, bahçe, doğal ürünler |
| **Elegant Shop** | Premium, lüks |
| **Modern Dark** | Karanlık mod öncelikli tasarım |
| **Modern Shop** | Çağdaş genel mağaza |
| **Nature** | Outdoor ve sürdürülebilir markalar |
| **Space** | Teknoloji, gadget, fütüristik |
| **Starter** | Özel temalar için minimal başlangıç noktası |
| **Tech** | Elektronik ve donanım |
| **Vivid** | Canlı, renkli |

### Yönetim Araçları (14)

Spwig yönetim panelinde tekrar kullanılabilir UI parçaları — renk seçici, gradyan oluşturucu, odak noktası seçici, gölge düzenleyici, tipografi düzenleyici, arka plan düzenleyici, kenarlık düzenleyici, boşluk düzenleyici, ikon seçici, birim seçici, görünürlük kuralı düzenleyici, form seçici, çeviri düzenleyici ve ortak bir araç tabanı dahil.

### Entegrasyonlar (49+)

| Kategori | Sağlayıcılar |
|----------|-------------|
| **Ödemeler** | Stripe, Adyen, PayPal Checkout, Airwallex, Revolut, Square |
| **Ödemeler (giden)** | PayPal, Airwallex Payouts, Wise |
| **Kargo** | FedEx, UPS, USPS, Canada Post, Australia Post, NinjaVan |
| **Terminaller** | Stripe Terminal, Square Terminal, Adyen Terminal, Revolut Terminal, SumUp, Zettle |
| **E-posta** | Gmail API, SMTP (Gmail / Outlook / SendGrid / SES / herhangi biri) |
| **SMS** | Twilio, Twilio WhatsApp |
| **Döviz kurları** | Fixer, currencylayer, XE, Open Exchange Rates, exchangerate-api, exchangeratesapi |
| **Çeviri** | DeepL, AWS Translate, Azure Translator, Google Translate, Genel API |
| **SEO** | Semrush, DataForSEO, AI SEO |
| **Sosyal** | Facebook Pages, Instagram Business, LinkedIn Company, Twitter |
| **Ürün beslemeleri** | Google Merchant Center |
| **Lisans sunucuları** | Cryptlex, LicenseSpring, Keygen, Özel API, Spwig Yerleşik |

---

## Kurulum

### Spwig yönetim paneli üzerinden (önerilen)

Bileşenler, Spwig mağazanızın yönetim panelinden tek tıklamayla kurulur:

**Yönetim → Marketplace → Bileşenler**

Marketplace, bu depodaki tüm bileşenleri, ayrıca premium ve üçüncü taraf bileşenleri gösterir. **Kur** düğmesine tıklayın ve Spwig bileşeni getirir, sitenize entegre eder ve gereken tüm migrasyonları uygular.

### Manuel kurulum

Özelleştirilmiş bir Spwig kurulumu çalıştırıyorsanız veya çevrimdışı geliştirme yapıyorsanız, bileşenleri manuel olarak kurabilirsiniz:

```bash
git clone https://github.com/Spwig/components.git
cp -r components/themes/botanica /path/to/spwig/media/components/themes/
```

Ardından Spwig yönetim panelinde **Marketplace → Yerel Bileşenleri Yeniden Tara** komutunu çalıştırın.

---

## Kendi Bileşeninizi Geliştirme

Yeni bir tema, araç veya entegrasyon mu oluşturuyorsunuz? SDK'larımızdan biriyle başlayın — her biri iyi belgelenmiş küçük bir çerçevedir ve fork edebileceğiniz bir örnek sağlayıcı içerir:

| SDK | Ne için |
|-----|---------|
| [`theme-sdk`](https://github.com/Spwig/theme-sdk) | Token, kritik CSS ve page builder desteği olan temalar |
| [`provider-sdks`](https://github.com/Spwig/provider-sdks) | Ödeme, kargo, SMS, e-posta ve diğer sağlayıcı entegrasyonları |
| [`headless-sdk`](https://github.com/Spwig/headless-sdk) | Spwig API'sini çağıran headless mağazalar |
| [`react`](https://github.com/Spwig/react) | Headless mağazalar için React hook'ları ve bileşenleri |

Bu depodaki her bileşen, Spwig marketplace tarafından keşfedilebilmesi için aynı manifest formatını (`manifest.json`) izler.

---

## Katkı

Katkılar memnuniyetle karşılanır. İşleri basit tutmak için CLA yerine **Developer Certificate of Origin (DCO)** kullanıyoruz — commit'lerinize sadece bir imza satırı ekleyin:

```bash
git commit -s -m "Add support for X"
```

PR gönderme, manifest formatı ve kod kuralları hakkında ayrıntılar için lütfen [CONTRIBUTING.md](CONTRIBUTING.md) dosyasına bakın.

**Katkı fikirleri:**

- Yeterince ele alınmamış sektörler için yeni temalar (yiyecek ve içecek, sağlık, eğitim, gayrimenkul)
- Bölgeye göre ek ödeme veya kargo sağlayıcıları
- Mevcut bileşenler için hata düzeltmeleri ve iyileştirmeler
- README ve bileşen kurulum talimatlarının çevirileri

---

## Lisans

**AGPL-3.0** — [LICENSE](LICENSE) dosyasına bakın. Bu kodu kendi kendine barındırılan mağazalar için özgürce kullanabilir, değiştirebilir ve dağıtabilirsiniz. Değiştirilmiş bir sürümü bir ağ hizmeti olarak çalıştırıyorsanız, değişikliklerinizi kullanıcılarınıza aynı lisans altında sunmanız gerekir.

Tescilli veya SaaS kullanımına uygun koşullar için [licensing@spwig.com](mailto:licensing@spwig.com) ile iletişime geçin.

---

## Destek

- **Belgeler**: [docs.spwig.com](https://docs.spwig.com)
- **Topluluk forumu**: [community.spwig.com](https://community.spwig.com)
- **E-posta**: support@spwig.com
- **Issues**: [github.com/Spwig/components/issues](https://github.com/Spwig/components/issues)

---

<p align="center">
  <sub><a href="https://spwig.com">Spwig</a> ve katkıda bulunanlar tarafından oluşturuldu</sub>
</p>
