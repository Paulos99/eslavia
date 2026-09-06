const items = [
  { title: "Опт от 5 000 ₽", text: "Каталог и оптовый прайс по заявке" },
  { title: "Натуральные ткани", text: "Хлопок и домашний трикотаж" },
  { title: "Размеры 42–72", text: "Широкий ряд, в том числе большие" },
  { title: "Самовывоз", text: "Иваново и Кохма" },
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
