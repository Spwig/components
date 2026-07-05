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
  <strong>Bahasa Indonesia</strong> |
  <a href="README.it.md">Italiano</a> |
  <a href="README.ko.md">한국어</a> |
  <a href="README.tr.md">Türkçe</a> |
  <a href="README.vi.md">Tiếng Việt</a> |
  <a href="README.th.md">ไทย</a>
</p>

<p align="center">
  <img src="https://spwig.com/images/logo.svg" alt="Spwig" width="200">
</p>

<h1 align="center">Komponen Spwig</h1>

<p align="center">
  <strong>Tema, utilitas admin, dan integrasi penyedia untuk platform e-commerce Spwig.</strong>
</p>

<p align="center">
  <a href="https://spwig.com">Situs web</a> &nbsp;&bull;&nbsp;
  <a href="https://docs.spwig.com">Dokumentasi</a> &nbsp;&bull;&nbsp;
  <a href="https://community.spwig.com">Komunitas</a> &nbsp;&bull;&nbsp;
  <a href="https://spwig.com/en/demos">Demo langsung</a>
</p>

---

## Ikhtisar

Repositori ini adalah pustaka komponen sumber terbuka untuk [Spwig](https://spwig.com), platform e-commerce yang di-host sendiri. Berisi tiga jenis komponen yang dapat digunakan oleh instalasi Spwig:

| | |
|--|--|
| **Tema** | Desain etalase siap pakai |
| **Utilitas** | Pembantu UI admin (pemilih warna, editor gradien, pemilih titik fokus, dll.) |
| **Integrasi** | Penyedia pembayaran, pengiriman, SMS, email, penerjemahan, SEO, dan media sosial |

Setiap komponen dirancang untuk diinstal dan diperbarui melalui admin Spwig — tanpa kode — tetapi kode sumbernya ada di sini agar Anda dapat memeriksa, berkontribusi, atau fork.

---

## Yang Termasuk

### Tema (13)

| Tema | Gaya |
|------|------|
| **Default** | Bersih, profesional, serbaguna |
| **Apparel** | Toko mode dan pakaian |
| **Artisan** | Barang kerajinan tangan |
| **Bold** | Kontras tinggi, tegas |
| **Botanica** | Tanaman, kebun, produk alami |
| **Elegant Shop** | Premium, mewah |
| **Modern Dark** | Desain berfokus pada mode gelap |
| **Modern Shop** | Toko umum kontemporer |
| **Nature** | Merek outdoor dan berkelanjutan |
| **Space** | Teknologi, gadget, futuristik |
| **Starter** | Titik awal minimal untuk tema kustom |
| **Tech** | Elektronik dan perangkat keras |
| **Vivid** | Cerah, berwarna |

### Utilitas Admin (14)

Bagian UI yang dapat digunakan kembali di seluruh admin Spwig — termasuk pemilih warna, pembuat gradien, pemilih titik fokus, editor bayangan, editor tipografi, editor latar belakang, editor batas, editor jarak, pemilih ikon, pemilih satuan, editor aturan visibilitas, pemilih formulir, editor terjemahan, dan basis utilitas bersama.

### Integrasi (49+)

| Kategori | Penyedia |
|----------|----------|
| **Pembayaran** | Stripe, Adyen, PayPal Checkout, Airwallex, Revolut, Square |
| **Pembayaran keluar** | PayPal, Airwallex Payouts, Wise |
| **Pengiriman** | FedEx, UPS, USPS, Canada Post, Australia Post, NinjaVan |
| **Terminal** | Stripe Terminal, Square Terminal, Adyen Terminal, Revolut Terminal, SumUp, Zettle |
| **Email** | Gmail API, SMTP (Gmail / Outlook / SendGrid / SES / apa saja) |
| **SMS** | Twilio, Twilio WhatsApp |
| **Nilai tukar** | Fixer, currencylayer, XE, Open Exchange Rates, exchangerate-api, exchangeratesapi |
| **Penerjemahan** | DeepL, AWS Translate, Azure Translator, Google Translate, API generik |
| **SEO** | Semrush, DataForSEO, AI SEO |
| **Media sosial** | Facebook Pages, Instagram Business, LinkedIn Company, Twitter |
| **Feed produk** | Google Merchant Center |
| **Server lisensi** | Cryptlex, LicenseSpring, Keygen, API kustom, Spwig bawaan |

---

## Instalasi

### Melalui admin Spwig (direkomendasikan)

Komponen dipasang dengan satu klik dari admin toko Spwig Anda:

**Admin → Marketplace → Komponen**

Marketplace menampilkan setiap komponen dalam repositori ini, plus yang premium dan pihak ketiga. Klik **Pasang**, dan Spwig akan mengambil komponen, mengintegrasikannya ke situs Anda, dan menerapkan migrasi yang diperlukan.

### Instalasi manual

Jika Anda menjalankan pengaturan Spwig yang dikustomisasi atau mengembangkan offline, Anda dapat memasang komponen secara manual:

```bash
git clone https://github.com/Spwig/components.git
cp -r components/themes/botanica /path/to/spwig/media/components/themes/
```

Kemudian, di admin Spwig, jalankan **Marketplace → Pindai ulang komponen lokal**.

---

## Mengembangkan Komponen Anda Sendiri

Membangun tema, utilitas, atau integrasi baru? Mulailah dengan salah satu SDK kami — masing-masing adalah kerangka kerja kecil yang didokumentasikan dengan baik dan berisi penyedia contoh yang dapat Anda fork:

| SDK | Untuk membangun |
|-----|-----------------|
| [`theme-sdk`](https://github.com/Spwig/theme-sdk) | Tema dengan token, CSS kritis, dan dukungan page builder |
| [`provider-sdks`](https://github.com/Spwig/provider-sdks) | Integrasi pembayaran, pengiriman, SMS, email, dan penyedia lainnya |
| [`headless-sdk`](https://github.com/Spwig/headless-sdk) | Etalase headless yang memanggil API Spwig |
| [`react`](https://github.com/Spwig/react) | Hook dan komponen React untuk etalase headless |

Setiap komponen dalam repositori ini mengikuti format manifest yang sama (`manifest.json`) sehingga dapat ditemukan oleh marketplace Spwig.

---

## Berkontribusi

Kontribusi diterima dengan senang hati. Untuk menjaga kesederhanaan, kami menggunakan **Developer Certificate of Origin (DCO)** alih-alih CLA — cukup tambahkan baris sign-off ke commit Anda:

```bash
git commit -s -m "Add support for X"
```

Lihat [CONTRIBUTING.md](CONTRIBUTING.md) untuk detail cara mengirim PR, format manifest, dan konvensi kode.

**Ide untuk berkontribusi:**

- Tema baru untuk sektor yang kurang tercakup (makanan & minuman, kesehatan, pendidikan, real estat)
- Penyedia pembayaran atau pengiriman tambahan berdasarkan wilayah
- Perbaikan bug dan peningkatan pada komponen yang ada
- Terjemahan README dan instruksi pengaturan komponen

---

## Lisensi

**AGPL-3.0** — lihat [LICENSE](LICENSE). Anda dapat menggunakan, memodifikasi, dan mendistribusikan kode ini secara bebas untuk toko yang di-host sendiri. Jika Anda menjalankan versi yang dimodifikasi sebagai layanan jaringan, Anda harus menyediakan perubahan Anda kepada pengguna Anda di bawah lisensi yang sama.

Untuk persyaratan yang sesuai dengan penggunaan proprietary atau SaaS, hubungi [licensing@spwig.com](mailto:licensing@spwig.com).

---

## Dukungan

- **Dokumentasi**: [docs.spwig.com](https://docs.spwig.com)
- **Forum komunitas**: [community.spwig.com](https://community.spwig.com)
- **Email**: support@spwig.com
- **Issues**: [github.com/Spwig/components/issues](https://github.com/Spwig/components/issues)

---

<p align="center">
  <sub>Dibuat oleh <a href="https://spwig.com">Spwig</a> dan kontributor</sub>
</p>
