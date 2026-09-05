# -*- coding: utf-8 -*-
"""Rewrite SEO copy without claiming production is in Ivanovo."""
from pathlib import Path
import json

ROOT = Path(r"C:\Users\user\Desktop\Организация\Проекты\КОДИНГ\таисия")
PHONE = "+7 (901) 694-01-48"
PHONE_RAW = "79016940148"
EMAIL = "Eslaviya.37@yandex.ru"
PICKUP_IVANOVO = "г. Иваново, ул. Ташкентская, д. 20"
PICKUP_KOHMA = "г. Кохма, ул. Ивановская, 17 (ТЦ Кохомский)"
OG_IMAGE = "https://paulos99.github.io/eslavia/images/products/m-126a/01.webp"
TITLE = "Эславия — женский трикотаж оптом и в розницу"
DESC = (
    "Женский трикотаж оптом и в розницу: домашние платья, пижамы, халаты. "
    "Оптовый прайс по запросу, розничные цены на сайте. Самовывоз в Иванове и Кохме, доставка по России."
)

ld = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": ["Organization", "ClothingStore"],
      "@id": "https://paulos99.github.io/eslavia/#organization",
      "name": "Эславия",
      "url": "https://paulos99.github.io/eslavia/",
      "image": OG_IMAGE,
      "description": "Женский трикотаж оптом и в розницу. Оптовый прайс по запросу.",
      "email": EMAIL,
      "telephone": f"+{PHONE_RAW}",
      "address": {
        "@type": "PostalAddress",
        "streetAddress": "ул. Ташкентская, д. 20",
        "addressLocality": "Иваново",
        "addressRegion": "Ивановская область",
        "addressCountry": "RU"
      },
      "areaServed": {"@type": "Country", "name": "Russia"},
      "priceRange": "₽₽",
      "sameAs": [
        f"https://t.me/+{PHONE_RAW}",
        f"https://wa.me/{PHONE_RAW}"
      ]
    },
    {
      "@type": "WebSite",
      "@id": "https://paulos99.github.io/eslavia/#website",
      "url": "https://paulos99.github.io/eslavia/",
      "name": "Эславия",
      "inLanguage": "ru-RU",
      "publisher": {"@id": "https://paulos99.github.io/eslavia/#organization"}
    },
    {
      "@type": "FAQPage",
      "@id": "https://paulos99.github.io/eslavia/#faq",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "Как купить женский трикотаж оптом у Эславии?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": (
              f"Оставьте заявку на оптовый прайс на сайте или напишите в WhatsApp/Telegram "
              f"по телефону {PHONE}. Самовывоз в Иванове и Кохме."
            )
          }
        },
        {
          "@type": "Question",
          "name": "Где самовывоз?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": f"{PICKUP_IVANOVO}; {PICKUP_KOHMA}."
          }
        },
        {
          "@type": "Question",
          "name": "Можно ли купить в розницу?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": (
              "Да. Розничные цены указаны в каталоге на сайте; "
              "опт — по отдельному прайсу после заявки."
            )
          }
        }
      ]
    }
  ]
}
ld_json = json.dumps(ld, ensure_ascii=False, indent=2)

index = f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <title>{TITLE}</title>
    <meta name="description" content="{DESC}" />
    <link rel="canonical" href="https://paulos99.github.io/eslavia/" />
    <meta property="og:title" content="{TITLE}" />
    <meta property="og:description" content="{DESC}" />
    <meta property="og:type" content="website" />
    <meta property="og:locale" content="ru_RU" />
    <meta property="og:url" content="https://paulos99.github.io/eslavia/" />
    <meta property="og:image" content="{OG_IMAGE}" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{TITLE}" />
    <meta name="twitter:description" content="{DESC}" />
    <meta name="twitter:image" content="{OG_IMAGE}" />
    <link rel="icon" href="./favicon.svg" type="image/svg+xml" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500;1,600&family=Manrope:wght@400;500;600;700&display=swap"
      rel="stylesheet"
    />
    <script type="application/ld+json">
{ld_json}
    </script>
  </head>
  <body>
    <noscript>
      <main style="max-width:40rem;margin:2rem auto;font-family:system-ui,sans-serif;padding:0 1rem">
        <h1>Эславия — женский трикотаж оптом и в розницу</h1>
        <p>Розничные цены — в каталоге на сайте. Оптовый прайс — по запросу.</p>
        <p>Телефон: <a href="tel:+{PHONE_RAW}">{PHONE}</a> · <a href="mailto:{EMAIL}">{EMAIL}</a></p>
        <p>Самовывоз: {PICKUP_IVANOVO}; {PICKUP_KOHMA}</p>
        <p><a href="https://paulos99.github.io/eslavia/">Открыть сайт с JavaScript</a></p>
      </main>
    </noscript>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""
