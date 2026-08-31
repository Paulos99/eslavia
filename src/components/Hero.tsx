import type { Product } from "../data/types";
import { publicUrl } from "../lib/publicUrl";

export function Hero({ photo }: { photo?: Product }) {
  return (
    <section className="hero" id="top">
      <div className="container hero-grid">
        <div className="hero-copy reveal">
          <p className="eyebrow">Женский трикотаж · Иваново</p>
          <h1>
            Комфорт натуральных тканей <em>на каждый день</em>
          </h1>
          <p className="hero-lead">
            Одежда для дома и отдыха, широкий размерный ряд от 42 до 70. Смотрите каталог или запросите оптовый прайс.
          </p>
          <div className="hero-actions">
            <a className="btn btn-primary" href="#catalog">
              Смотреть каталог
            </a>
            <a className="btn btn-ghost" href="#wholesale">
              Получить оптовый прайс
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
