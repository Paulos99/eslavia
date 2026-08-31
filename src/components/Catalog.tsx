import { useState } from "react";
import { ProductCard } from "./ProductCard";
import type { Category, Product } from "../data/types";

const PAGE = 12;

export function Catalog({
  products,
  categories,
  category,
  setCategory,
  size,
  setSize,
  sizes,
  query,
  setQuery,
  onOpen,
}: {
  products: Product[];
  categories: Category[];
  category: string | null;
  setCategory: (v: string | null) => void;
  size: string | null;
  setSize: (v: string | null) => void;
  sizes: string[];
  query: string;
  setQuery: (v: string) => void;
  onOpen: (p: Product) => void;
}) {
  const [limit, setLimit] = useState(PAGE);
  const [sheet, setSheet] = useState(false);
  const visible = products.slice(0, limit);

  const resetLimit = () => setLimit(PAGE);

  return (
    <section className="section catalog-section" id="catalog">
      <div className="container">
        <div className="section-head">
          <div>
            <p className="eyebrow">Коллекция</p>
            <h2 className="section-title">Каталог</h2>
          </div>
          <div className="catalog-tabs desktop-only">
            <button type="button" className={`chip ${!category ? "is-active" : ""}`} onClick={() => { setCategory(null); resetLimit(); }}>
              Все
            </button>
            {categories.map((c) => (
              <button
                key={c.id}
                type="button"
                className={`chip ${category === c.name ? "is-active" : ""}`}
                onClick={() => {
                  setCategory(c.name);
                  resetLimit();
                }}
              >
                {c.name}
              </button>
            ))}
          </div>
        </div>

        <div className="catalog-tools desktop-only">
          <input
            className="search"
            type="search"
            placeholder="Поиск по названию, артикулу или категории"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              resetLimit();
            }}
            aria-label="Поиск"
          />
          <select
            className="size-select"
            value={size || ""}
            onChange={(e) => {
              setSize(e.target.value || null);
              resetLimit();
            }}
            aria-label="Размер"
          >
            <option value="">Все размеры</option>
            {sizes.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <div className="filters filters-mobile">
          <input
            className="search"
            type="search"
            placeholder="Поиск"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              resetLimit();
            }}
            aria-label="Поиск по каталогу"
          />
          <button type="button" className="btn btn-ghost mobile-filters-btn" onClick={() => setSheet(true)}>
            Фильтры
          </button>
        </div>

        {sheet ? (
          <>
            <button className="sheet-backdrop" type="button" aria-label="Закрыть фильтры" onClick={() => setSheet(false)} />
            <div className="sheet" role="dialog" aria-label="Фильтры">
              <p className="sheet-title">Фильтры</p>
              <div className="sheet-chips">
                <button type="button" className={`chip ${!category ? "is-active" : ""}`} onClick={() => setCategory(null)}>
                  Все
                </button>
                {categories.map((c) => (
                  <button key={c.id} type="button" className={`chip ${category === c.name ? "is-active" : ""}`} onClick={() => setCategory(c.name)}>
                    {c.name}
                  </button>
                ))}
              </div>
              <select className="size-select" value={size || ""} onChange={(e) => setSize(e.target.value || null)} aria-label="Размер">
                <option value="">Все размеры</option>
                {sizes.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <button type="button" className="btn btn-primary sheet-done" onClick={() => setSheet(false)}>
                Готово
              </button>
            </div>
          </>
        ) : null}

        {visible.length === 0 ? (
          <p className="empty">Ничего не найдено. Сбросьте фильтр или измените запрос.</p>
        ) : (
          <div className="product-grid">
            {visible.map((p) => (
              <ProductCard key={p.id} product={p} onOpen={onOpen} />
            ))}
          </div>
        )}
        {limit < products.length ? (
          <div className="more-wrap">
            <button type="button" className="btn btn-ghost" onClick={() => setLimit((n) => n + PAGE)}>
              Показать ещё
            </button>
          </div>
        ) : null}
      </div>
    </section>
  );
}
