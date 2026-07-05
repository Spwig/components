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
  <strong>한국어</strong> |
  <a href="README.tr.md">Türkçe</a> |
  <a href="README.vi.md">Tiếng Việt</a> |
  <a href="README.th.md">ไทย</a>
</p>

<p align="center">
  <img src="https://spwig.com/images/logo.svg" alt="Spwig" width="200">
</p>

<h1 align="center">Spwig 컴포넌트</h1>

<p align="center">
  <strong>Spwig 이커머스 플랫폼을 위한 테마, 관리자 유틸리티, 공급자 통합.</strong>
</p>

<p align="center">
  <a href="https://spwig.com">웹사이트</a> &nbsp;&bull;&nbsp;
  <a href="https://docs.spwig.com">문서</a> &nbsp;&bull;&nbsp;
  <a href="https://community.spwig.com">커뮤니티</a> &nbsp;&bull;&nbsp;
  <a href="https://spwig.com/en/demos">라이브 데모</a>
</p>

---

## 개요

이 저장소는 자체 호스팅형 이커머스 플랫폼 [Spwig](https://spwig.com)를 위한 오픈소스 컴포넌트 라이브러리입니다. Spwig 설치가 사용할 수 있는 세 가지 컴포넌트 유형을 포함합니다:

| | |
|--|--|
| **테마** | 바로 사용할 수 있는 스토어프론트 디자인 |
| **유틸리티** | 관리 UI 도우미 (색상 선택기, 그라디언트 편집기, 초점 선택기 등) |
| **통합** | 결제, 배송, SMS, 이메일, 번역, SEO, 소셜 공급자 |

각 컴포넌트는 Spwig 관리자에서 코드 없이 설치 및 업데이트되도록 설계되었으며, 소스는 여기에 있어 검토, 기여 또는 포크가 가능합니다.

---

## 포함된 항목

### 테마 (13)

| 테마 | 스타일 |
|------|--------|
| **Default** | 깔끔하고 전문적, 범용 |
| **Apparel** | 패션 및 의류 매장 |
| **Artisan** | 수공예품 |
| **Bold** | 강한 대비, 인상적 |
| **Botanica** | 식물, 정원, 자연 제품 |
| **Elegant Shop** | 프리미엄, 럭셔리 |
| **Modern Dark** | 다크 모드 우선 디자인 |
| **Modern Shop** | 현대적인 종합 매장 |
| **Nature** | 아웃도어 및 지속 가능한 브랜드 |
| **Space** | 기술, 가젯, 미래적 |
| **Starter** | 사용자 정의 테마의 최소 출발점 |
| **Tech** | 전자제품 및 하드웨어 |
| **Vivid** | 생동감 있고 화려한 |

### 관리자 유틸리티 (14)

Spwig 관리자 전반에서 재사용되는 UI 조각 — 색상 선택기, 그라디언트 크리에이터, 초점 선택기, 그림자 편집기, 타이포그래피 편집기, 배경 편집기, 테두리 편집기, 간격 편집기, 아이콘 선택기, 단위 선택기, 가시성 규칙 편집기, 폼 선택기, 번역 편집기 및 공유 유틸리티 베이스를 포함합니다.

### 통합 (49+)

| 카테고리 | 공급자 |
|----------|--------|
| **결제** | Stripe, Adyen, PayPal Checkout, Airwallex, Revolut, Square |
| **송금** | PayPal, Airwallex Payouts, Wise |
| **배송** | FedEx, UPS, USPS, Canada Post, Australia Post, NinjaVan |
| **터미널** | Stripe Terminal, Square Terminal, Adyen Terminal, Revolut Terminal, SumUp, Zettle |
| **이메일** | Gmail API, SMTP (Gmail / Outlook / SendGrid / SES / 모든 것) |
| **SMS** | Twilio, Twilio WhatsApp |
| **환율** | Fixer, currencylayer, XE, Open Exchange Rates, exchangerate-api, exchangeratesapi |
| **번역** | DeepL, AWS Translate, Azure Translator, Google Translate, 범용 API |
| **SEO** | Semrush, DataForSEO, AI SEO |
| **소셜** | Facebook Pages, Instagram Business, LinkedIn Company, Twitter |
| **상품 피드** | Google Merchant Center |
| **라이선스 서버** | Cryptlex, LicenseSpring, Keygen, 사용자 정의 API, Spwig 내장 |

---

## 설치

### Spwig 관리자를 통해 (권장)

Spwig 스토어의 관리자에서 클릭 한 번으로 컴포넌트를 설치할 수 있습니다:

**관리자 → 마켓플레이스 → 컴포넌트**

마켓플레이스는 이 저장소의 모든 컴포넌트와 프리미엄 및 서드파티 컴포넌트를 보여줍니다. **설치** 를 클릭하면 Spwig가 컴포넌트를 가져와 사이트에 통합하고 필요한 마이그레이션을 적용합니다.

### 수동 설치

사용자 정의된 Spwig 환경을 실행 중이거나 오프라인으로 개발하는 경우 수동으로 컴포넌트를 설치할 수 있습니다:

```bash
git clone https://github.com/Spwig/components.git
cp -r components/themes/botanica /path/to/spwig/media/components/themes/
```

그런 다음 Spwig 관리자에서 **마켓플레이스 → 로컬 컴포넌트 재검색** 을 실행합니다.

---

## 나만의 컴포넌트 개발하기

새 테마, 유틸리티 또는 통합을 만드시나요? 저희 SDK 중 하나로 시작하세요 — 각 SDK는 작고 잘 문서화된 프레임워크이며 포크할 수 있는 예제 공급자를 포함합니다:

| SDK | 만들 대상 |
|-----|-----------|
| [`theme-sdk`](https://github.com/Spwig/theme-sdk) | 토큰, 크리티컬 CSS, 페이지 빌더 지원이 있는 테마 |
| [`provider-sdks`](https://github.com/Spwig/provider-sdks) | 결제, 배송, SMS, 이메일 및 기타 공급자 통합 |
| [`headless-sdk`](https://github.com/Spwig/headless-sdk) | Spwig API를 호출하는 헤드리스 스토어프론트 |
| [`react`](https://github.com/Spwig/react) | 헤드리스 스토어프론트를 위한 React 훅과 컴포넌트 |

이 저장소의 모든 컴포넌트는 Spwig 마켓플레이스에서 검색할 수 있도록 동일한 매니페스트 형식 (`manifest.json`)을 따릅니다.

---

## 기여하기

기여를 환영합니다. 간단함을 유지하기 위해 CLA 대신 **Developer Certificate of Origin (DCO)** 을 사용합니다 — 커밋에 서명 라인만 추가하면 됩니다:

```bash
git commit -s -m "Add support for X"
```

PR 제출 방법, 매니페스트 형식 및 코딩 규칙에 대한 자세한 내용은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참조하세요.

**기여 아이디어:**

- 다루지 않은 분야를 위한 새 테마 (음식 및 음료, 건강, 교육, 부동산)
- 지역별 추가 결제 또는 배송 공급자
- 기존 컴포넌트의 버그 수정 및 개선
- README 및 컴포넌트 설정 지침의 번역

---

## 라이선스

**AGPL-3.0** — [LICENSE](LICENSE)를 참조하세요. 자체 호스팅 스토어를 위해 이 코드를 자유롭게 사용, 수정, 배포할 수 있습니다. 수정된 버전을 네트워크 서비스로 실행하는 경우 동일한 라이선스로 사용자에게 변경 사항을 제공해야 합니다.

독점적 또는 SaaS 용도에 맞는 조건은 [licensing@spwig.com](mailto:licensing@spwig.com)으로 문의하세요.

---

## 지원

- **문서**: [docs.spwig.com](https://docs.spwig.com)
- **커뮤니티 포럼**: [community.spwig.com](https://community.spwig.com)
- **이메일**: support@spwig.com
- **이슈**: [github.com/Spwig/components/issues](https://github.com/Spwig/components/issues)

---

<p align="center">
  <sub><a href="https://spwig.com">Spwig</a>와 기여자들이 만듭니다</sub>
</p>