(ROOT / "index.html").write_text(index, encoding="utf-8")
print("index.html updated")

hero = '''import type { Product } from "../data/types";
import { contacts } from "../data";
import { publicUrl } from "../lib/publicUrl";

export function Hero({ photo }: { photo?: Product }) {
  return (
    <section className="hero" id="top">
      <div className="container hero-grid">
        <div className="hero-copy reveal">
          <p className="eyebrow">Эславия · опт и розница</p>
          <h1>
            Женский трикотаж <em>оптом и в розницу</em>
          </h1>
          <p className="hero-lead">
            Эславия — домашний трикотаж: платья, пижамы, сарафаны, халаты и сорочки. Розница — цены на сайте.
            Опт — по прайсу после заявки. Размеры от 42 до 70.
          </p>
          <div className="hero-actions">
            <a className="btn btn-primary" href="#wholesale">
              Получить оптовый прайс
            </a>
            <a className="btn btn-ghost" href="#catalog">
              Смотреть каталог
            </a>
            <a className="btn btn-ghost" href={contacts.whatsapp}>
              Написать в WhatsApp
            </a>
          </div>
        </div>
        {photo?.images[0] ? (
          <div className="hero-photo reveal">
            <img src={publicUrl(photo.images[0])} alt={photo.name} width={720} height={900} fetchPriority="high" />
          </div>
        ) : null}
      </div>
    </section>
  );
}
'''
(ROOT / "src/components/Hero.tsx").write_text(hero, encoding="utf-8")
print("Hero.tsx updated")

faq = '''export function SeoFaq() {
  const items = [
    {
      q: "Как купить женский трикотаж оптом?",
      a: "Оставьте заявку «Получить оптовый прайс» или напишите в WhatsApp / Telegram. Прайс отправим после контакта.",
    },
    {
      q: "Где самовывоз?",
      a: "г. Иваново, ул. Ташкентская, д. 20 и г. Кохма, ул. Ивановская, 17 (ТЦ Кохомский).",
    },
    {
      q: "Есть розница?",
      a: "Да. Розничные цены указаны в каталоге на сайте; опт — по отдельному прайсу.",
    },
    {
      q: "Какие категории?",
      a: "Платья, пижамы, сарафаны, сорочки, туники, халаты.",
    },
  ];

  return (
    <section className="section" id="faq">
      <div className="container">
        <p className="eyebrow">Вопросы</p>
        <h2 className="section-title">Частые вопросы по опту</h2>
        <div className="faq-list">
          {items.map((item) => (
            <details key={item.q} className="faq-item">
              <summary>{item.q}</summary>
              <p>{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
'''
(ROOT / "src/components/SeoFaq.tsx").write_text(faq, encoding="utf-8")
print("SeoFaq.tsx updated")

# Scrub leftover "производство" + Иваново claims in other common UI files
banned_phrases = [
    "производство в Иваново",
    "производство Иваново",
    "от производителя в Иваново",
    "от производства в Иваново",
]
for rel in [
    "src/components/Hero.tsx",
    "src/components/SeoFaq.tsx",
    "index.html",
    "src/App.tsx",
    "src/components/Footer.tsx",
    "src/components/Contacts.tsx",
]:
    p = ROOT / rel
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8")
    low = text.lower()
    for phrase in banned_phrases:
        if phrase.lower() in low:
            print("WARN still has:", phrase, "in", rel)

print("done")
