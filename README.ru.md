<p align="center">
  <a href="README.md">English</a> |
  <a href="README.fr.md">Français</a> |
  <a href="README.es.md">Español</a> |
  <a href="README.de.md">Deutsch</a> |
  <a href="README.ja.md">日本語</a> |
  <a href="README.zh-Hans.md">简体中文</a> |
  <a href="README.zh-Hant.md">繁體中文</a> |
  <a href="README.pt.md">Português</a> |
  <strong>Русский</strong> |
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

<h1 align="center">Компоненты Spwig</h1>

<p align="center">
  <strong>Темы, утилиты администрирования и интеграции провайдеров для платформы электронной коммерции Spwig.</strong>
</p>

<p align="center">
  <a href="https://spwig.com">Сайт</a> &nbsp;&bull;&nbsp;
  <a href="https://docs.spwig.com">Документация</a> &nbsp;&bull;&nbsp;
  <a href="https://community.spwig.com">Сообщество</a> &nbsp;&bull;&nbsp;
  <a href="https://spwig.com/en/demos">Живые демо</a>
</p>

---

## Обзор

Этот репозиторий — библиотека компонентов с открытым исходным кодом для [Spwig](https://spwig.com), самостоятельно размещаемой платформы электронной коммерции. Он содержит три типа компонентов, которые может использовать установка Spwig:

| | |
|--|--|
| **Темы** | Готовые дизайны витрин |
| **Утилиты** | Помощники интерфейса администратора (выбор цвета, редактор градиентов, выбор фокуса и т. д.) |
| **Интеграции** | Провайдеры платежей, доставки, SMS, электронной почты, перевода, SEO и социальных сетей |

Каждый компонент устанавливается и обновляется через администрирование Spwig без написания кода, но исходный код находится здесь, чтобы вы могли изучить его, внести вклад или сделать форк.

---

## Что включено

### Темы (13)

| Тема | Стиль |
|------|-------|
| **Default** | Чистый, профессиональный, универсальный |
| **Apparel** | Магазины моды и одежды |
| **Artisan** | Ручные изделия |
| **Bold** | Высокий контраст, выразительный |
| **Botanica** | Растения, сад, натуральные продукты |
| **Elegant Shop** | Премиум, роскошь |
| **Modern Dark** | Дизайн с приоритетом тёмной темы |
| **Modern Shop** | Современный универсальный магазин |
| **Nature** | Аутдор и экологичные бренды |
| **Space** | Технологии, гаджеты, футуризм |
| **Starter** | Минимальная база для собственных тем |
| **Tech** | Электроника и оборудование |
| **Vivid** | Яркий, красочный |

### Утилиты администрирования (14)

Переиспользуемые элементы интерфейса во всей администрации Spwig — включая выбор цвета, генератор градиентов, выбор фокуса, редактор теней, редактор типографики, редактор фона, редактор границ, редактор отступов, выбор иконок, выбор единиц, редактор правил видимости, выбор форм, редактор переводов и общую базу утилит.

### Интеграции (49+)

| Категория | Провайдеры |
|-----------|------------|
| **Платежи** | Stripe, Adyen, PayPal Checkout, Airwallex, Revolut, Square |
| **Выплаты** | PayPal, Airwallex Payouts, Wise |
| **Доставка** | FedEx, UPS, USPS, Canada Post, Australia Post, NinjaVan |
| **Терминалы** | Stripe Terminal, Square Terminal, Adyen Terminal, Revolut Terminal, SumUp, Zettle |
| **Email** | Gmail API, SMTP (Gmail / Outlook / SendGrid / SES / любой) |
| **SMS** | Twilio, Twilio WhatsApp |
| **Курсы валют** | Fixer, currencylayer, XE, Open Exchange Rates, exchangerate-api, exchangeratesapi |
| **Перевод** | DeepL, AWS Translate, Azure Translator, Google Translate, универсальный API |
| **SEO** | Semrush, DataForSEO, AI SEO |
| **Соцсети** | Facebook Pages, Instagram Business, LinkedIn Company, Twitter |
| **Товарные фиды** | Google Merchant Center |
| **Серверы лицензий** | Cryptlex, LicenseSpring, Keygen, произвольный API, встроенный Spwig |

---

## Установка

### Через администрирование Spwig (рекомендуется)

Компоненты устанавливаются одним щелчком из администрирования вашего магазина Spwig:

**Admin → Marketplace → Компоненты**

Marketplace показывает все компоненты этого репозитория, а также премиум- и сторонние. Нажмите **Установить**, и Spwig загрузит компонент, интегрирует его в ваш сайт и применит необходимые миграции.

### Ручная установка

Если вы используете кастомизированную настройку Spwig или разрабатываете офлайн, компоненты можно установить вручную:

```bash
git clone https://github.com/Spwig/components.git
cp -r components/themes/botanica /path/to/spwig/media/components/themes/
```

Затем в администрировании Spwig выполните **Marketplace → Пересканировать локальные компоненты**.

---

## Разработка собственного компонента

Создаёте новую тему, утилиту или интеграцию? Начните с одного из наших SDK — каждый представляет собой небольшой хорошо документированный фреймворк с примером провайдера для форка:

| SDK | Для создания |
|-----|--------------|
| [`theme-sdk`](https://github.com/Spwig/theme-sdk) | Темы с токенами, критическим CSS и поддержкой page builder |
| [`provider-sdks`](https://github.com/Spwig/provider-sdks) | Интеграции платежей, доставки, SMS, email и других провайдеров |
| [`headless-sdk`](https://github.com/Spwig/headless-sdk) | Headless-витрины, обращающиеся к API Spwig |
| [`react`](https://github.com/Spwig/react) | React-хуки и компоненты для headless-витрин |

Каждый компонент в этом репозитории следует единому формату манифеста (`manifest.json`), чтобы marketplace Spwig мог его обнаружить.

---

## Вклад

Вклады приветствуются. Чтобы сохранить простоту, мы используем **Developer Certificate of Origin (DCO)** вместо CLA — просто добавьте строку подписи к вашим коммитам:

```bash
git commit -s -m "Add support for X"
```

Подробности о том, как отправить PR, о формате манифеста и о соглашениях по коду, см. в [CONTRIBUTING.md](CONTRIBUTING.md).

**Идеи для вклада:**

- Новые темы для недостаточно представленных отраслей (еда и напитки, здоровье, образование, недвижимость)
- Дополнительные провайдеры платежей или доставки по регионам
- Исправления и улучшения существующих компонентов
- Переводы README и инструкций по настройке компонентов

---

## Лицензия

**AGPL-3.0** — см. [LICENSE](LICENSE). Вы можете свободно использовать, изменять и распространять этот код для самостоятельно размещаемых магазинов. Если вы запускаете изменённую версию как сетевой сервис, вы обязаны предоставить свои изменения пользователям на тех же условиях лицензии.

Для условий, подходящих для проприетарного или SaaS-использования, свяжитесь с [licensing@spwig.com](mailto:licensing@spwig.com).

---

## Поддержка

- **Документация**: [docs.spwig.com](https://docs.spwig.com)
- **Форум сообщества**: [community.spwig.com](https://community.spwig.com)
- **Email**: support@spwig.com
- **Issues**: [github.com/Spwig/components/issues](https://github.com/Spwig/components/issues)

---

<p align="center">
  <sub>Создано <a href="https://spwig.com">Spwig</a> и участниками</sub>
</p>
