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
  <strong>हिन्दी</strong> |
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

<h1 align="center">Spwig कंपोनेंट्स</h1>

<p align="center">
  <strong>Spwig ई-कॉमर्स प्लेटफ़ॉर्म के लिए थीम, एडमिन यूटिलिटीज़ और प्रदाता एकीकरण।</strong>
</p>

<p align="center">
  <a href="https://spwig.com">वेबसाइट</a> &nbsp;&bull;&nbsp;
  <a href="https://docs.spwig.com">दस्तावेज़</a> &nbsp;&bull;&nbsp;
  <a href="https://community.spwig.com">समुदाय</a> &nbsp;&bull;&nbsp;
  <a href="https://spwig.com/en/demos">लाइव डेमो</a>
</p>

---

## अवलोकन

यह रिपॉज़िटरी [Spwig](https://spwig.com) के लिए ओपन-सोर्स कंपोनेंट लाइब्रेरी है, जो एक स्व-होस्टेड ई-कॉमर्स प्लेटफ़ॉर्म है। इसमें तीन प्रकार के कंपोनेंट होते हैं जिन्हें Spwig इंस्टॉलेशन उपयोग कर सकता है:

| | |
|--|--|
| **थीम** | उपयोग के लिए तैयार स्टोरफ्रंट डिज़ाइन |
| **यूटिलिटीज़** | एडमिन UI सहायक (कलर पिकर, ग्रेडिएंट एडिटर, फोकल पॉइंट पिकर, आदि) |
| **एकीकरण** | भुगतान, शिपिंग, SMS, ईमेल, अनुवाद, SEO और सोशल प्रदाता |

प्रत्येक कंपोनेंट को Spwig एडमिन के माध्यम से बिना कोड के इंस्टॉल और अपडेट करने के लिए डिज़ाइन किया गया है, लेकिन स्रोत यहीं रहता है ताकि आप इसे निरीक्षित कर सकें, योगदान दे सकें या fork कर सकें।

---

## जो शामिल है

### थीम (13)

| थीम | शैली |
|-----|------|
| **Default** | साफ़, पेशेवर, बहुमुखी |
| **Apparel** | फैशन और वस्त्र स्टोर |
| **Artisan** | हस्तनिर्मित सामान |
| **Bold** | उच्च कंट्रास्ट, प्रभावशाली |
| **Botanica** | पौधे, बगीचा, प्राकृतिक उत्पाद |
| **Elegant Shop** | प्रीमियम, लक्जरी |
| **Modern Dark** | डार्क-मोड-प्रथम डिज़ाइन |
| **Modern Shop** | समकालीन सामान्य स्टोर |
| **Nature** | आउटडोर और टिकाऊ ब्रांड |
| **Space** | तकनीक, गैजेट्स, भविष्यवादी |
| **Starter** | कस्टम थीम के लिए न्यूनतम प्रारंभिक बिंदु |
| **Tech** | इलेक्ट्रॉनिक्स और हार्डवेयर |
| **Vivid** | जीवंत, रंगीन |

### एडमिन यूटिलिटीज़ (14)

Spwig एडमिन इंटरफ़ेस में पुन: प्रयोज्य UI टुकड़े — कलर पिकर, ग्रेडिएंट क्रिएटर, फोकल पॉइंट सेलेक्टर, शैडो एडिटर, टाइपोग्राफी एडिटर, बैकग्राउंड एडिटर, बॉर्डर एडिटर, स्पेसिंग एडिटर, आइकन पिकर, यूनिट सेलेक्टर, विज़िबिलिटी रूल एडिटर, फॉर्म सेलेक्टर, अनुवाद एडिटर और एक साझा यूटिलिटी बेस शामिल हैं।

### एकीकरण (49+)

| श्रेणी | प्रदाता |
|--------|--------|
| **भुगतान** | Stripe, Adyen, PayPal Checkout, Airwallex, Revolut, Square |
| **भुगतान (आउटगोइंग)** | PayPal, Airwallex Payouts, Wise |
| **शिपिंग** | FedEx, UPS, USPS, Canada Post, Australia Post, NinjaVan |
| **टर्मिनल** | Stripe Terminal, Square Terminal, Adyen Terminal, Revolut Terminal, SumUp, Zettle |
| **ईमेल** | Gmail API, SMTP (Gmail / Outlook / SendGrid / SES / कोई भी) |
| **SMS** | Twilio, Twilio WhatsApp |
| **विनिमय दर** | Fixer, currencylayer, XE, Open Exchange Rates, exchangerate-api, exchangeratesapi |
| **अनुवाद** | DeepL, AWS Translate, Azure Translator, Google Translate, सामान्य API |
| **SEO** | Semrush, DataForSEO, AI SEO |
| **सोशल** | Facebook Pages, Instagram Business, LinkedIn Company, Twitter |
| **उत्पाद फ़ीड** | Google Merchant Center |
| **लाइसेंस सर्वर** | Cryptlex, LicenseSpring, Keygen, कस्टम API, Spwig बिल्ट-इन |

---

## स्थापना

### Spwig एडमिन के माध्यम से (अनुशंसित)

कंपोनेंट आपके Spwig स्टोर के एडमिन से एक क्लिक में इंस्टॉल हो जाते हैं:

**एडमिन → मार्केटप्लेस → कंपोनेंट्स**

मार्केटप्लेस इस रिपॉज़िटरी के प्रत्येक कंपोनेंट के साथ-साथ प्रीमियम और तृतीय-पक्ष वाले भी दिखाता है। **इंस्टॉल** पर क्लिक करें, और Spwig कंपोनेंट लाएगा, इसे आपकी साइट में एकीकृत करेगा, और आवश्यक माइग्रेशन लागू करेगा।

### मैनुअल इंस्टॉलेशन

यदि आप कस्टमाइज़्ड Spwig सेटअप चला रहे हैं या ऑफ़लाइन विकास कर रहे हैं, तो आप कंपोनेंट्स को मैन्युअल रूप से इंस्टॉल कर सकते हैं:

```bash
git clone https://github.com/Spwig/components.git
cp -r components/themes/botanica /path/to/spwig/media/components/themes/
```

फिर, Spwig एडमिन में, **मार्केटप्लेस → स्थानीय कंपोनेंट्स को फिर से स्कैन करें** चलाएँ।

---

## अपना स्वयं का कंपोनेंट विकसित करना

नई थीम, यूटिलिटी या एकीकरण बनाना चाहते हैं? हमारे एक SDK के साथ शुरू करें — प्रत्येक एक छोटा, अच्छी तरह से प्रलेखित फ्रेमवर्क है जिसमें एक उदाहरण प्रदाता है जिसे आप fork कर सकते हैं:

| SDK | निर्माण के लिए |
|-----|---------------|
| [`theme-sdk`](https://github.com/Spwig/theme-sdk) | टोकन, क्रिटिकल CSS और पेज बिल्डर समर्थन के साथ थीम |
| [`provider-sdks`](https://github.com/Spwig/provider-sdks) | भुगतान, शिपिंग, SMS, ईमेल और अन्य प्रदाता एकीकरण |
| [`headless-sdk`](https://github.com/Spwig/headless-sdk) | Spwig API को कॉल करने वाले हेडलेस स्टोरफ्रंट |
| [`react`](https://github.com/Spwig/react) | हेडलेस स्टोरफ्रंट के लिए React हुक्स और कंपोनेंट्स |

इस रिपॉज़िटरी में प्रत्येक कंपोनेंट एक ही manifest प्रारूप (`manifest.json`) का पालन करता है ताकि इसे Spwig मार्केटप्लेस द्वारा खोजा जा सके।

---

## योगदान

योगदान का स्वागत है। चीज़ों को सरल रखने के लिए हम CLA के बजाय **Developer Certificate of Origin (DCO)** का उपयोग करते हैं — बस अपने commits में एक sign-off लाइन जोड़ें:

```bash
git commit -s -m "Add support for X"
```

PR कैसे भेजें, manifest प्रारूप और कोडिंग सम्मेलनों के विवरण के लिए कृपया [CONTRIBUTING.md](CONTRIBUTING.md) देखें।

**योगदान के लिए विचार:**

- कम-सेवा वाले क्षेत्रों के लिए नई थीम (खाद्य और पेय, स्वास्थ्य, शिक्षा, रियल एस्टेट)
- क्षेत्र के अनुसार अतिरिक्त भुगतान या शिपिंग प्रदाता
- मौजूदा कंपोनेंट्स में बग फ़िक्स और सुधार
- README और कंपोनेंट सेटअप निर्देशों के अनुवाद

---

## लाइसेंस

**AGPL-3.0** — [LICENSE](LICENSE) देखें। आप स्व-होस्टेड स्टोर के लिए इस कोड का स्वतंत्र रूप से उपयोग, संशोधन और वितरण कर सकते हैं। यदि आप संशोधित संस्करण को नेटवर्क सेवा के रूप में चलाते हैं, तो आपको अपने उपयोगकर्ताओं को उसी लाइसेंस के तहत अपने परिवर्तनों को उपलब्ध कराना होगा।

स्वामित्व या SaaS उपयोग के अनुकूल शर्तों के लिए, [licensing@spwig.com](mailto:licensing@spwig.com) से संपर्क करें।

---

## समर्थन

- **दस्तावेज़ीकरण**: [docs.spwig.com](https://docs.spwig.com)
- **समुदाय फोरम**: [community.spwig.com](https://community.spwig.com)
- **ईमेल**: support@spwig.com
- **Issues**: [github.com/Spwig/components/issues](https://github.com/Spwig/components/issues)

---

<p align="center">
  <sub><a href="https://spwig.com">Spwig</a> और योगदानकर्ताओं द्वारा निर्मित</sub>
</p>
