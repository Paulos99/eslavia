const items = [
  { title: "Опт и розница", text: "Каталог моделей и оптовый прайс" },
  { title: "Натуральные ткани", text: "Хлопок и домашний трикотаж" },
  { title: "Размеры 42–70", text: "Широкий ряд, в том числе большие" },
  { title: "Москва", text: "Магазин в ТЦ «Домодедовский»" },
];

export function FactsBar() {
  return (
    <section className="facts-bar" aria-label="О бренде">
      <div className="container facts-bar-grid">
        {items.map((item) => (
          <div key={item.title} className="facts-bar-item">
            <p className="facts-bar-title">{item.title}</p>
            <p>{item.text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
