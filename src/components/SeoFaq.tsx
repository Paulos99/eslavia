export function SeoFaq() {
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
