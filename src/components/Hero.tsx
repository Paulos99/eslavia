import type { Product } from "../data/types";
import { publicUrl } from "../lib/publicUrl";

/**
 * Dedicated high-quality hero renditions (scripts/make_hero_image.py), built from the
 * untouched 900x1200 original. Never use catalog thumbnails here.
 */
const HERO_IMAGES: Record<string, { widths: number[]; path: (w: number) => string }> = {
  "m-105h": { widths: [600, 900], path: (w) => `/images/hero/m-105h-${w}.webp` },
};

/** Rendered hero column width: 1 column ≤900px, else 1.1fr of (container − padding − 72px gap). */
const HERO_SIZES =
  "(max-width: 767px) calc(100vw - 40px), (max-width: 900px) calc(100vw - 80px), (max-width: 1240px) calc(55vw - 84px), 600px";

function heroImage(photo: Product) {
  const hi = HERO_IMAGES[photo.id];
  if (!hi) return { src: publicUrl(photo.images[0]), srcSet: undefined, sizes: undefined };
  const largest = hi.widths[hi.widths.length - 1];
  return {
    src: publicUrl(hi.path(largest)),
    srcSet: hi.widths.map((w) => `${publicUrl(hi.path(w))} ${w}w`).join(", "),
    sizes: HERO_SIZES,
  };
}

export function Hero({ photo }: { photo?: Product }) {
  return (
    <section className="hero" id="top">
      <div className="container hero-grid">
        <div className="hero-copy reveal">
          <p className="eyebrow">Эславия · женский трикотаж</p>
          <h1>
            Комфорт натуральных тканей <em>на каждый день</em>
          </h1>
          <p className="hero-lead">
            Одежда для дома и отдыха, широкий размерный ряд от 42 до 72. Смотрите каталог или запросите оптовый прайс.
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
            <img
              {...heroImage(photo)}
              alt={photo.name}
              width={900}
              height={1200}
              loading="eager"
              fetchPriority="high"
            />
          </div>
        ) : null}
      </div>
    </section>
  );
}
