import type { Category } from "../data/types";
import { publicUrl } from "../lib/publicUrl";

export function CategoryNav({
  categories,
  onSelect,
}: {
  categories: Category[];
  onSelect: (name: string) => void;
}) {
  return (
    <section className="section" id="categories">
      <div className="container">
        <div className="section-head">
          <div>
            <p className="eyebrow">Ассортимент</p>
            <h2 className="section-title">Категории</h2>
          </div>
          <a className="text-link" href="#catalog">
            Смотреть каталог
          </a>
        </div>
        <div className="category-grid">
          {categories.map((c) => (
            <a
              key={c.id}
              className="category-card"
              href="#catalog"
              onClick={() => onSelect(c.name)}
            >
              <div className="category-media">
                {c.image ? (
                  <img src={publicUrl(c.image)} alt={c.name} width={480} height={600} />
                ) : (
                  <span className="no-photo" />
                )}
                <span className="category-caption">
                  <span className="category-name">{c.name}</span>
                  <span className="category-count">
                    {c.count} {plural(c.count)}
                  </span>
                </span>
              </div>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}

function plural(n: number) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return "модель";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "модели";
  return "моделей";
}
